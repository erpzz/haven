"""Bounded publication scope/content check; complements manual review.

Examines only this campaign's changed and untracked files. It never prints
matched secret material, touches original checkouts or publishes anything.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = "8e1304caf82c0a889eeaea7691db7b9d7b98c526"
ALLOWED = ("labs/ip01/", "campaigns/IP-01/ip01-v2-20260929/")
DENIED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".pem", ".key", ".log", ".gguf", ".safetensors", ".whl"}
SECRET_PATTERNS = {
    "github_token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{32,})"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "provider_key": re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def check():
    # Diff from setup includes committed, staged and current worktree edits.
    changed = git("diff", "--name-only", "-z", BASE).decode("utf-8").split("\0")
    new = git("ls-files", "--others", "--exclude-standard", "-z").decode("utf-8").split("\0")
    names = sorted(set(changed + new) - {""})
    findings, files = [], []
    for name in names:
        path = ROOT / name
        if not name.startswith(ALLOWED):
            findings.append({"path": name, "kind": "OUTSIDE_TRACKED_SCOPE"})
            continue
        if not path.exists():
            findings.append({"path": name, "kind": "DELETION_REQUIRES_EXPLICIT_REVIEW"})
            continue
        if path.is_symlink():
            findings.append({"path": name, "kind": "SYMLINK_NOT_PUBLICATION_READY"})
            continue
        if path.suffix.lower() in DENIED_SUFFIXES or path.name == ".env" or ".ip01-runtime" in path.parts:
            findings.append({"path": name, "kind": "PRIVATE_RUNTIME_OR_BINARY_TYPE"})
        if path.stat().st_size > 5 * 1024 * 1024:
            findings.append({"path": name, "kind": "OVERSIZE_REQUIRES_REVIEW"})
            continue
        data = path.read_bytes()
        files.append({"path": name, "sha256_worktree": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        for kind, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(data):
                findings.append({"path": name, "kind": kind, "line": data[:match.start()].count(b"\n") + 1, "content": "REDACTED"})
        if path.suffix == ".json":
            try:
                json.loads(data)
            except (ValueError, UnicodeDecodeError):
                findings.append({"path": name, "kind": "INVALID_JSON"})
    exclusion = subprocess.run(["git", "check-ignore", ".ip01-runtime/probe"], cwd=ROOT, capture_output=True).returncode == 0
    if not exclusion:
        findings.append({"path": ".ip01-runtime/", "kind": "PRIVATE_EXCLUSION_MISSING"})
    return {"scope_base": BASE, "state": "CHECKS_PASS_MANUAL_REVIEW_STILL_REQUIRED" if not findings else "FINDINGS",
            "checked_files": files, "findings": findings, "private_runtime_excluded": exclusion,
            "limits": "Pattern checks do not prove absence of personal data, protected expected answers or all credential forms. Review intended public source/reports explicitly."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt")
    args = parser.parse_args()
    result = check()
    if args.receipt:
        path = Path(args.receipt).resolve()
        allowed = (ROOT / "campaigns/IP-01/ip01-v2-20260929").resolve()
        private = (ROOT / ".ip01-runtime").resolve()
        if allowed not in path.parents and private not in path.parents:
            raise ValueError("Receipt must be campaign-owned")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"state": result["state"], "checked_files": len(result["checked_files"]), "findings": result["findings"]}))
    return 0 if not result["findings"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
