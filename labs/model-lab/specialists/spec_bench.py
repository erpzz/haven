"""SPEC-2 knowledge benchmarks: freeze pinned eval/train sets, run a loopback model, score and compare.

  freeze   download pinned dataset revisions, normalize to multiple choice, decontaminate the training
           pools against every eval set, and write private JSONL plus a hash manifest
  run      ask an OpenAI-compatible loopback endpoint (llama-server, MLX, the Lab) each item once
  score    accuracy with Wilson 95% intervals and invalid-answer counts per benchmark
  compare  paired outcome counts and an exact two-sided sign test over shared item ids

Data and model outputs are private run files. Only manifests and aggregate receipts belong in Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import re
import time
import urllib.request

LETTERS = "ABCDE"
MMLU_MEDICAL = ["anatomy", "clinical_knowledge", "college_biology", "college_medicine",
                "medical_genetics", "professional_medicine"]

# name -> (domain, role, repo, licence). Eval sets are never trained on.
SOURCES = {
    "medqa_test": ("medical", "eval", "GBaker/MedQA-USMLE-4-options", "CC-BY-4.0"),
    "medmcqa_val": ("medical", "eval", "openlifescienceai/medmcqa", "Apache-2.0"),
    "pubmedqa_labeled": ("medical", "eval", "qiaojin/PubMedQA", "MIT"),
    "mmlu_medical": ("medical", "eval", "cais/mmlu", "MIT"),
    "cti_mcq": ("cyber", "eval", "AI4Sec/cti-bench", "CC-BY-NC-SA-4.0 (evaluation only)"),
    "cybermetric_2000": ("cyber", "eval", "tihanyin/CyberMetric", "Apache-2.0"),
    "mmlu_computer_security": ("cyber", "eval", "cais/mmlu", "MIT"),
    "medqa_train": ("medical", "train", "GBaker/MedQA-USMLE-4-options", "CC-BY-4.0"),
    "medmcqa_train": ("medical", "train", "openlifescienceai/medmcqa", "Apache-2.0"),
}


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def item(bench, index, question, options, answer, context=None):
    options = {k: str(v).strip() for k, v in options.items()}
    answer = str(answer).strip().upper()  # some sources use lowercase letters
    if answer not in options:
        raise ValueError(f"{bench}:{index} answer {answer!r} is not an option")
    row = {"id": f"{bench}-{index:05d}", "bench": bench, "question": str(question).strip(),
           "options": options, "answer": answer}
    if context:
        row["context"] = context
    return row


# ------------------------------------------------------------------ freeze
def _download(repo, filename, revision):
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo, filename, repo_type="dataset", revision=revision)


def _parquet(repo, config, split, revision):
    import pandas as pd
    from huggingface_hub import HfApi
    files = [f for f in HfApi().list_repo_files(repo, repo_type="dataset", revision=revision)
             if f.startswith(f"{config}/{split}") and f.endswith(".parquet")]
    if not files:
        raise SystemExit(f"{repo}: no parquet for {config}/{split} at {revision}")
    return pd.concat([pd.read_parquet(_download(repo, f, revision)) for f in sorted(files)])


def load_source(name, revisions):
    """revisions: {"main": sha, "parquet": sha of refs/convert/parquet or None} for the source repo."""
    repo = SOURCES[name][2]
    revision = revisions["parquet"] if name not in ("cti_mcq", "cybermetric_2000") else revisions["main"]
    if name in ("medqa_test", "medqa_train"):
        df = _parquet(repo, "default", name.split("_")[1], revision)
        return [item(name, i, r.question, dict(r.options), r.answer_idx) for i, r in enumerate(df.itertuples())]
    if name in ("medmcqa_val", "medmcqa_train"):
        df = _parquet(repo, "default", "validation" if name.endswith("val") else "train", revision)
        rows = []
        for i, r in enumerate(df.itertuples()):
            if r.choice_type != "single":
                continue  # multi-answer items have no single verifiable letter
            rows.append(item(name, i, r.question, {"A": r.opa, "B": r.opb, "C": r.opc, "D": r.opd},
                             LETTERS[int(r.cop)]))
        return rows
    if name == "pubmedqa_labeled":
        df = _parquet(repo, "pqa_labeled", "train", revision)
        choice = {"yes": "A", "no": "B", "maybe": "C"}
        return [item(name, i, r.question, {"A": "yes", "B": "no", "C": "maybe"}, choice[r.final_decision],
                     context="\n".join(r.context["contexts"])) for i, r in enumerate(df.itertuples())]
    if name.startswith("mmlu_"):
        subjects = MMLU_MEDICAL if name == "mmlu_medical" else ["computer_security"]
        rows = []
        for subject in subjects:
            df = _parquet(repo, subject, "test", revision)
            for r in df.itertuples():
                rows.append(item(name, len(rows), r.question, dict(zip(LETTERS, r.choices)), LETTERS[int(r.answer)]))
        return rows
    if name == "cti_mcq":
        import pandas as pd
        df = pd.read_csv(_download(repo, "cti-mcq.tsv", revision), sep="\t")
        return [item(name, i, r["Question"], {k: r[f"Option {k}"] for k in "ABCD"}, str(r["GT"]).strip())
                for i, r in df.iterrows()]
    if name == "cybermetric_2000":
        data = json.loads(pathlib.Path(_download(repo, "CyberMetric-2000-v1.json", revision)).read_text())
        return [item(name, i, q["question"], q["answers"], q["solution"])
                for i, q in enumerate(data["questions"])]
    raise KeyError(name)


def decontaminate(train_rows, eval_rows):
    """Drop training items whose normalized question equals any eval question."""
    seen = {norm(r["question"]) for r in eval_rows}
    kept = [r for r in train_rows if norm(r["question"]) not in seen]
    return kept, len(train_rows) - len(kept)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_freeze(args):
    from huggingface_hub import HfApi
    out = pathlib.Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; frozen sets are never silently regenerated.")
    out.mkdir(parents=True, exist_ok=True)
    os.umask(0o077)
    pinned = json.loads(pathlib.Path(args.pin).read_text())["sets"] if args.pin else None
    api, revisions = HfApi(), {}
    for repo in sorted({s[2] for s in SOURCES.values()}):
        if pinned:  # reproduce a committed manifest exactly
            revisions[repo] = next(v["revisions"] for v in pinned.values() if v["source"] == repo)
            continue
        refs = {r.ref: r.target_commit for r in api.list_repo_refs(repo, repo_type="dataset").converts}
        revisions[repo] = {"main": api.dataset_info(repo).sha, "parquet": refs.get("refs/convert/parquet")}
    data = {name: load_source(name, revisions[SOURCES[name][2]]) for name in SOURCES}
    evals = [r for name, rows in data.items() if SOURCES[name][1] == "eval" for r in rows]
    manifest = {"schema": "haven-spec2-bench-manifest-1", "frozen_unix": int(time.time()), "sets": {}}
    for name, rows in data.items():
        domain, role, repo, licence = SOURCES[name]
        removed = 0
        if role == "train":
            rows, removed = decontaminate(rows, evals)
        path = out / f"{name}.jsonl"
        path.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows))
        manifest["sets"][name] = {"domain": domain, "role": role, "source": repo,
                                  "revisions": revisions[repo], "licence": licence, "items": len(rows),
                                  "removed_as_eval_duplicates": removed, "sha256": sha256(path)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if pinned:
        drift = sorted(n for n, v in manifest["sets"].items() if v["sha256"] != pinned[n]["sha256"])
        if drift:
            raise SystemExit(f"Re-frozen sets differ from the pinned manifest: {drift}")
    print(json.dumps(manifest, indent=2, sort_keys=True))


# ------------------------------------------------------------------ run
SYSTEM = ("You are a careful expert. Answer the multiple-choice question. You may reason briefly; "
          "the last line of your reply must be 'Answer: X' where X is one option letter.")


def prompt(row):
    parts = []
    if row.get("context"):
        parts.append("Context:\n" + row["context"])
    parts.append("Question: " + row["question"])
    parts.append("\n".join(f"{k}) {v}" for k, v in sorted(row["options"].items())))
    return "\n\n".join(parts)


_ANSWER = re.compile(r"answer\s*(?:is)?\s*[:\-]?[\s*(]*([A-E])\b", re.I)


def parse_answer(text, options):
    """The last 'Answer: X', else a final line that is only a letter; otherwise None (invalid)."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    found = [m.group(1).upper() for m in _ANSWER.finditer(text)]
    if not found:
        last = text.strip().splitlines()[-1].strip(" .*()[]") if text.strip() else ""
        found = [last.upper()] if len(last) == 1 else []
    letter = found[-1] if found else None
    return letter if letter in options else None


def chat(base_url, model, key, messages, max_tokens, timeout):
    url = base_url.rstrip("/") + "/chat/completions"
    if not url.startswith("http://127.0.0.1:"):
        raise ValueError("Only literal loopback inference endpoints are allowed.")
    body = {"model": model, "messages": messages, "temperature": 0, "max_tokens": max_tokens, "stream": False}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with opener.open(request, timeout=timeout) as response:
        obj = json.load(response)
    message = obj["choices"][0]["message"]
    return (message.get("content") or ""), obj.get("usage") or {}


def read_jsonl(path):
    return [json.loads(x) for x in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def cmd_run(args):
    rows = read_jsonl(args.bench)
    if args.limit:
        rows = rows[:args.limit]
    out = pathlib.Path(args.out)
    done = {r["id"] for r in read_jsonl(out)} if out.exists() else set()  # resumable
    key = pathlib.Path(args.api_key_file).expanduser().read_text().strip() if args.api_key_file else None
    os.umask(0o077)
    with out.open("a", encoding="utf-8") as handle:
        for row in rows:
            if row["id"] in done:
                continue
            started = time.monotonic()
            try:
                text, usage = chat(args.base_url, args.model, key,
                                   [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": prompt(row)}], args.max_tokens, args.timeout)
                error = None
            except Exception as exc:  # a transport failure is a recorded wrong answer
                text, usage, error = "", {}, f"{type(exc).__name__}: {str(exc)[:200]}"
            pred = parse_answer(text, row["options"])
            handle.write(json.dumps({"id": row["id"], "bench": row["bench"], "label": args.label,
                                     "pred": pred, "answer": row["answer"], "correct": pred == row["answer"],
                                     "error": error, "usage": usage, "text": text,
                                     "seconds": round(time.monotonic() - started, 3)}) + "\n")
            handle.flush()


# ------------------------------------------------------------------ score / compare
def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(centre - half, 4), round(centre + half, 4))


def summarize(records):
    by = {}
    for r in records:
        by.setdefault(r["bench"], []).append(r)
    out = {}
    for bench, rows in sorted(by.items()):
        k = sum(r["correct"] for r in rows)
        out[bench] = {"correct": k, "total": len(rows), "accuracy": round(k / len(rows), 4),
                      "wilson95": wilson(k, len(rows)), "invalid": sum(r["pred"] is None for r in rows),
                      "errors": sum(bool(r.get("error")) for r in rows),
                      "mean_seconds": round(sum(r["seconds"] for r in rows) / len(rows), 3)}
    return out


def cmd_score(args):
    records = read_jsonl(args.records)
    print(json.dumps({"label": records[0]["label"] if records else None,
                      "records_sha256": sha256(args.records), "benchmarks": summarize(records)},
                     indent=2, sort_keys=True))


def sign_test(gained, lost):
    n = gained + lost
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(gained, lost) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def cmd_compare(args):
    a = {r["id"]: r for r in read_jsonl(args.before)}
    b = {r["id"]: r for r in read_jsonl(args.after)}
    shared = sorted(set(a) & set(b))
    gained = sum(b[i]["correct"] and not a[i]["correct"] for i in shared)
    lost = sum(a[i]["correct"] and not b[i]["correct"] for i in shared)
    print(json.dumps({"paired": len(shared), "gained": gained, "lost": lost,
                      "before_correct": sum(a[i]["correct"] for i in shared),
                      "after_correct": sum(b[i]["correct"] for i in shared),
                      "sign_test_p_two_sided": round(sign_test(gained, lost), 6)}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("freeze")
    p.add_argument("--out", required=True)
    p.add_argument("--pin", help="Re-freeze at a committed manifest's revisions and verify every hash.")
    p = sub.add_parser("run")
    p.add_argument("--bench", required=True)
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--api-key-file")
    p.add_argument("--limit", type=int)
    p.add_argument("--max-tokens", type=int, default=1024)
    p.add_argument("--timeout", type=float, default=600)
    p = sub.add_parser("score")
    p.add_argument("--records", required=True)
    p = sub.add_parser("compare")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    args = parser.parse_args(argv)
    {"freeze": cmd_freeze, "run": cmd_run, "score": cmd_score, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
