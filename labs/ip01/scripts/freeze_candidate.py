"""Record a committed candidate and its actual local bytes without publishing secrets.

A freeze is an identity receipt, not test acceptance. Final reviews must name
its digest and candidate commit. Later administrative commits do not change
the evaluated identity; source changes require a new freeze and affected check.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = ROOT / ".ip01-runtime"
CAMPAIGN = ROOT / "campaigns/IP-01/ip01-v2-20260929"
EVALUATOR = ROOT.parent / "haven-ip01-runtime-20260929-eval"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def confined_file(value, roots):
    path = Path(value).resolve()
    if not any(root.resolve() in path.parents for root in roots):
        raise ValueError("Path must be inside the campaign, private runtime, or named evaluator scope")
    return path


def make_receipt(evaluator_manifest=None):
    changes = git("status", "--porcelain=v1", "--untracked-files=all", "--", "labs/ip01/")
    if changes.strip():
        raise ValueError("Commit all candidate source/test/dependency changes before freezing")
    commit = git("rev-parse", "HEAD").decode().strip()
    files = []
    for name in sorted(filter(None, git("ls-files", "-z", "labs/ip01/").decode("utf-8").split("\0"))):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Candidate contains a missing file or symlink")
        raw = path.read_bytes()
        committed = git("show", f"{commit}:{name}")
        files.append({"path": name, "worktree_sha256": digest(raw), "commit_bytes_sha256": digest(committed),
                      "bytes": len(raw), "git_blob": git("rev-parse", f"{commit}:{name}").decode().strip()})
    if not files:
        raise ValueError("No tracked candidate files")
    packages = sorted(({"name": d.metadata["Name"], "version": d.version} for d in importlib.metadata.distributions()),
                      key=lambda d: d["name"].lower())
    receipt = {"schema": "ip01.candidate-freeze.v1", "created_at": datetime.now(timezone.utc).isoformat(),
               "candidate_commit": commit, "candidate_tree": git("rev-parse", f"{commit}:labs/ip01").decode().strip(),
               "source_files": files, "source_manifest_sha256": digest(canonical(files)),
               "environment": {"system": platform.system(), "release": platform.release(),
                               "machine": platform.machine(), "python": platform.python_version(),
                               "implementation": platform.python_implementation(), "packages": packages},
               "acceptance": "NOT_ESTABLISHED_BY_IDENTITY_RECEIPT"}
    identity_file = PRIVATE / "model/identity.json"
    if identity_file.exists():
        identity = json.loads(identity_file.read_bytes())
        receipt["model_identity_file_sha256"] = digest(identity_file.read_bytes())
        receipt["model_identity"] = {key: identity[key] for key in (
            "manifest_sha256", "runtime_sha256", "template_sha256", "preprocessor_sha256", "prompt_sha256", "envelope"
        ) if key in identity}
    else:
        receipt["model_identity"] = "NOT_PREPARED"
    if evaluator_manifest:
        path = confined_file(evaluator_manifest, [EVALUATOR])
        receipt["evaluator_manifest_sha256"] = digest(path.read_bytes())
        receipt["evaluator_protection"] = "MUST_BE_ESTABLISHED_SEPARATELY"
    receipt["receipt_payload_sha256"] = digest(canonical(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--evaluator-manifest")
    args = parser.parse_args()
    path = confined_file(args.output, [CAMPAIGN, PRIVATE])
    receipt = make_receipt(args.evaluator_manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    # A prior frozen identity is immutable, including failed candidates.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"candidate_commit": receipt["candidate_commit"],
                      "receipt_payload_sha256": receipt["receipt_payload_sha256"],
                      "files": len(receipt["source_files"])}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
