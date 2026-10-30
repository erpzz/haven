"""SPEC-2 speech-to-text evaluation: frozen LibriSpeech subsets, WER and real-time factor.

  freeze  pin hf-audio/open-asr-leaderboard, take every k-th utterance of test.clean/test.other, write
          private audio files plus a manifest with references, durations and hashes
  run     transcribe with a local transformers pipeline or a loopback /v1/audio/transcriptions server
  score   corpus WER per split (simple normalizer: lowercase, drop punctuation) and real-time factor

The owner's household recordings, when added, stay private like everything under the output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import time
import urllib.request
import uuid

REPO = "hf-audio/open-asr-leaderboard"
SPLITS = {"clean": "librispeech/test.clean-00000-of-00001.parquet",
          "other": "librispeech/test.other-00000-of-00001.parquet"}


def normalize(text):
    text = re.sub(r"[^a-z0-9' ]+", " ", str(text).lower().replace("-", " "))
    return " ".join(text.replace(" '", " ").replace("' ", " ").split())


def edit_distance(ref, hyp):
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


def corpus_wer(pairs):
    errors = words = 0
    for ref, hyp in pairs:
        r, h = normalize(ref).split(), normalize(hyp).split()
        errors += edit_distance(r, h)
        words += len(r)
    return errors / words if words else None


def cmd_freeze(args):
    import pandas as pd
    import soundfile as sf
    from huggingface_hub import HfApi, hf_hub_download
    out = pathlib.Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; frozen sets are never silently regenerated.")
    (out / "audio").mkdir(parents=True)
    os.umask(0o077)
    revision = HfApi().dataset_info(REPO).sha
    rows = []
    for split, filename in SPLITS.items():
        df = pd.read_parquet(hf_hub_download(REPO, filename, repo_type="dataset", revision=revision))
        step = max(1, len(df) // args.per_split)
        for n, (_, r) in enumerate(df.iloc[::step].head(args.per_split).iterrows()):
            data, rate = sf.read(io.BytesIO(r["audio"]["bytes"]))
            path = out / "audio" / f"{split}-{n:04d}.wav"
            sf.write(path, data, rate, subtype="PCM_16")
            rows.append({"id": f"{split}-{n:04d}", "split": split, "audio": str(path.relative_to(out)),
                         "reference": r["text"], "seconds": round(len(data) / rate, 3)})
    (out / "items.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    manifest = {"schema": "haven-spec2-stt-manifest-1", "source": REPO, "revision": revision,
                "licence": "CC-BY-4.0 (LibriSpeech)", "per_split": args.per_split,
                "items": len(rows), "audio_seconds": round(sum(r["seconds"] for r in rows), 1),
                "items_sha256": hashlib.sha256((out / "items.jsonl").read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def _multipart(path, model):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for name, value in (("model", model), ("response_format", "json")):
        body.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    body.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.wav\"\r\n"
               "Content-Type: audio/wav\r\n\r\n".encode())
    body.write(pathlib.Path(path).read_bytes())
    body.write(f"\r\n--{boundary}--\r\n".encode())
    return body.getvalue(), f"multipart/form-data; boundary={boundary}"


def make_transcriber(args):
    if args.backend == "openai":
        url = args.base_url.rstrip("/") + "/audio/transcriptions"
        if not url.startswith("http://127.0.0.1:"):
            raise ValueError("Only literal loopback inference endpoints are allowed.")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def transcribe(path):
            data, ctype = _multipart(path, args.model)
            req = urllib.request.Request(url, data=data, headers={"Content-Type": ctype})
            with opener.open(req, timeout=args.timeout) as response:
                return json.load(response).get("text", "")
        return transcribe
    from transformers import pipeline
    asr = pipeline("automatic-speech-recognition", model=args.model, revision=args.revision, device=args.device)
    kwargs = {"generate_kwargs": {"language": "en", "task": "transcribe"}} if "whisper" in args.model else {}
    return lambda path: asr(str(path), **kwargs)["text"]


def cmd_run(args):
    root = pathlib.Path(args.data)
    items = [json.loads(x) for x in (root / "items.jsonl").read_text().splitlines() if x.strip()]
    if args.limit:
        items = items[:args.limit]
    out = pathlib.Path(args.out)
    done = {json.loads(x)["id"] for x in out.read_text().splitlines()} if out.exists() else set()
    transcribe = make_transcriber(args)
    os.umask(0o077)
    with out.open("a", encoding="utf-8") as handle:
        for it in items:
            if it["id"] in done:
                continue
            started = time.monotonic()
            try:
                text, error = transcribe(root / it["audio"]), None
            except Exception as exc:
                text, error = "", f"{type(exc).__name__}: {str(exc)[:200]}"
            elapsed = time.monotonic() - started
            handle.write(json.dumps({"id": it["id"], "split": it["split"], "label": args.label,
                                     "reference": it["reference"], "hypothesis": text, "error": error,
                                     "seconds": round(elapsed, 3), "audio_seconds": it["seconds"]}) + "\n")
            handle.flush()


def cmd_score(args):
    rows = [json.loads(x) for x in pathlib.Path(args.records).read_text().splitlines() if x.strip()]
    report = {"label": rows[0]["label"] if rows else None, "splits": {}}
    for split in sorted({r["split"] for r in rows}):
        sel = [r for r in rows if r["split"] == split]
        report["splits"][split] = {
            "utterances": len(sel), "wer": round(corpus_wer([(r["reference"], r["hypothesis"]) for r in sel]), 4),
            "errors": sum(bool(r["error"]) for r in sel),
            "real_time_factor": round(sum(r["seconds"] for r in sel) / sum(r["audio_seconds"] for r in sel), 4)}
    print(json.dumps(report, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("freeze")
    p.add_argument("--out", required=True)
    p.add_argument("--per-split", type=int, default=300)
    p = sub.add_parser("run")
    p.add_argument("--data", required=True)
    p.add_argument("--backend", choices=("transformers", "openai"), default="transformers")
    p.add_argument("--model", required=True)
    p.add_argument("--revision")
    p.add_argument("--base-url")
    p.add_argument("--device", default="cpu")
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--timeout", type=float, default=300)
    p = sub.add_parser("score")
    p.add_argument("--records", required=True)
    args = parser.parse_args(argv)
    {"freeze": cmd_freeze, "run": cmd_run, "score": cmd_score}[args.command](args)


if __name__ == "__main__":
    main()
