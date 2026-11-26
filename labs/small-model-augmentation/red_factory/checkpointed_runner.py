#!/usr/bin/env python3
"""Checkpointed Hermes-in-loop runner for Haven Local Red Factory.

This adapter composes #130's unit-level recovery journal with the existing HRF
Hermes runner. It does not restore opaque conversations. Each HRF case is one
restartable unit, and completed units are reused only after their private result
receipt re-hashes to the journal's committed payload hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Mapping

import checkpoint_journal as checkpoint
from hermes_runner import run_hermes_case
from local_runner import (
    _parse_csv_ints,
    _parse_families,
    _validate_new_output_path,
    _write_private_json,
    normalize_loopback_base_url,
)
from red_factory import build_suite, summarize, validate_suite

SCHEMA = "haven-local-red-factory-hermes-checkpoint-v1"
MAX_RESULT_BYTES = 8 * 1024 * 1024
_RUN_ID = re.compile(r"[A-Za-z0-9_.:@/-]{1,256}\Z")


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _manifest(
    *,
    suite: Mapping[str, Any],
    hermes: Path,
    backend_base_url: str,
    model: str,
    toolsets: str,
    timeout_seconds: float,
    max_turns: int,
) -> tuple[dict[str, Any], str]:
    hermes = Path(hermes)
    if not hermes.is_file():
        raise ValueError("Hermes executable is not a file")
    body = {
        "schema": SCHEMA,
        "classification": "development",
        "suite_sha256": suite["suite_sha256"],
        "hermes_sha256": _hash_file(hermes),
        "backend_base_url": normalize_loopback_base_url(backend_base_url),
        "model": model,
        "toolsets": toolsets,
        "timeout_seconds": float(timeout_seconds),
        "max_turns": max_turns,
    }
    return body, _sha256(body)


def _case_path(results_dir: Path, case_id: str, attempt: int) -> Path:
    return results_dir / f"result-{case_id}-a{attempt}.json"


def _validate_case_result(
    value: Mapping[str, Any], *, case_id: str, expected_sha256: str | None = None
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("case_id") != case_id:
        raise ValueError("case receipt identity mismatch")
    normalized = dict(value)
    claimed = normalized.get("result_sha256")
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        raise ValueError("case receipt missing hash")
    body = {k: v for k, v in normalized.items() if k != "result_sha256"}
    if _sha256(body) != claimed:
        raise ValueError("case receipt hash mismatch")
    if expected_sha256 is not None and claimed != expected_sha256:
        raise ValueError("case receipt committed hash mismatch")
    return normalized


def _read_case_result(path: Path, *, expected_sha256: str, case_id: str) -> dict[str, Any]:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RESULT_BYTES:
        raise ValueError("unsafe completed-case receipt")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid completed-case receipt") from exc
    value = _validate_case_result(
        value, case_id=case_id, expected_sha256=expected_sha256
    )
    if value.get("status") != "pass":
        raise ValueError("completed-case receipt was not a passing result")
    return value


def _completion_map(events: list[dict[str, Any]]) -> dict[str, tuple[int, str]]:
    out: dict[str, tuple[int, str]] = {}
    for event in events:
        if event["event"] == "unit_completed":
            out[event["unit"]] = (event["attempt"], event["payload_sha256"])
    return out


def _result_body(
    *,
    suite: Mapping[str, Any],
    run_id: str,
    manifest_sha256: str,
    journal: Path,
    results: list[dict[str, Any]],
    plan: Mapping[str, Any],
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    scan = checkpoint.scan(journal)
    if not scan.ok:
        raise ValueError("checkpoint journal invalid after run")
    all_valid = len(results) == suite["n"] and all(row.get("status") == "pass" for row in results)
    model_summary = summarize([row["score"] for row in results], suite) if all_valid else None
    execution_summary = summarize([row["execution_score"] for row in results], suite) if all_valid else None
    body = {
        "schema": SCHEMA,
        "classification": "development",
        "status": status,
        "error": error,
        "run_id": run_id,
        "manifest_sha256": manifest_sha256,
        "suite_sha256": suite["suite_sha256"],
        "n": suite["n"],
        "completed": len(results),
        "result_sha256s": [row["result_sha256"] for row in results],
        "model_summary": model_summary,
        "execution_summary": execution_summary,
        "resume_plan": dict(plan),
        "journal_head_sha256": scan.events[-1]["event_sha256"] if scan.events else None,
    }
    body["run_sha256"] = _sha256(body)
    return body


def run_checkpointed_suite(
    *,
    hermes: Path,
    hermes_home: Path,
    toolsets: str,
    backend_base_url: str,
    model: str,
    suite: Mapping[str, Any],
    journal_path: Path,
    results_dir: Path,
    run_id: str,
    resume: bool = False,
    max_attempts: int = 3,
    backend_key: str | None = None,
    timeout_seconds: float = 180.0,
    max_turns: int = 8,
    env: Mapping[str, str] | None = None,
    case_runner: Callable[..., dict[str, Any]] = run_hermes_case,
) -> dict[str, Any]:
    """Run or resume one HRF suite under #130's unit-level journal contract."""
    cases = validate_suite(suite)
    if not isinstance(run_id, str) or _RUN_ID.fullmatch(run_id) is None:
        raise ValueError("invalid run_id")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 20:
        raise ValueError("invalid max_attempts")
    results_dir = Path(results_dir)
    if results_dir.is_symlink() or not results_dir.is_dir():
        raise ValueError("results_dir must be an existing non-symlink directory")
    journal_path = Path(journal_path)
    if journal_path.is_symlink():
        raise ValueError("journal must not be a symlink")

    _, manifest_sha256 = _manifest(
        suite=suite,
        hermes=hermes,
        backend_base_url=backend_base_url,
        model=model,
        toolsets=toolsets,
        timeout_seconds=timeout_seconds,
        max_turns=max_turns,
    )
    j = checkpoint.Journal(journal_path, run_id, manifest_sha256, fsync=True)

    # Hold the authoritative runner lease while inspecting and mutating the journal.
    with checkpoint.RunLease(journal_path):
        before = checkpoint.scan(journal_path)
        if not before.ok:
            raise ValueError("checkpoint journal invalid: " + ",".join(before.errors))
        if resume:
            if not before.events:
                raise ValueError("cannot resume an empty checkpoint journal")
        elif before.events:
            raise ValueError("checkpoint journal already contains a run")
        j.open(resume=resume)

        scan = checkpoint.scan(journal_path)
        if not scan.ok:
            raise ValueError("checkpoint journal invalid after open")
        plan = checkpoint.resume_plan(scan.events, max_attempts=max_attempts)
        if plan["blocked_units"]:
            completed_map = _completion_map(scan.events)
            loaded = []
            for case in cases:
                if case.case_id in completed_map:
                    attempt, digest = completed_map[case.case_id]
                    loaded.append(_read_case_result(
                        _case_path(results_dir, case.case_id, attempt),
                        expected_sha256=digest,
                        case_id=case.case_id,
                    ))
            return _result_body(
                suite=suite, run_id=run_id, manifest_sha256=manifest_sha256,
                journal=journal_path, results=loaded, plan=plan, status="block",
                error="CHECKPOINT_RESUME_BLOCKED",
            )

        completed_map = _completion_map(scan.events)
        results_by_id: dict[str, dict[str, Any]] = {}
        for case in cases:
            completed = completed_map.get(case.case_id)
            if completed is None:
                continue
            attempt, digest = completed
            results_by_id[case.case_id] = _read_case_result(
                _case_path(results_dir, case.case_id, attempt),
                expected_sha256=digest,
                case_id=case.case_id,
            )

        if plan["run_completed"]:
            if len(results_by_id) != len(cases):
                raise ValueError("run_completed journal is missing case receipts")
            ordered = [results_by_id[case.case_id] for case in cases]
            return _result_body(
                suite=suite, run_id=run_id, manifest_sha256=manifest_sha256,
                journal=journal_path, results=ordered, plan=plan, status="pass",
            )

        retry = {row["unit"]: row["next_attempt"] for row in plan["retryable_units"]}
        known_units = {
            event["unit"] for event in scan.events
            if event["unit"]
        }

        for case in cases:
            if case.case_id in results_by_id:
                continue
            if case.case_id in retry:
                attempt = retry[case.case_id]
            elif case.case_id in known_units:
                return _result_body(
                    suite=suite, run_id=run_id, manifest_sha256=manifest_sha256,
                    journal=journal_path,
                    results=[results_by_id[c.case_id] for c in cases if c.case_id in results_by_id],
                    plan=j.state(max_attempts=max_attempts),
                    status="block", error="CHECKPOINT_UNIT_NOT_RETRYABLE",
                )
            else:
                attempt = 1

            j.append("unit_started", case.case_id, attempt)
            model_op = f"m{attempt}"
            j.append(
                "model_request_started", case.case_id, attempt,
                model_op, True, checkpoint.ZERO,
            )

            child_env = dict(os.environ if env is None else env)
            child_env.update({
                "HRF_CHECKPOINT_JOURNAL": str(journal_path),
                "HRF_CHECKPOINT_RUN_ID": run_id,
                "HRF_CHECKPOINT_MANIFEST_SHA256": manifest_sha256,
                "HRF_CHECKPOINT_UNIT": case.case_id,
                "HRF_CHECKPOINT_ATTEMPT": str(attempt),
            })
            try:
                result = case_runner(
                    hermes=Path(hermes),
                    hermes_home=Path(hermes_home),
                    toolsets=toolsets,
                    backend_base_url=backend_base_url,
                    model=model,
                    case=case,
                    backend_key=backend_key,
                    timeout_seconds=timeout_seconds,
                    max_turns=max_turns,
                    env=child_env,
                )
            except Exception:
                plan = j.state(max_attempts=max_attempts)
                ordered = [results_by_id[c.case_id] for c in cases if c.case_id in results_by_id]
                return _result_body(
                    suite=suite, run_id=run_id, manifest_sha256=manifest_sha256,
                    journal=journal_path, results=ordered, plan=plan, status="block",
                    error="CASE_RUNNER_EXCEPTION",
                )

            try:
                result = _validate_case_result(result, case_id=case.case_id)
            except (TypeError, ValueError):
                plan = j.state(max_attempts=max_attempts)
                ordered = [results_by_id[c.case_id] for c in cases if c.case_id in results_by_id]
                return _result_body(
                    suite=suite, run_id=run_id, manifest_sha256=manifest_sha256,
                    journal=journal_path, results=ordered, plan=plan, status="block",
                    error="INVALID_CASE_RESULT",
                )

            result_path = _case_path(results_dir, case.case_id, attempt)
            _write_private_json(result_path, result)
            j.append(
                "model_response_committed", case.case_id, attempt,
                model_op, False, result["result_sha256"],
            )
            if result.get("status") != "pass":
                plan = j.state(max_attempts=max_attempts)
                ordered = [results_by_id[c.case_id] for c in cases if c.case_id in results_by_id]
                return _result_body(
                    suite=suite, run_id=run_id, manifest_sha256=manifest_sha256,
                    journal=journal_path, results=ordered, plan=plan, status="block",
                    error="CASE_EVIDENCE_BLOCKED",
                )

            j.append(
                "unit_completed", case.case_id, attempt,
                payload_sha256=result["result_sha256"],
            )
            results_by_id[case.case_id] = result

        j.append("run_completed")
        plan = j.state(max_attempts=max_attempts)
        ordered = [results_by_id[case.case_id] for case in cases]
        return _result_body(
            suite=suite, run_id=run_id, manifest_sha256=manifest_sha256,
            journal=journal_path, results=ordered, plan=plan, status="pass",
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes", type=Path, required=True)
    parser.add_argument("--hermes-home", type=Path, required=True)
    parser.add_argument("--toolsets", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--seeds", default="0")
    parser.add_argument("--families", default="all")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--api-key-env")
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    _validate_new_output_path(args.out)
    backend_key = None
    if args.api_key_env:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", args.api_key_env):
            raise ValueError("invalid api-key environment variable name")
        backend_key = os.environ.get(args.api_key_env)
        if backend_key is None:
            raise ValueError("api-key environment variable is not set")

    suite = build_suite(
        seeds=_parse_csv_ints(args.seeds),
        families=_parse_families(args.families),
    )
    result = run_checkpointed_suite(
        hermes=args.hermes,
        hermes_home=args.hermes_home,
        toolsets=args.toolsets,
        backend_base_url=args.base_url,
        model=args.model,
        suite=suite,
        journal_path=args.journal,
        results_dir=args.results_dir,
        run_id=args.run_id,
        resume=args.resume,
        max_attempts=args.max_attempts,
        backend_key=backend_key,
        timeout_seconds=args.timeout,
        max_turns=args.max_turns,
    )
    _write_private_json(args.out, result)
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "run_id": result["run_id"],
        "manifest_sha256": result["manifest_sha256"],
        "run_sha256": result["run_sha256"],
        "completed": result["completed"],
        "n": result["n"],
        "journal_head_sha256": result["journal_head_sha256"],
        "out": str(args.out),
    }, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
