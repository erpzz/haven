"""Shared plumbing for Phase 0: pinned imports, hashing, salted commitments, JSONL I/O.

Import order matters. Main-branch modules (adjudicated/, distillation/tool_sft/) are imported
from the repository first, then the pinned PR #115 harness from _deps/. Every file is checked
against deps.json before use, so the harness that filters training data is byte-for-byte the
one that produced Kaggle run 1.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import secrets
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEPS_DIR = pathlib.Path(os.environ.get("PHASE0_DEPS", HERE / "_deps"))
SPEC = json.loads((HERE / "deps.json").read_text())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(pathlib.Path(path).read_bytes())


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def verify_pins() -> list[str]:
    problems = []
    for path, want in SPEC["main"]["files"].items():
        p = REPO / path
        got = sha256_file(p) if p.exists() else "missing"
        if got != want:
            problems.append(f"main:{path} {got[:12]} != {want[:12]}")
    for src in SPEC["sources"]:
        for path, want in src["files"].items():
            p = DEPS_DIR / path
            got = sha256_file(p) if p.exists() else "missing"
            if got != want:
                problems.append(f"{src['name']}:{path} {got[:12]} != {want[:12]} (run fetch_deps.py)")
    return problems


_problems = verify_pins()
if _problems and not os.environ.get("PHASE0_ALLOW_UNPINNED"):
    raise ImportError("Phase 0 dependencies do not match deps.json:\n  " + "\n  ".join(_problems))

BAKEOFF = REPO / "labs" / "intelligence-bakeoff"
SYSTEM0 = DEPS_DIR / "labs" / "intelligence-bakeoff" / "system0"
QUERYWRITER = DEPS_DIR / "labs" / "intelligence-bakeoff" / "querywriter"
PURPLE = DEPS_DIR / "labs" / "purple-copilot-apm"
for p in (BAKEOFF / "adjudicated", BAKEOFF / "distillation" / "tool_sft", BAKEOFF):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import adjudicator  # noqa: E402,F401  (main)
import agent  # noqa: E402,F401  (main)
import bench  # noqa: E402,F401  (main)
import generator  # noqa: E402,F401  (main)
import world as contract  # noqa: E402,F401  (main: TOOL_SCHEMAS, dispatch)

for p in (SYSTEM0, QUERYWRITER):
    if str(p) not in sys.path:
        sys.path.append(str(p))

import checks  # noqa: E402,F401  (PR #115, pinned)
import enforce  # noqa: E402,F401  (PR #115, pinned)
import bench_x  # noqa: E402,F401  (PR #115, pinned)

FULL = dict(bench_x.ARMS["full"])          # advisory + gateway + verifier + one correction
REPLAY = dict(FULL, correction=False)      # a fixed answer cannot revise itself
AUTH_POLICIES = ("P1_proposal_requires_request", "P2_named_owner_only")


# ------------------------------------------------------------------ JSONL
def read_jsonl(path):
    with open(path, encoding="utf-8") as h:
        return [json.loads(line) for line in h if line.strip()]


def write_jsonl(path, rows, mode="w"):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as h:
        for row in rows:
            h.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def refuse_overwrite(*paths):
    for p in paths:
        if pathlib.Path(p).exists():
            raise SystemExit(f"{p} exists; refusing to overwrite.")


def private_dir(path) -> pathlib.Path:
    """A directory for secrets (seeds, salts, gold before reveal). Never inside the Git tree."""
    p = pathlib.Path(path).resolve()
    try:
        p.relative_to(REPO.resolve())
    except ValueError:
        p.mkdir(parents=True, exist_ok=True, mode=0o700)
        return p
    raise SystemExit(f"{p} is inside the repository; secrets must live outside Git.")


# ------------------------------------------------------------------ salted commitments
def new_salt() -> str:
    return secrets.token_hex(32)


COMMITMENT_RULE = ("SHA-256(raw 32-byte salt || uint64 big-endian byte length of P || P), P = canonical JSON "
                   "(sort_keys, separators (',', ':'), UTF-8). Amendment 1, section 5: unambiguously framed.")


def commit(salt_hex: str, payload) -> str:
    """Framed commitment: salt, then the payload's length, then the payload (no concatenation ambiguity)."""
    salt = bytes.fromhex(salt_hex)
    if len(salt) != 32:
        raise ValueError("salt must be 32 bytes")
    body = canonical(payload)
    return sha256_bytes(salt + len(body).to_bytes(8, "big") + body)


def check_commitment(salt_hex: str, payload, digest: str) -> bool:
    return secrets.compare_digest(commit(salt_hex, payload), digest)


# ------------------------------------------------------------------ the real harness
def strip_annotations(messages):
    """Tool messages without System 0 advisory lines (the scripted oracle parses tool JSON)."""
    return [dict(m, content=m["content"].split("\n[runtime check]")[0]) if m.get("role") == "tool" else m
            for m in messages]


class Oracle:
    """The generator's scripted solver under the full harness (same wrapper as PR #115's tests)."""

    def __init__(self, episode):
        self.inner = agent.OracleBackend(episode)

    def step(self, messages, tools):
        return self.inner.step(strip_annotations(messages), tools)


def run_harness(backend, episode: dict, mechanisms: dict) -> dict:
    """One episode through PR #115's loop (enforce.run_episode_x via bench_x.run_x)."""
    return bench_x.run_x(backend, episode, mechanisms)


def judge(record: dict, episode: dict) -> dict:
    """Run-1 metrics, Amendment 1's three score views, and the keep rule.

    model-clean:     the model's first answer and the trace at that point pass, with no blocked call before it
    corrected-model: the final answer (after at most one verifier revision) passes, with no blocked call
    final-system:    the final answer passes, whatever the harness did
    keep (W1/W2):    model-clean pass, zero blocked or duplicate calls anywhere, transport ok
                     (Amendment 2, D1: a pass that needed a verifier correction is not training data)
    """
    m = bench_x.episode_metrics(record, episode)
    attempts = record.get("attempts") or []
    blocked = [a for a in attempts if not a["executed"]]
    blocked_main = [a for a in blocked if a.get("phase") != "correction"]
    m["blocked_any"] = len(blocked)
    m["views"] = {"model_clean": bool(m["transport_ok"] and m["raw_pass"] and not blocked_main),
                  "corrected_model": bool(m["transport_ok"] and m["pass"] and not blocked),
                  "final_system": bool(m["transport_ok"] and m["pass"])}
    m["keep"] = bool(m["transport_ok"] and m["views"]["model_clean"] and not blocked)
    return m


def load_querywriter():
    """(tenant, run) from PR #118. run.py is loaded by path: tool_sft also has a run.py."""
    import importlib.util
    import tenant
    if "querywriter_run" not in sys.modules:
        spec = importlib.util.spec_from_file_location("querywriter_run", QUERYWRITER / "run.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["querywriter_run"] = mod
        spec.loader.exec_module(mod)
    return tenant, sys.modules["querywriter_run"]


def code_hashes(names) -> dict:
    return {n: sha256_file(HERE / n) for n in names}
