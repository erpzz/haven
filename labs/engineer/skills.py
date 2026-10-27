#!/usr/bin/env python3
"""Inherited skills: executable capabilities admitted only on held-out evidence.

A skill is a directory with skill.json (name, description, parameters schema),
skill.py (stdlib Python, reads JSON args, prints one JSON result) and
recipe.md (the same procedure in prose, used as the text-only control arm).

admit() runs the candidate, inside the OS sandbox, against held-out cases the
author never saw (they live in the private state directory, which the sandbox
denies to every agent). Each case has a repo and an expect.json; the harness,
not the skill, decides pass/fail. Admitted skills are content-addressed and the
admission record is HMAC-signed; any later change to the files changes the hash
and the executor refuses to run it. Rejections are kept with their reasons.

An admitted skill is then offered to agents as a tool (skill_<name>), runs
under the same policy, sandbox and receipts as any command, and can be shipped
to an enrolled node and run there with no model involved (export/run-remote).

  skills.py admit CANDIDATE_DIR --heldout DIR --author ID [--evidence TASK_ID ...]
  skills.py list
  skills.py run-remote NAME --node slink --repo-bundle DIR
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sandbox  # noqa: E402
from session import STATE  # noqa: E402

REG = STATE / "skills"
FILES = ("skill.json", "skill.py", "recipe.md")


def _key():
    REG.mkdir(parents=True, exist_ok=True, mode=0o700)
    p = REG / "registry.key"
    if not p.exists():
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(secrets.token_bytes(32))
    return p.read_bytes()


def content_hash(d):
    h = hashlib.sha256()
    for name in FILES:
        h.update(name.encode() + b"\0" + (pathlib.Path(d) / name).read_bytes() + b"\0")
    return h.hexdigest()


def run_skill(skill_dir, cwd, args, *, timeout_s=300, network=False):
    """Run a skill in the sandbox with cwd as the writable workspace. Returns (result_dict|None, raw)."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="haven-skill-"))
    argv = [sys.executable, "-I", str(pathlib.Path(skill_dir) / "skill.py"), json.dumps(args)]
    if sandbox.describe()["available"]:
        argv = sandbox.wrap(argv, workspace=cwd, tmpdir=tmp, network=network)
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "USER") if k in os.environ}
    env.update(TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1", NO_COLOR="1", CI="1")
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout_s, env=env)
        raw = r.stdout.strip()
    except subprocess.TimeoutExpired:
        return None, "timeout"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        return json.loads(raw.splitlines()[-1]), raw
    except (ValueError, IndexError):
        return None, (raw + "\n" + r.stderr)[-2000:]


def check_case(result, expect):
    """Harness-side judgement of one held-out case."""
    if not isinstance(result, dict):
        return False, "no JSON result"
    problems = []
    if expect.get("framework") and result.get("framework") != expect["framework"]:
        problems.append(f"framework {result.get('framework')!r} != {expect['framework']!r}")
    got = {_norm_id(f.get("id", "")) for f in result.get("failing") or [] if isinstance(f, dict)}
    want = {_norm_id(x) for x in expect.get("failing", [])}
    if got != want:
        problems.append(f"failing {sorted(got)} != {sorted(want)}")
    if "passed" in expect and result.get("passed") != expect["passed"]:
        problems.append(f"passed {result.get('passed')} != {expect['passed']}")
    if expect.get("failing") and not all(f.get("message") for f in result.get("failing") or []):
        problems.append("a failure has no message")
    return not problems, "; ".join(problems)


def _norm_id(s):
    """Compare test ids by their last two components (Class.test or file::test)."""
    parts = [p for p in s.replace("::", ".").replace("/", ".").replace(" ", "").split(".") if p and p != "py"]
    return ".".join(parts[-2:]).lower()


def validate(candidate, cases_dir):
    report = []
    for case in sorted(pathlib.Path(cases_dir).iterdir()):
        if not (case / "repo").is_dir():
            continue
        expect = json.loads((case / "expect.json").read_text())
        with tempfile.TemporaryDirectory(prefix="haven-case-") as t:
            ws = pathlib.Path(t) / "repo"
            shutil.copytree(case / "repo", ws)
            t0 = time.monotonic()
            result, raw = run_skill(candidate, ws, expect.get("args", {}))
            ok, why = check_case(result, expect)
            report.append({"case": case.name, "ok": ok, "why": why, "seconds": round(time.monotonic() - t0, 2),
                           "raw_tail": "" if ok else raw[-400:]})
    return report


def admit(candidate, heldout, author, evidence=(), dev=None):
    candidate = pathlib.Path(candidate)
    manifest = json.loads((candidate / "skill.json").read_text())
    name = manifest["name"]
    if not name.replace("_", "").isalnum():
        raise SystemExit("skill name must be alphanumeric/underscore")
    for f in FILES:
        if not (candidate / f).is_file():
            raise SystemExit(f"candidate is missing {f}")
    digest = content_hash(candidate)
    dev_report = validate(candidate, dev) if dev else []
    held = validate(candidate, heldout)
    passed = all(c["ok"] for c in held) and bool(held)
    record = {"name": name, "sha256": digest, "author": author, "evidence_tasks": list(evidence),
              "description": manifest.get("description", ""), "parameters": manifest.get("parameters", {}),
              "status": "admitted" if passed else "rejected", "admitted_at": time.time(),
              "validation": {"heldout": held, "dev": dev_report},
              "validation_summary": {"heldout_pass": sum(c["ok"] for c in held), "heldout_total": len(held),
                                     "dev_pass": sum(c["ok"] for c in dev_report), "dev_total": len(dev_report)}}
    body = json.dumps(record, sort_keys=True)
    record["signature"] = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()
    dest = REG / name / digest[:12] if passed else REG / "rejected" / f"{name}-{digest[:12]}-{int(time.time())}"
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    for f in FILES:
        shutil.copy2(candidate / f, dest / f)
    (dest / "admission.json").write_text(json.dumps(record, indent=2))
    if passed:
        index = _index()
        index[name] = {"version": digest[:12], "path": str(dest)}
        (REG / "index.json").write_text(json.dumps(index, indent=2))
    return record


def _index():
    p = REG / "index.json"
    return json.loads(p.read_text()) if p.exists() else {}


def verified(name):
    """Admitted skill dir, after re-checking its signature and content hash. None if anything differs."""
    entry = _index().get(name)
    if not entry:
        return None
    d = pathlib.Path(entry["path"])
    try:
        rec = json.loads((d / "admission.json").read_text())
    except (OSError, ValueError):
        return None
    sig = rec.pop("signature", "")
    if not hmac.compare_digest(sig, hmac.new(_key(), json.dumps(rec, sort_keys=True).encode(),
                                             hashlib.sha256).hexdigest()):
        return None
    if rec.get("status") != "admitted" or content_hash(d) != rec["sha256"]:
        return None
    return d, rec


def tool_schemas(names=None):
    out = {}
    for name in (names or _index()):
        v = verified(name)
        if not v:
            continue
        d, rec = v
        params = rec.get("parameters") or {"type": "object", "properties": {}}
        params = {"type": "object", "properties": params.get("properties", {}),
                  "required": params.get("required", []), "additionalProperties": False}
        out[f"skill_{name}"] = {"description": f"[inherited skill, admitted on held-out evidence] {rec['description']}",
                                "parameters": params}
    return out


def recipe(name):
    v = verified(name)
    return (v[0] / "recipe.md").read_text() if v else ""


def list_skills():
    items = []
    for name, entry in _index().items():
        v = verified(name)
        rec = json.loads((pathlib.Path(entry["path"]) / "admission.json").read_text())
        items.append({k: rec.get(k) for k in ("name", "sha256", "author", "description", "admitted_at",
                                               "validation_summary", "evidence_tasks")}
                     | {"status": "admitted" if v else "INVALID (signature or content changed)"})
    rej = REG / "rejected"
    for d in sorted(rej.iterdir()) if rej.exists() else []:
        try:
            rec = json.loads((d / "admission.json").read_text())
        except (OSError, ValueError):
            continue
        items.append({k: rec.get(k) for k in ("name", "sha256", "author", "description", "admitted_at",
                                               "validation_summary")} | {"status": "rejected"})
    return {"skills": items}


def run_remote(name, node_ssh, repo_dir):
    """Ship an admitted skill (+ the sandbox) and a repo to an enrolled node; run it there with no model."""
    v = verified(name)
    if not v:
        raise SystemExit(f"{name} is not an admitted, intact skill")
    d, rec = v
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", node_ssh]
    stage = f".local/share/haven-skills/{name}-{rec['sha256'][:12]}"
    with tempfile.TemporaryDirectory() as t:
        tar = pathlib.Path(t) / "bundle.tar"
        bundle = pathlib.Path(t) / "bundle"
        (bundle / "skill").mkdir(parents=True)
        for f in FILES:
            shutil.copy2(d / f, bundle / "skill" / f)
        shutil.copy2(HERE / "sandbox.py", bundle / "sandbox.py")
        shutil.copytree(repo_dir, bundle / "repo", ignore=shutil.ignore_patterns(".git", "__pycache__"))
        subprocess.run(["tar", "-C", str(bundle), "-cf", str(tar), "."], check=True)
        remote = (f"set -e; rm -rf ~/{stage}; mkdir -p ~/{stage}; tar -C ~/{stage} -xf -; cd ~/{stage}; "
                  f"echo SHA=$(cat skill/skill.json skill/skill.py skill/recipe.md | sha256sum | cut -c1-12); "
                  f"python3 -c 'import sandbox,json;print(\"SANDBOX=\"+json.dumps(sandbox.describe()))'; "
                  f"cd repo; mkdir -p ../tmp; t0=$(date +%s.%N); "
                  f"python3 -I ../sandbox.py --landlock-exec "
                  f"'{{\"write\": [\"'$HOME/{stage}/repo'\", \"'$HOME/{stage}/tmp'\"], \"deny\": [], \"network\": false, \"local_ports\": []}}' "
                  f"-- env TMPDIR=$HOME/{stage}/tmp python3 -I ../skill/skill.py '{{}}' > ../result.json || true; "
                  f"echo ELAPSED=$(echo \"$(date +%s.%N) - $t0\" | bc); echo RESULT=$(tail -1 ../result.json)")
        t0 = time.monotonic()
        with open(tar, "rb") as fh:
            r = subprocess.run(ssh + [remote], stdin=fh, capture_output=True, text=True, timeout=300)
    out = {"node": node_ssh, "skill": name, "sha256": rec["sha256"], "round_trip_s": round(time.monotonic() - t0, 2),
           "exit": r.returncode, "stderr": r.stderr[-500:]}
    for line in r.stdout.splitlines():
        if line.startswith("RESULT="):
            try:
                out["result"] = json.loads(line[7:])
            except ValueError:
                out["result_raw"] = line[7:500]
        elif line.startswith("SANDBOX="):
            out["remote_sandbox"] = json.loads(line[8:])
        elif "=" in line and line.split("=", 1)[0] in ("SHA", "ELAPSED"):
            out[line.split("=", 1)[0].lower()] = line.split("=", 1)[1]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("admit")
    a.add_argument("candidate")
    a.add_argument("--heldout", required=True)
    a.add_argument("--dev")
    a.add_argument("--author", required=True)
    a.add_argument("--evidence", nargs="*", default=[])
    sub.add_parser("list")
    v = sub.add_parser("validate")
    v.add_argument("candidate")
    v.add_argument("--cases", required=True)
    rr = sub.add_parser("run-remote")
    rr.add_argument("name")
    rr.add_argument("--node", required=True)
    rr.add_argument("--repo", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "admit":
        rec = admit(args.candidate, args.heldout, args.author, args.evidence, args.dev)
        print(json.dumps({k: rec[k] for k in ("name", "status", "sha256", "validation_summary")}, indent=2))
        for c in rec["validation"]["heldout"]:
            print(("PASS " if c["ok"] else "FAIL ") + c["case"] + ("" if c["ok"] else f": {c['why']}"))
    elif args.cmd == "list":
        print(json.dumps(list_skills(), indent=2))
    elif args.cmd == "validate":
        for c in validate(args.candidate, args.cases):
            print(("PASS " if c["ok"] else "FAIL ") + c["case"] + ("" if c["ok"] else f": {c['why']} {c['raw_tail']}"))
    elif args.cmd == "run-remote":
        print(json.dumps(run_remote(args.name, args.node, args.repo), indent=2))


if __name__ == "__main__":
    main()
