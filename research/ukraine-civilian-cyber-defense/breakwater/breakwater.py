#!/usr/bin/env python3
"""BREAKWATER: an offline, read-only attack-path interruption planner.

Mathematical coverage applies ONLY to operator-supplied models. It cannot prove
that any real attack would be stopped. There is no endpoint/network access.
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
MAX_PATHS = 40
MAX_CONTROLS = 16


class InvalidModel(ValueError):
    pass


def _ids(values: object, label: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise InvalidModel(f"{label} must be a non-empty list")
    if not all(isinstance(v, str) and ID.fullmatch(v) for v in values):
        raise InvalidModel(f"{label} contains an invalid ID")
    if len(set(values)) != len(values):
        raise InvalidModel(f"{label} has duplicate IDs")
    return values


def _date(raw: object) -> datetime:
    if not isinstance(raw, str):
        raise ValueError("datetime must be a string")
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("datetime must include timezone")
    return parsed.astimezone(timezone.utc)


def _attested(control: dict, now: datetime) -> bool:
    """An operator attestation, not an independently measured control test."""
    if control["state"] != "attested":
        return False
    if not isinstance(control.get("evidence_reference"), str) or not control["evidence_reference"].strip():
        return False
    try:
        measured = _date(control.get("validated_utc"))
    except (ValueError, TypeError):
        return False
    return timedelta(0) <= now - measured <= timedelta(days=30)


def validate(model: object) -> tuple[list[dict], list[dict]]:
    if not isinstance(model, dict):
        raise InvalidModel("Input must be an object")
    source = model.get("source_url")
    if not isinstance(source, str):
        raise InvalidModel("source_url is required")
    try:
        parsed = urlparse(source)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise InvalidModel("source_url must be an HTTPS public reference")
    except ValueError as exc:
        raise InvalidModel(f"Invalid source_url: {exc}") from exc
    paths, controls = model.get("attack_paths"), model.get("controls")
    if not isinstance(paths, list) or not (1 <= len(paths) <= MAX_PATHS):
        raise InvalidModel(f"attack_paths must contain 1–{MAX_PATHS} paths")
    if not isinstance(controls, list) or len(controls) > MAX_CONTROLS:
        raise InvalidModel(f"controls must contain at most {MAX_CONTROLS} controls")
    path_ids, control_ids, steps_in_paths = set(), set(), set()
    for path in paths:
        if not isinstance(path, dict) or not isinstance(path.get("id"), str) or not ID.fullmatch(path["id"]):
            raise InvalidModel("Every path needs a valid id")
        if path["id"] in path_ids:
            raise InvalidModel("Duplicate path id")
        path_ids.add(path["id"])
        steps = _ids(path.get("steps"), "attack path steps")
        steps_in_paths.update(steps)
    for control in controls:
        if not isinstance(control, dict) or not isinstance(control.get("id"), str) or not ID.fullmatch(control["id"]):
            raise InvalidModel("Every control needs a valid id")
        if control["id"] in control_ids:
            raise InvalidModel("Duplicate control id")
        control_ids.add(control["id"])
        blocked = _ids(control.get("interrupts"), "interrupts")
        if not set(blocked).issubset(steps_in_paths):
            raise InvalidModel(f"Control {control['id']} references undefined attack steps")
        if control.get("state") not in ("attested", "candidate", "unavailable"):
            raise InvalidModel(f"Control {control['id']} has invalid state")
        for field in ("effort", "disruption"):
            value = control.get(field)
            if type(value) is not int or not 0 <= value <= 10:
                raise InvalidModel(f"{control['id']}.{field} must be an integer from 0 to 10")
        if not isinstance(control.get("scope"), str) or not control["scope"].strip():
            raise InvalidModel(f"Control {control['id']} needs an explicit defender-controlled scope")
        if not isinstance(control.get("rollback"), str) or not control["rollback"].strip():
            raise InvalidModel(f"Control {control['id']} needs rollback guidance")
    return paths, controls


def _cover(paths: list[dict], controls: list[dict]) -> dict[str, list[str]]:
    return {
        p["id"]: sorted(c["id"] for c in controls if set(c["interrupts"]) & set(p["steps"]))
        for p in paths
    }


def choose_minimal(remaining: list[dict], candidates: list[dict]) -> tuple[list[dict], list[str]]:
    """Exact weighted set cover over the bounded candidate set, or disclose gaps."""
    if not remaining:
        return [], []
    coverable = [p for p in remaining if any(set(p["steps"]) & set(c["interrupts"]) for c in candidates)]
    impossible = sorted(p["id"] for p in remaining if p not in coverable)
    if not coverable:
        return [], impossible
    best = None
    chosen: tuple[dict, ...] = ()
    for size in range(len(candidates) + 1):
        for group in itertools.combinations(candidates, size):
            if not all(any(set(p["steps"]) & set(c["interrupts"]) for c in group) for p in coverable):
                continue
            rank = (
                sum(c["effort"] + 3 * c["disruption"] for c in group),
                sum(c["disruption"] for c in group),
                len(group),
                tuple(sorted(c["id"] for c in group)),
            )
            if best is None or rank < best:
                best, chosen = rank, group
    return sorted(chosen, key=lambda c: c["id"]), impossible


def plan(model: object, now: datetime | None = None) -> dict:
    paths, controls = validate(model)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise InvalidModel("now must have timezone")
    now = now.astimezone(timezone.utc)
    asserted = [c for c in controls if _attested(c, now)]
    candidates = [c for c in controls if c["state"] == "candidate"]
    coverage = _cover(paths, asserted)
    unresolved = [p for p in paths if not coverage[p["id"]]]
    chosen, no_candidate = choose_minimal(unresolved, candidates)
    suggested = _cover(paths, chosen)
    return {
        "schema": "breakwater/v0.1",
        "campaign": str(model.get("campaign", "unnamed campaign")),
        "source_url": model["source_url"],
        "evaluated_utc": now.isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Attack paths and control-step mappings are manual hypotheses; unknown paths are not modeled.",
            "Attested controls are operator claims, not independently verified control effectiveness.",
            "Candidate coverage is a mathematical recommendation, NOT a validated or deployed protection.",
            "Never interpret zero uncovered modeled paths as proof that an organization is secure.",
        ],
        "modeled_paths": len(paths),
        "attested_path_coverage": coverage,
        "attested_covered_count": len(paths) - len(unresolved),
        "remaining_path_ids": [p["id"] for p in unresolved],
        "recommended_controls": [{
            "id": c["id"], "scope": c["scope"], "rollback": c["rollback"],
            "effort": c["effort"], "disruption": c["disruption"],
        } for c in chosen],
        "candidate_coverage": {p["id"]: suggested[p["id"]] for p in unresolved},
        "no_candidate_path_ids": no_candidate,
        "status": "NO_SUPPORTED_PLAN" if no_candidate else ("ATTESTED_IN_MODEL" if not unresolved else "PROPOSED_ONLY"),
    }


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("manifest", type=Path, help="Local JSON attack paths and defender-controlled capabilities")
    cli.add_argument("--output", type=Path, help="Optional JSON report destination; defaults to stdout")
    args = cli.parse_args(argv)
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = plan(data)
        output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"BREAKWATER refused invalid input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
