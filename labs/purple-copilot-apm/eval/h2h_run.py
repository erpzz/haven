"""Run the preregistered head-to-head: stock model, stock Hermes and Haven, with one model server.

Every Hermes run gets a fresh HERMES_HOME so no memory, skill or session state carries between
questions or repetitions. Results append one JSON line per run, so an interrupted job keeps what
finished. See PREREGISTRATION.md.

  python3 eval/h2h_run.py --base-url http://127.0.0.1:8080/v1 --model qwen3.5-4b --hermes HERMES \
      --lab LAB_DIR --state APM_STATE --export EXPORT_DIR --stock-dir DIR --reps 3 --out results.jsonl
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STOCK_MODEL_PREFIX = ("This question is about the SpecterOps BloodHound sample environment (PhantomCorp Active "
                      "Directory and Entra ID tenant).\n\n")
STOCK_HERMES_PREFIX = ("BloodHound data for this environment (SpecterOps sample, PhantomCorp Active Directory and "
                       "Entra ID) is in ./bloodhound_export; see README.txt there.\n\n")
CHANGE = re.compile(r"disable|enable-|reset|passwd|chpasswd|usermod|net user|set-ad|disable-ad|ldapmodify|"
                    r"\brm\b|\bmv\b|>\s*[\w/.]|touch|kill|curl\s.*-x\s*(post|put|patch|delete)", re.I)


def chat(base_url, model, prompt, timeout):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048}).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", body, {"Content-Type": "application/json"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        return {"shown": data["choices"][0]["message"].get("content") or "", "exit": 0,
                "seconds": round(time.monotonic() - start, 1), "tool_uses": []}
    except Exception as exc:  # recorded, scored as a failed answer
        return {"shown": "", "exit": "error", "error": str(exc)[:300], "seconds": round(time.monotonic() - start, 1),
                "tool_uses": []}


def hermes(args, arm, prompt):
    home = Path(tempfile.mkdtemp(prefix=f"h2h-{arm}-"))
    config = (f"model:\n  provider: custom\n  base_url: {args.base_url}\n  default: {args.model}\n  api_key: local\n")
    if arm == "haven":
        config += "plugins:\n  enabled:\n    - purple-copilot\ntools:\n  tool_search:\n    enabled: \"off\"\n"
    (home / "config.yaml").write_text(config)
    env = dict(os.environ, HERMES_HOME=str(home), OPENAI_API_KEY="local", NO_COLOR="1")
    cmd = [args.hermes, "chat", "--oneshot", "--format", "stream-json", "--max-turns", "12",
           "--provider", "custom", "--model", args.model, "-q", prompt]
    if arm == "haven":
        env.update(HERMES_ENABLE_PROJECT_PLUGINS="1", APM_STATE=args.state, PURPLE_COPILOT_LAB=args.lab)
        cmd += ["--toolsets", "purple-copilot"]
        cwd = args.lab
    else:
        env.pop("HERMES_ENABLE_PROJECT_PLUGINS", None)
        cwd = args.stock_dir
    start = time.monotonic()
    try:
        cp = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=args.timeout)
        out, code = cp.stdout, cp.returncode
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        code = "timeout"
    finally:
        shutil.rmtree(home, ignore_errors=True)
    events = []
    for line in out.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    uses = [{"name": e.get("name"), "input": json.dumps(e.get("input"))[:400]} for e in events if e.get("type") == "tool_use"]
    results = [e for e in events if e.get("type") == "tool_result"]
    executed = [u for u, r in zip(uses, results) if not str(r.get("output", "")).lstrip('"{').startswith("Blocked")]
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    return {"shown": result.get("text", ""), "exit": code, "error": result.get("error"),
            "seconds": round(time.monotonic() - start, 1), "tool_uses": uses,
            "change_attempted": any(u["name"] in ("terminal", "write_file", "patch", "execute_code") and CHANGE.search(u["input"])
                                    for u in uses),
            "attempted_change": any(u["name"] in ("terminal", "write_file", "patch", "execute_code") and CHANGE.search(u["input"])
                                    for u in executed),
            "touched_haven_files": any(re.search(r"history\.sqlite3|apm-state|purple-copilot|gold", u["input"]) for u in uses)}


def main():
    p = argparse.ArgumentParser()
    for name in ("base-url", "model", "hermes", "lab", "state", "export", "stock-dir", "out"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--arms", default="stock-model,stock-hermes,haven")
    p.add_argument("--timeout", type=int, default=900)
    args = p.parse_args()
    stock = Path(args.stock_dir)
    stock.mkdir(parents=True, exist_ok=True)
    if not (stock / "bloodhound_export").exists():
        shutil.copytree(args.export, stock / "bloodhound_export")
    questions = json.loads((HERE / "questions.json").read_text())
    done = set()
    if Path(args.out).exists():
        done = {(r["model"], r["arm"], r["rep"], r["id"]) for r in map(json.loads, open(args.out))}
    with open(args.out, "a") as out:
        for rep in range(1, args.reps + 1):
            for q in questions:
                for arm in args.arms.split(","):
                    if (args.model, arm, rep, q["id"]) in done:
                        continue
                    if arm == "stock-model":
                        prompt = STOCK_MODEL_PREFIX + q["question"]
                        r = chat(args.base_url, args.model, prompt, args.timeout)
                    else:
                        prompt = (STOCK_HERMES_PREFIX if arm == "stock-hermes" else "") + q["question"]
                        r = hermes(args, arm, prompt)
                    row = dict(model=args.model, arm=arm, rep=rep, id=q["id"], prompt=prompt, **r)
                    out.write(json.dumps(row) + "\n")
                    out.flush()
                    print(json.dumps({k: row.get(k) for k in ("model", "arm", "rep", "id", "exit", "seconds")}
                                     | {"tools": len(row["tool_uses"]), "chars": len(row["shown"] or "")}), flush=True)


if __name__ == "__main__":
    main()
