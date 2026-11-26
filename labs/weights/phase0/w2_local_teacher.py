#!/usr/bin/env python3
"""Frozen local/open-weight W2 teacher runner.

This lane is deliberately separate from the Astra stepwise exchange.  It prepares the
99-episode metadata-only census, binds the Qwen3.6/llama.cpp execution identity, records
exactly one terminal trajectory per slot, and projects only model-clean traces through
the shared Phase-0 SFT code.

The CPU-only preparation command is safe to run before a GGUF is present.  The run
command measures and binds the exact GGUF and llama-server bytes before the first model
request.  A slot is claimed durably before inference; a claimed slot without a valid
terminal receipt becomes an interrupted terminal failure on resume and is never retried.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Callable

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import astra_batch  # noqa: E402
import common  # noqa: E402
import sft  # noqa: E402


SCHEMA = "haven-w2-local-teacher-1"
MEMBERSHIP_SCHEMA = "haven-w2-local-teacher-membership-1"
RUNTIME_SCHEMA = "haven-w2-local-teacher-runtime-1"
GRID_SCHEMA = "haven-w2-local-teacher-grid-1"
RECEIPT_SCHEMA = "haven-w2-local-teacher-slot-1"
AUDIT_SCHEMA = "haven-w2-local-teacher-audit-1"
DEFAULT_LABEL = "w2-qwen36-35b-b1"
DEFAULT_PRIVATE = pathlib.Path.home() / "haven-private/weights/w1-pilot"

TEACHER = "qwen3.6-35b-a3b-q4"
MODEL_REPO = "unsloth/Qwen3.6-35B-A3B-GGUF"
MODEL_FILE = "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
MODEL_REVISION = "a483e9e6cbd595906af30beda3187c2663a1118c"
ENGINE_TAG = "b11146"
ORDER_DOMAIN = "haven-w2-qwen36-35b-v1"
TARGET_FAMILIES = {
    "conflict_rule", "distractor_resolve", "injection_output", "stale_premise"
}
EXPECTED_FAMILIES = {
    "chain3_conditional": 12,
    "chain_device_cause": 13,
    "conflict_report": 6,
    "conflict_rule": 14,
    "distractor_resolve": 14,
    "household_own": 3,
    "injection_output": 14,
    "no_tool": 1,
    "stale_note_chain": 9,
    "stale_premise": 13,
}
SAMPLING = {
    "temperature": 0.3,
    "top_p": 0.95,
    "seed": 0,
    "max_tokens": 700,
    "thinking": False,
}
SERVER = {
    "host": "127.0.0.1",
    "n_gpu_layers": 999,
    "parallel": 8,
    "context_total": 65536,
    "jinja": True,
    "flash_attention": True,
}


class LocalTeacherError(RuntimeError):
    pass


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_blob(obj) -> bytes:
    return canonical(obj) + b"\n"


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    rows = []
    for n, line in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LocalTeacherError(f"{path}: invalid JSON on line {n}: {exc}") from exc
        if not isinstance(obj, dict):
            raise LocalTeacherError(f"{path}: line {n} is not an object")
        rows.append(obj)
    return rows


def atomic_write(path, blob: bytes, *, mode=0o600):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as f:
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, mode)
    tmp.replace(path)


def write_once(path, blob: bytes, *, mode=0o600):
    path = pathlib.Path(path)
    if path.exists():
        if path.read_bytes() != blob:
            raise LocalTeacherError(f"existing file differs: {path}")
        return
    atomic_write(path, blob, mode=mode)


def metadata_rows(episodes_path) -> tuple[list[dict], str]:
    """Read only ID/family metadata for selection; all semantic fields are discarded."""
    rows = []
    seen = set()
    for n, obj in enumerate(read_jsonl(episodes_path), 1):
        eid, family = obj.get("id"), obj.get("family")
        if not isinstance(eid, str) or not isinstance(family, str):
            raise LocalTeacherError(f"{episodes_path}: line {n}: missing id/family metadata")
        if eid in seen:
            raise LocalTeacherError(f"{episodes_path}: duplicate episode id")
        seen.add(eid)
        rows.append({"id": eid, "family": family})
    return rows, sha256_file(episodes_path)


def verify_membership_file(path) -> dict:
    obj = load_json(path)
    if set(obj) != {"salt_hex", "payload", "commitment"}:
        raise LocalTeacherError(f"{path}: malformed membership wrapper")
    if not common.check_commitment(obj["salt_hex"], obj["payload"], obj["commitment"]):
        raise LocalTeacherError(f"{path}: membership commitment does not verify")
    ids = obj["payload"].get("episode_ids")
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        raise LocalTeacherError(f"{path}: malformed episode_ids")
    if len(ids) != len(set(ids)):
        raise LocalTeacherError(f"{path}: duplicate episode_ids")
    return obj


def hard_identity(paths) -> tuple[set[str], str, str, list[str]]:
    records = [verify_membership_file(p) for p in paths]
    run_ids = {x["payload"].get("run_id") for x in records}
    hard_hashes = {x["payload"].get("hard_set_sha256") for x in records}
    if len(run_ids) != 1 or None in run_ids:
        raise LocalTeacherError("hard memberships do not share one run_id")
    if len(hard_hashes) != 1 or None in hard_hashes:
        raise LocalTeacherError("hard memberships do not share one hard-set identity")
    ids = [eid for x in records for eid in x["payload"]["episode_ids"]]
    if len(ids) != len(set(ids)) or len(ids) != 55:
        raise LocalTeacherError(f"hard membership union must contain 55 unique IDs, got {len(set(ids))}")
    source_hashes = [sha256_file(p) for p in paths]
    return set(ids), next(iter(run_ids)), next(iter(hard_hashes)), source_hashes


def order_digest(run_id: str, episode_id: str) -> str:
    data = (ORDER_DOMAIN + "\0" + run_id + "\0" + episode_id).encode("utf-8")
    return sha256_bytes(data)


def select_population(rows: list[dict], hard_ids: set[str], run_id: str) -> tuple[list[str], dict]:
    by_id = {r["id"]: r["family"] for r in rows}
    missing = hard_ids - set(by_id)
    if missing:
        raise LocalTeacherError(f"{len(missing)} frozen hard IDs are absent from the W1 pool")
    chosen = set(hard_ids)
    chosen.update(r["id"] for r in rows if r["id"] not in hard_ids and r["family"] in TARGET_FAMILIES)
    ordered = sorted(chosen, key=lambda eid: (order_digest(run_id, eid), eid))
    histogram = dict(sorted(collections.Counter(by_id[eid] for eid in ordered).items()))
    if len(ordered) != 99:
        raise LocalTeacherError(f"frozen local-teacher population must contain 99 IDs, got {len(ordered)}")
    if histogram != EXPECTED_FAMILIES:
        raise LocalTeacherError(f"family histogram mismatch: {histogram}")
    return ordered, histogram


def membership_payload(*, label: str, run_id: str, hard_set_sha256: str,
                       episodes_sha256: str, hard_membership_sha256: list[str],
                       episode_ids: list[str], family_counts: dict) -> dict:
    return {
        "schema": MEMBERSHIP_SCHEMA,
        "label": label,
        "run_id": run_id,
        "episodes_sha256": episodes_sha256,
        "hard_set_sha256": hard_set_sha256,
        "hard_membership_sha256": hard_membership_sha256,
        "selection": "55 frozen hard IDs union every non-hard episode in the four frozen judgement families",
        "order_rule": f'SHA256("{ORDER_DOMAIN}\\0" || run_id || "\\0" || episode_id), then episode_id',
        "selected_count": len(episode_ids),
        "family_counts": family_counts,
        "episode_ids": episode_ids,
    }


def code_hashes() -> dict:
    names = ["w2_local_teacher.py", "common.py", "sft.py", "astra_batch.py", "deps.json",
             "kaggle/w2_local_teacher_kaggle.py"]
    return {name: sha256_file(HERE / name) for name in names}


def harness_hashes() -> dict:
    paths = {
        "common.py": HERE / "common.py",
        "deps.json": HERE / "deps.json",
        "tool_catalogue": None,
        "mechanisms": None,
    }
    return {
        "common.py": sha256_file(paths["common.py"]),
        "deps.json": sha256_file(paths["deps.json"]),
        "tool_catalogue": sha256_bytes(canonical(common.contract.TOOL_SCHEMAS)),
        "mechanisms": sha256_bytes(canonical(common.REPLAY)),
    }


def runtime_manifest(*, label: str, membership_path, episodes_path, membership: dict,
                     model_path=None, engine_path=None) -> dict:
    model_sha = sha256_file(model_path) if model_path else None
    engine_sha = sha256_file(engine_path) if engine_path else None
    return {
        "schema": RUNTIME_SCHEMA,
        "batch": label,
        "membership_commitment": membership["commitment"],
        "membership_file_sha256": sha256_file(membership_path),
        "episodes_sha256": sha256_file(episodes_path),
        "teacher": TEACHER,
        "model": {"repo": MODEL_REPO, "file": MODEL_FILE, "revision": MODEL_REVISION,
                  "sha256": model_sha, "sha256_status": "bound" if model_sha else "bind-before-inference"},
        "engine": {"tag": ENGINE_TAG, "binary_sha256": engine_sha,
                   "binary_sha256_status": "bound" if engine_sha else "bind-before-inference"},
        "sampling": dict(SAMPLING),
        "server": dict(SERVER),
        "attempts_per_episode": 1,
        "semantic_retries": 0,
        "reasoning_retries": 0,
        "harness": {"correction": False, **harness_hashes()},
        "runner_code_sha256": code_hashes(),
    }


def public_receipt(runtime: dict, membership: dict) -> dict:
    payload = membership["payload"]
    return {
        "schema": "haven-w2-local-teacher-prerun-receipt-1",
        "batch": runtime["batch"],
        "offered": payload["selected_count"],
        "family_counts": payload["family_counts"],
        "membership_commitment": membership["commitment"],
        "source": {
            "run_id": payload["run_id"],
            "episodes_sha256": payload["episodes_sha256"],
            "hard_set_sha256": payload["hard_set_sha256"],
            "hard_membership_sha256": payload["hard_membership_sha256"],
        },
        "teacher": runtime["teacher"],
        "model": runtime["model"],
        "engine": runtime["engine"],
        "sampling": runtime["sampling"],
        "server": runtime["server"],
        "attempts_per_episode": runtime["attempts_per_episode"],
        "harness_sha256": runtime["harness"],
        "runner_code_sha256": runtime["runner_code_sha256"],
    }


def prepare(args):
    private = common.private_dir(args.private_dir)
    metadata, episodes_sha = metadata_rows(args.episodes)
    hard_ids, run_id, hard_sha, hard_sources = hard_identity(args.hard_membership)
    ordered, histogram = select_population(metadata, hard_ids, run_id)
    payload = membership_payload(label=args.label, run_id=run_id, hard_set_sha256=hard_sha,
                                 episodes_sha256=episodes_sha, hard_membership_sha256=hard_sources,
                                 episode_ids=ordered, family_counts=histogram)
    membership_path = private / f"{args.label}.membership.private.json"
    if membership_path.exists():
        membership = verify_membership_file(membership_path)
        if membership["payload"] != payload:
            raise LocalTeacherError(f"existing membership payload differs: {membership_path}")
    else:
        salt = common.new_salt()
        membership = {"salt_hex": salt, "payload": payload, "commitment": common.commit(salt, payload)}
        atomic_write(membership_path, json_blob(membership))

    model_path = pathlib.Path(args.model_file).resolve() if args.model_file else None
    engine_path = pathlib.Path(args.engine_binary).resolve() if args.engine_binary else None
    if model_path and (not model_path.is_file() or model_path.name != MODEL_FILE):
        raise LocalTeacherError(f"model file must be an existing {MODEL_FILE}")
    if engine_path and not engine_path.is_file():
        raise LocalTeacherError("engine binary does not exist")
    runtime = runtime_manifest(label=args.label, membership_path=membership_path,
                               episodes_path=args.episodes, membership=membership,
                               model_path=model_path, engine_path=engine_path)
    runtime_path = private / f"{args.label}.runtime.private.json"
    write_once(runtime_path, json_blob(runtime))
    receipt = public_receipt(runtime, membership)
    receipt_path = private / f"{args.label}.pre-run.public.json"
    write_once(receipt_path, json.dumps(receipt, sort_keys=True, indent=2).encode() + b"\n", mode=0o644)
    print(json.dumps(receipt, indent=2, sort_keys=True))


def verify_runtime(runtime: dict, membership_path, episodes_path):
    if runtime.get("schema") != RUNTIME_SCHEMA:
        raise LocalTeacherError("wrong runtime schema")
    membership = verify_membership_file(membership_path)
    if runtime.get("membership_commitment") != membership["commitment"]:
        raise LocalTeacherError("runtime/membership commitment mismatch")
    if runtime.get("membership_file_sha256") != sha256_file(membership_path):
        raise LocalTeacherError("runtime/membership file hash mismatch")
    if runtime.get("episodes_sha256") != sha256_file(episodes_path):
        raise LocalTeacherError("runtime/episode pool hash mismatch")
    if runtime.get("teacher") != TEACHER or runtime.get("sampling") != SAMPLING or runtime.get("server") != SERVER:
        raise LocalTeacherError("frozen teacher settings changed")
    if runtime.get("attempts_per_episode") != 1 or runtime.get("semantic_retries") != 0:
        raise LocalTeacherError("frozen one-attempt contract changed")
    if runtime.get("engine", {}).get("tag") != ENGINE_TAG:
        raise LocalTeacherError("wrong engine tag")
    if runtime.get("model", {}).get("repo") != MODEL_REPO or runtime["model"].get("file") != MODEL_FILE \
            or runtime["model"].get("revision") != MODEL_REVISION:
        raise LocalTeacherError("wrong model identity")
    if runtime.get("runner_code_sha256") != code_hashes():
        raise LocalTeacherError("runner code changed since prepare")
    if runtime.get("harness") != {"correction": False, **harness_hashes()}:
        raise LocalTeacherError("harness/tool identity changed since prepare")
    return membership


def execution_identity(runtime: dict, membership: dict, model_file, engine_binary) -> dict:
    model_file, engine_binary = pathlib.Path(model_file), pathlib.Path(engine_binary)
    if model_file.name != MODEL_FILE or not model_file.is_file() or not engine_binary.is_file():
        raise LocalTeacherError("model/engine file identity is incomplete")
    model_sha, engine_sha = sha256_file(model_file), sha256_file(engine_binary)
    version = subprocess.run([str(engine_binary), "--version"], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    reported = version.stdout.strip()
    if version.returncode or not re.search(r"(?<!\d)11146(?!\d)", reported):
        raise LocalTeacherError("llama-server does not report the frozen b11146 build")
    if runtime["model"].get("sha256") not in (None, model_sha):
        raise LocalTeacherError("measured model SHA differs from prepared runtime")
    if runtime["engine"].get("binary_sha256") not in (None, engine_sha):
        raise LocalTeacherError("measured engine SHA differs from prepared runtime")
    return {
        "schema": "haven-w2-local-teacher-execution-identity-1",
        "batch": runtime["batch"],
        "membership_commitment": membership["commitment"],
        "teacher": TEACHER,
        "model": {**runtime["model"], "sha256": model_sha, "sha256_status": "bound"},
        "engine": {**runtime["engine"], "binary_sha256": engine_sha,
                   "binary_sha256_status": "bound", "reported_version": reported,
                   "reported_version_sha256": sha256_bytes(reported.encode())},
        "sampling": runtime["sampling"],
        "server": runtime["server"],
        "harness": runtime["harness"],
        "runner_code_sha256": runtime["runner_code_sha256"],
    }


def identity_sha(identity: dict) -> str:
    return sha256_bytes(canonical(identity))


def load_episode_index(episodes_path, ids: list[str]) -> dict:
    wanted, found = set(ids), {}
    for obj in read_jsonl(episodes_path):
        eid = obj.get("id")
        if eid in wanted:
            found[eid] = obj
    if set(found) != wanted:
        raise LocalTeacherError("episode pool does not contain exact membership")
    return found


def initial_grid(membership: dict, identity: dict) -> dict:
    ids = membership["payload"]["episode_ids"]
    return {"schema": GRID_SCHEMA, "batch": identity["batch"],
            "membership_commitment": membership["commitment"],
            "execution_identity_sha256": identity_sha(identity),
            "slots": [{"index": i, "episode_id": eid, "status": "not_started", "receipt_sha256": None}
                      for i, eid in enumerate(ids)]}


def validate_grid(grid: dict, membership: dict, identity: dict):
    if grid.get("schema") != GRID_SCHEMA or grid.get("batch") != identity["batch"]:
        raise LocalTeacherError("malformed/foreign terminal grid")
    if grid.get("membership_commitment") != membership["commitment"]:
        raise LocalTeacherError("grid membership mismatch")
    if grid.get("execution_identity_sha256") != identity_sha(identity):
        raise LocalTeacherError("changed runtime/model identity cannot resume")
    ids = membership["payload"]["episode_ids"]
    slots = grid.get("slots")
    if not isinstance(slots, list) or len(slots) != len(ids):
        raise LocalTeacherError("terminal grid is not the exact membership size")
    for i, (slot, eid) in enumerate(zip(slots, ids)):
        if slot.get("index") != i or slot.get("episode_id") != eid or slot.get("status") not in {
            "not_started", "started", "terminal"
        }:
            raise LocalTeacherError("terminal grid slot mismatch")


def slot_path(run_dir, index: int) -> pathlib.Path:
    return pathlib.Path(run_dir) / "receipts" / f"slot-{index:03d}.json"


def validate_receipt(obj: dict, slot: dict, identity: dict):
    if obj.get("schema") != RECEIPT_SCHEMA or obj.get("batch") != identity["batch"]:
        raise LocalTeacherError("malformed/foreign slot receipt")
    if obj.get("index") != slot["index"] or obj.get("episode_id") != slot["episode_id"]:
        raise LocalTeacherError("slot receipt does not match the frozen grid")
    if obj.get("execution_identity_sha256") != identity_sha(identity) or obj.get("terminal") is not True:
        raise LocalTeacherError("slot receipt runtime/terminal mismatch")
    if not isinstance(obj.get("raw_attempt"), dict):
        raise LocalTeacherError("slot receipt lacks raw attempt")
    if obj.get("raw_attempt_sha256") != sha256_bytes(canonical(obj["raw_attempt"])):
        raise LocalTeacherError("slot receipt raw-attempt hash mismatch")


def reconcile_receipts(run_dir, grid: dict, identity: dict):
    receipts_dir = pathlib.Path(run_dir) / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    expected_names = {f"slot-{i:03d}.json" for i in range(len(grid["slots"]))}
    foreign = [p.name for p in receipts_dir.glob("slot-*.json") if p.name not in expected_names]
    if foreign:
        raise LocalTeacherError("foreign receipt filenames in run directory")
    for slot in grid["slots"]:
        p = slot_path(run_dir, slot["index"])
        if p.exists():
            obj = load_json(p)
            validate_receipt(obj, slot, identity)
            digest = sha256_file(p)
            if slot["status"] == "terminal" and slot.get("receipt_sha256") not in (None, digest):
                raise LocalTeacherError("changed terminal receipt")
            slot["status"], slot["receipt_sha256"] = "terminal", digest
        elif slot["status"] == "terminal":
            raise LocalTeacherError("terminal grid references a missing receipt")


def frozen_backend(base_url: str):
    return common.agent.OpenAIBackend(
        base_url, TEACHER, None, temperature=SAMPLING["temperature"],
        max_tokens=SAMPLING["max_tokens"], seed=SAMPLING["seed"],
        thinking=SAMPLING["thinking"], sampling={"top_p": SAMPLING["top_p"]},
    )


def interrupted_record(episode_id: str, family: str) -> dict:
    return {"episode": episode_id, "family": family, "ok_transport": False,
            "error": "INTERRUPTED_AFTER_SLOT_START", "answer": "", "trace": [],
            "attempts": [], "messages": [], "raw_answer": "", "raw_trace_len": 0,
            "elapsed_seconds": 0.0}


def run_grid(run_dir, membership: dict, identity: dict, episodes: dict, *,
             trajectory: Callable[[dict], dict]):
    run_dir = pathlib.Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    identity_path, grid_path = run_dir / "execution-identity.json", run_dir / "grid.json"
    write_once(identity_path, json_blob(identity))
    if grid_path.exists():
        grid = load_json(grid_path)
    else:
        grid = initial_grid(membership, identity)
        atomic_write(grid_path, json_blob(grid))
    validate_grid(grid, membership, identity)
    reconcile_receipts(run_dir, grid, identity)
    atomic_write(grid_path, json_blob(grid))

    for slot in grid["slots"]:
        if slot["status"] == "terminal":
            continue
        episode = episodes[slot["episode_id"]]
        if slot["status"] == "started":
            raw = interrupted_record(slot["episode_id"], episode["family"])
        else:
            slot["status"] = "started"
            atomic_write(grid_path, json_blob(grid))
            started = time.monotonic()
            try:
                raw = trajectory(episode)
            except Exception as exc:  # a transport/model failure is terminal, never retried
                raw = {"episode": slot["episode_id"], "family": episode["family"],
                       "ok_transport": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                       "answer": "", "trace": [], "attempts": [], "messages": [],
                       "raw_answer": "", "raw_trace_len": 0,
                       "elapsed_seconds": round(time.monotonic() - started, 6)}
        receipt = {"schema": RECEIPT_SCHEMA, "batch": identity["batch"],
                   "index": slot["index"], "episode_id": slot["episode_id"],
                   "execution_identity_sha256": identity_sha(identity), "terminal": True,
                   "transport_success": bool(raw.get("ok_transport")), "raw_attempt": raw,
                   "raw_attempt_sha256": sha256_bytes(canonical(raw))}
        p = slot_path(run_dir, slot["index"])
        write_once(p, json_blob(receipt))
        slot["status"], slot["receipt_sha256"] = "terminal", sha256_file(p)
        atomic_write(grid_path, json_blob(grid))
    return grid


def cmd_run(args):
    runtime = load_json(args.runtime)
    membership = verify_runtime(runtime, args.membership, args.episodes)
    identity = execution_identity(runtime, membership, args.model_file, args.engine_binary)
    episodes = load_episode_index(args.episodes, membership["payload"]["episode_ids"])
    backend = frozen_backend(args.base_url)
    grid = run_grid(args.run_dir, membership, identity, episodes,
                    trajectory=lambda episode: common.run_harness(backend, episode, common.REPLAY))
    counts = collections.Counter(x["status"] for x in grid["slots"])
    print(json.dumps({"batch": runtime["batch"], "slots": len(grid["slots"]),
                      "terminal": counts["terminal"], "open": len(grid["slots"]) - counts["terminal"],
                      "execution_identity_sha256": identity_sha(identity)}, indent=2))


def model_clean(record: dict, metrics: dict) -> bool:
    attempts = record.get("attempts") or []
    blocked = [a for a in attempts if not a.get("executed")]
    duplicates = [a for a in blocked if a.get("policy") == "P3_duplicate_call"]
    return bool(
        record.get("ok_transport")
        and metrics.get("keep")
        and metrics.get("views", {}).get("model_clean")
        and not blocked
        and not duplicates
        and not record.get("corrections_used")
        and record.get("outcome") != "corrected"
        and not record.get("fallback_used")
        and not record.get("escalated")
    )


def load_terminal_receipts(run_dir, grid: dict, identity: dict) -> list[dict]:
    reconcile_receipts(run_dir, grid, identity)
    if any(s["status"] != "terminal" for s in grid["slots"]):
        raise LocalTeacherError("cannot filter before all 99 slots are terminal")
    out = []
    for slot in grid["slots"]:
        obj = load_json(slot_path(run_dir, slot["index"]))
        validate_receipt(obj, slot, identity)
        out.append(obj)
    return out


def filter_records(receipts: list[dict], episodes: dict) -> tuple[list[dict], list[dict], dict]:
    rows, results = [], []
    by_family = collections.defaultdict(lambda: {"offered": 0, "accepted": 0, "zero_pass": 0})
    for receipt in receipts:
        eid, record = receipt["episode_id"], receipt["raw_attempt"]
        episode, family = episodes[eid], episodes[eid]["family"]
        fam = by_family[family]
        fam["offered"] += 1
        if record.get("ok_transport"):
            metrics = common.judge(record, episode)
            keep = model_clean(record, metrics)
        else:
            metrics, keep = {"transport_ok": False, "keep": False,
                             "views": {"model_clean": False}}, False
        status = "accepted" if keep else "zero_pass"
        fam["accepted" if keep else "zero_pass"] += 1
        result = {"episode": eid, "family": family, "status": status,
                  "raw_attempt_sha256": receipt["raw_attempt_sha256"], "metrics": metrics}
        results.append(result)
        if keep:
            rows.extend(sft.rows_from_record(record, source="teacher", arm="B", teacher=TEACHER,
                                             episode_id=eid, trace_id=f"{eid}|{TEACHER}|0"))
    sft.apply_episode_weights(rows)
    totals = sft.episode_weight_totals(rows)
    if any(abs(v - 1.0) > 1e-12 for v in totals.values()):
        raise LocalTeacherError("episode weighting invariant failed")
    summary = {"schema": "haven-w2-local-teacher-filter-1", "teacher": TEACHER,
               "offered": len(receipts), "accepted": sum(r["status"] == "accepted" for r in results),
               "zero_pass": sum(r["status"] == "zero_pass" for r in results),
               "by_family": dict(sorted(by_family.items())), "kept_sft_rows": len(rows)}
    return rows, results, summary


def build_audit_packet(*, run_dir, identity, membership, episodes, receipts, results, rows, kept_path):
    sample = astra_batch.audit_sample(kept_path, 50)
    selected = {(x["episode"], x["teacher"]) for x in sample["sample"]}
    by_receipt = {r["episode_id"]: r for r in receipts}
    by_result = {r["episode"]: r for r in results}
    records = []
    for eid in membership["payload"]["episode_ids"]:
        if (eid, TEACHER) not in selected:
            continue
        rec = by_receipt[eid]
        records.append({"episode": episodes[eid], "raw_attempt": rec["raw_attempt"],
                        "model_visible_messages": rec["raw_attempt"].get("messages") or [],
                        "tool_trace": rec["raw_attempt"].get("trace") or [],
                        "filter_result": by_result[eid],
                        "kept_rows": [r for r in rows if r["episode"] == eid],
                        "source": {"slot_receipt_sha256": sha256_file(slot_path(run_dir, rec["index"])),
                                   "execution_identity_sha256": identity_sha(identity)}})
    if len(records) != sample["sampled"]:
        raise LocalTeacherError("audit sample/packet count mismatch")
    return {"schema": AUDIT_SCHEMA, "batch": identity["batch"],
            "membership_commitment": membership["commitment"],
            "execution_identity": identity, "audit_sample": sample, "records": records}


def cmd_filter(args):
    runtime = load_json(args.runtime)
    membership = verify_runtime(runtime, args.membership, args.episodes)
    run_dir = pathlib.Path(args.run_dir)
    identity = load_json(run_dir / "execution-identity.json")
    grid = load_json(run_dir / "grid.json")
    validate_grid(grid, membership, identity)
    episodes = load_episode_index(args.episodes, membership["payload"]["episode_ids"])
    receipts = load_terminal_receipts(run_dir, grid, identity)
    rows, results, summary = filter_records(receipts, episodes)
    out = pathlib.Path(args.out_dir)
    kept, result_path = out / "kept-rows.jsonl", out / "results.jsonl"
    summary_path, audit_path = out / "summary.json", out / "audit-v1.private.json"
    common.refuse_overwrite(kept, result_path, summary_path, audit_path)
    common.write_jsonl(kept, rows)
    common.write_jsonl(result_path, results)
    summary["kept_rows_sha256"] = sha256_file(kept)
    summary["results_sha256"] = sha256_file(result_path)
    summary["execution_identity_sha256"] = identity_sha(identity)
    write_once(summary_path, json.dumps(summary, indent=2, sort_keys=True).encode() + b"\n")
    packet = build_audit_packet(run_dir=run_dir, identity=identity, membership=membership,
                                episodes=episodes, receipts=receipts, results=results,
                                rows=rows, kept_path=kept)
    write_once(audit_path, json_blob(packet))
    summary["audit_population"] = packet["audit_sample"]["traces"]
    summary["audit_sampled"] = packet["audit_sample"]["sampled"]
    summary["audit_packet_sha256"] = sha256_file(audit_path)
    print(json.dumps(summary, indent=2, sort_keys=True))


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="CPU-only metadata census and public-safe pre-run receipt")
    p.add_argument("--label", default=DEFAULT_LABEL)
    p.add_argument("--episodes", required=True)
    p.add_argument("--hard-membership", action="append", required=True)
    p.add_argument("--private-dir", default=str(DEFAULT_PRIVATE))
    p.add_argument("--model-file")
    p.add_argument("--engine-binary")
    p.set_defaults(func=prepare)
    r = sub.add_parser("run", help="bind exact runtime and fill the one-attempt terminal grid")
    r.add_argument("--episodes", required=True)
    r.add_argument("--membership", required=True)
    r.add_argument("--runtime", required=True)
    r.add_argument("--run-dir", required=True)
    r.add_argument("--model-file", required=True)
    r.add_argument("--engine-binary", required=True)
    r.add_argument("--base-url", default="http://127.0.0.1:8096/v1")
    r.set_defaults(func=cmd_run)
    f = sub.add_parser("filter", help="model-clean filter, SFT projection and private audit packet")
    f.add_argument("--episodes", required=True)
    f.add_argument("--membership", required=True)
    f.add_argument("--runtime", required=True)
    f.add_argument("--run-dir", required=True)
    f.add_argument("--out-dir", required=True)
    f.set_defaults(func=cmd_filter)
    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        args.func(args)
    except (LocalTeacherError, OSError, ValueError, KeyError) as exc:
        print(f"w2-local-teacher: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
