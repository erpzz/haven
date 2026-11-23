#!/usr/bin/env python3
"""Extract the pinned files listed in deps.json into _deps/, hash-checked.

  python3 fetch_deps.py            # from labs/weights/phase0/, inside a git clone of erpzz/haven
  python3 fetch_deps.py --verify   # check what is already in _deps/ without fetching

Each file is read with `git show <commit>:<path>` from the exact commit in deps.json. If the
commit is not in the local clone it is fetched with a bounded depth. A file whose sha256
differs from deps.json is refused, so a moved branch can never change what Phase 0 runs.
Nothing is copied into the tracked tree; _deps/ is gitignored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEPS = HERE / "_deps"


def repo_root() -> pathlib.Path:
    out = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, check=True)
    return pathlib.Path(out.stdout.strip())


def have(root, commit, path) -> bool:
    return subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{commit}:{path}"],
                          capture_output=True).returncode == 0


def fetch_commit(root, commit):
    r = subprocess.run(["git", "-C", str(root), "fetch", "-q", "--depth=1", "origin", commit],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"cannot fetch {commit}: {r.stderr.strip()[:300]}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args(argv)
    spec = json.loads((HERE / "deps.json").read_text())
    problems, written = [], 0
    root = None if args.verify else repo_root()
    for src in spec["sources"]:
        for path, want in src["files"].items():
            dest = DEPS / path
            if args.verify:
                got = sha256(dest.read_bytes()) if dest.exists() else "missing"
            else:
                if not have(root, src["commit"], path):
                    fetch_commit(root, src["commit"])
                data = subprocess.run(["git", "-C", str(root), "show", f"{src['commit']}:{path}"],
                                      capture_output=True, check=True).stdout
                got = sha256(data)
                if got == want:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                    written += 1
            if got != want:
                problems.append(f"{src['name']}:{path} sha256 {got[:12]} != pinned {want[:12]}")
    print(json.dumps({"deps_dir": str(DEPS), "written": written, "problems": problems}, indent=2))
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    sys.exit(main())
