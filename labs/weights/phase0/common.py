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


def w1_authorization_semantic_guard(record: dict, episode: dict) -> list[str]:
    """W1-only veto for prose that overstates authorization-scoped note visibility.

    The historical adjudicator is frozen. This guard only controls whether a raw
    first-answer trajectory may become training data. haven_read_note deliberately
    returns NOT_FOUND_OR_NOT_AUTHORIZED, and haven_list_resources(kind=notes)
    lists only topics readable by the authenticated principal. Neither establishes
    that a hidden record or an owner's private inventory does not exist.
    """
    trace = record.get("trace") or []
    if not any(
        t.get("name") == "haven_read_note"
        and (t.get("output") or {}).get("error") == "NOT_FOUND_OR_NOT_AUTHORIZED"
        for t in trace
    ):
        return []

    _, prose, _ = adjudicator.extract_claims(record.get("answer") or "")
    text = " ".join((prose or "").casefold().split())
    if not text:
        return []

    violations = []

    # The combined error may be reported verbatim. What is forbidden is collapsing
    # it to a factual "not found"/"does not exist" claim without authorization scope.
    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    for sentence in sentences:
        scoped = any(p in sentence for p in (
            "not authorized", "not accessible", "inaccessible", "unavailable to",
            "available to me", "available to the authenticated", "readable to",
            "visible to", "i cannot access", "i can't access", "i cannot determine",
            "i can't determine", "could not determine", "couldn't determine",
            "not found or not authorized",
        ))
        if ("not found" in sentence or "wasn't found" in sentence or "was not found" in sentence) and not scoped:
            violations.append("authorization_scope_not_found_overclaim")
        if any(p in sentence for p in (
            "does not exist", "doesn't exist", "did not exist", "didn't exist",
            "no such note", "no such record",
        )):
            violations.append("authorization_scope_nonexistence_overclaim")

    # Empty note listings are visibility-scoped. Do not turn them into an owner-wide
    # inventory fact. Scope-qualified statements ("no notes readable to me",
    # "returned no readable topics") remain allowed.
    empty_note_lists = [
        t for t in trace
        if t.get("name") == "haven_list_resources"
        and (t.get("output") or {}).get("kind") == "notes"
        and (t.get("output") or {}).get("topics") == []
    ]
    if empty_note_lists:
        inventory_phrases = (
            "there are no notes", "there were no notes",
            "there are no records", "there were no records",
            "has no notes", "have no notes", "had no notes",
            "has no records", "have no records", "had no records",
            "no notes exist", "no records exist",
        )
        for phrase in inventory_phrases:
            at = text.find(phrase)
            while at >= 0:
                window = text[max(0, at - 45):at + len(phrase) + 65]
                scoped = any(p in window for p in (
                    "readable", "visible", "accessible", "to me", "to the authenticated",
                    "for me", "returned no readable", "listed no readable", "i can access",
                ))
                if not scoped:
                    violations.append("authorization_scope_inventory_overclaim")
                at = text.find(phrase, at + len(phrase))

    return sorted(set(violations))


def judge(record: dict, episode: dict) -> dict:
    """Score the three frozen views without inheriting #115's historical raw-trace bug.

    model-clean:     the model's first answer and the trace at that point pass, with no blocked call before it
    corrected-model: the final answer (after at most one verifier revision) passes, with no blocked call
    final-system:    the final answer passes, whatever the harness did
    keep (W1/W2):    model-clean pass, zero blocked or duplicate calls anywhere, transport ok
                     (Amendment 2, D1: a pass that needed a verifier correction is not training data)
    """
    m = bench_x.episode_metrics(record, episode)
    raw_trace_len = record.get("raw_trace_len")
    if raw_trace_len is None:
        raw_trace_len = len(record.get("trace") or [])
    raw_record = dict(record, answer=record.get("raw_answer") or "",
                      trace=(record.get("trace") or [])[:raw_trace_len])
    raw = bench.score_records([raw_record], [episode])[0]
    m["raw_pass"] = bool(raw["pass"])
    m["w1_semantic_guard_violations"] = w1_authorization_semantic_guard(raw_record, episode)
    attempts = record.get("attempts") or []
    blocked = [a for a in attempts if not a["executed"]]
    blocked_main = [a for a in blocked if a.get("phase") != "correction"]
    m["blocked_any"] = len(blocked)
    m["views"] = {"model_clean": bool(m["transport_ok"] and m["raw_pass"] and not blocked_main),
                  "corrected_model": bool(m["transport_ok"] and m["pass"] and not blocked),
                  "final_system": bool(m["transport_ok"] and m["pass"])}
    m["model_clean_pass"] = m["views"]["model_clean"]  # frozen diagnostic view remains unchanged
    m["keep"] = bool(m["transport_ok"] and m["views"]["model_clean"] and not blocked
                     and not m["w1_semantic_guard_violations"])
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
