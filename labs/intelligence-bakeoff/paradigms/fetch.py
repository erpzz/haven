#!/usr/bin/env python3
"""Download preregistered GGUFs at a pinned revision and verify size and SHA-256.

Resumable (HTTP Range onto a .part file). The hash is computed while streaming;
on resume the existing prefix is re-hashed first. Written pages are flushed and
dropped from the page cache as the download proceeds, so a multi-GB fetch does
not evict a running model's memory-mapped weights. Nothing is executed or
loaded; a file is renamed into place only after its digest matches.

  fetch.py --models-dir DIR [--prereg FILE] [--only id,id] [--execute]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
PREREG = HERE / "PREREGISTRATION.json"
CHUNK = 4 << 20
DROP_EVERY = 256 << 20
ALLOWED_HOST = "https://huggingface.co/"


def load_models(path=PREREG):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["models"]


def resolve_url(model):
    """Pinned-revision URL; a branch name or a non-40-hex revision is refused."""
    rev = model["revision"]
    if len(rev) != 40 or any(c not in "0123456789abcdef" for c in rev):
        raise ValueError(f"{model['id']}: revision must be a full commit SHA")
    for part in (model["repo"], model["file"]):
        if ".." in part or part.startswith("/") or "?" in part or "#" in part:
            raise ValueError(f"{model['id']}: unsafe repo or file name")
    return f"{ALLOWED_HOST}{model['repo']}/resolve/{rev}/{model['file']}"


def drop_cache(fd):
    os.fsync(fd)
    if hasattr(os, "posix_fadvise"):
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)


def hash_prefix(path, digest):
    size = 0
    with open(path, "rb") as handle:
        while block := handle.read(CHUNK):
            digest.update(block)
            size += len(block)
        if hasattr(os, "posix_fadvise"):
            os.posix_fadvise(handle.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return size


def verify_file(path, model):
    digest = hashlib.sha256()
    size = hash_prefix(path, digest)
    return size == model["size_bytes"] and digest.hexdigest() == model["sha256"]


def fetch(model, models_dir, opener=None, log=print):
    models_dir = pathlib.Path(models_dir)
    final = models_dir / model["file"]
    if final.exists():
        if not verify_file(final, model):
            raise ValueError(f"{final.name} exists but does not match its registered digest")
        return {"id": model["id"], "status": "PRESENT_VERIFIED", "downloaded_bytes": 0}
    part = final.with_name(final.name + ".part")
    digest = hashlib.sha256()
    have = hash_prefix(part, digest) if part.exists() else 0
    if have > model["size_bytes"]:
        raise ValueError(f"{part.name} is larger than the registered size")
    opener = opener or urllib.request.build_opener()
    request = urllib.request.Request(resolve_url(model), headers={"User-Agent": "haven-paradigms/1"})
    if have:
        request.add_header("Range", f"bytes={have}-")
    started, got = time.monotonic(), 0
    if have < model["size_bytes"]:
        with opener.open(request, timeout=60) as response:
            if have and response.status != 206:
                raise ValueError("server ignored the Range request; refusing to append")
            fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                since_drop = 0
                while block := response.read(CHUNK):
                    os.write(fd, block)
                    digest.update(block)
                    got += len(block)
                    since_drop += len(block)
                    if have + got > model["size_bytes"]:
                        raise ValueError("download exceeds the registered size")
                    if since_drop >= DROP_EVERY:
                        drop_cache(fd)
                        since_drop = 0
                        log(f"{model['id']}: {(have + got) >> 20} / {model['size_bytes'] >> 20} MiB")
                drop_cache(fd)
            finally:
                os.close(fd)
    if have + got != model["size_bytes"] or digest.hexdigest() != model["sha256"]:
        part.rename(part.with_name(part.name + ".bad"))
        raise ValueError(f"{model['id']}: size or SHA-256 mismatch; quarantined as .bad")
    part.rename(final)
    os.chmod(final, 0o600)
    return {"id": model["id"], "status": "DOWNLOADED_VERIFIED", "downloaded_bytes": got,
            "seconds": round(time.monotonic() - started, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", type=pathlib.Path, required=True)
    ap.add_argument("--prereg", type=pathlib.Path, default=PREREG)
    ap.add_argument("--only", help="comma-separated model ids")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args(argv)
    models = [m for m in load_models(args.prereg) if m.get("source") == "download"]
    if args.only:
        wanted = set(args.only.split(","))
        models = [m for m in models if m["id"] in wanted]
    if not args.execute:
        for m in models:
            print("PLAN", m["id"], resolve_url(m), m["size_bytes"])
        return 0
    os.umask(0o077)
    args.models_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipts = []
    for m in models:
        try:
            receipts.append(fetch(m, args.models_dir))
        except Exception as error:  # record and continue; a failed model is simply not run
            receipts.append({"id": m["id"], "status": "FAILED", "error": f"{type(error).__name__}: {error}"[:300]})
        print(json.dumps(receipts[-1]), flush=True)
    # Never overwrite round 1's receipt with a later preregistration's fetch.
    name = "fetch-receipt.json" if args.prereg.resolve() == PREREG else f"fetch-receipt-{args.prereg.stem}.json"
    (args.models_dir / name).write_text(json.dumps(receipts, indent=2) + "\n")
    return 0 if all(r["status"] != "FAILED" for r in receipts) else 1


if __name__ == "__main__":
    sys.exit(main())
