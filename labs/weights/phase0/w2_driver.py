#!/usr/bin/env python3
"""Owner-side automation for the frozen Haven Astra W2 stepwise exchange.

This wraps astra_batch.py; it does not change the teacher protocol.

Flow:
  python3 w2_driver.py begin --label B --episodes TRAIN.jsonl --ids IDS.txt
  # upload B.round0.jsonl to the clean teacher and download B.reply0.jsonl
  python3 w2_driver.py next --label B
  # repeat upload/download + next until open=0
  python3 w2_driver.py seal --label B
  python3 w2_driver.py finalize --label B

The next command never seals. finalize refuses to run until an explicit seal exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASTRA = HERE / "astra_batch.py"
SCHEMA = "haven-weights-astra-stepwise-1"
HOME = Path.home()
DEFAULT_PRIVATE = HOME / "haven-private/weights/w1-pilot"
DEFAULT_DOWNLOADS = HOME / "Downloads"
DEFAULT_DESKTOP = HOME / "Desktop"


class DriverError(RuntimeError):
    pass


def load_json(path):
    return json.loads(Path(path).read_text())


def read_jsonl(path):
    rows = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DriverError(f"{path}: invalid JSON on line {n}: {exc}") from exc
        if not isinstance(obj, dict):
            raise DriverError(f"{path}: line {n} is not an object")
        rows.append(obj)
    if not rows:
        raise DriverError(f"{path}: no JSONL records")
    return rows


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def paths(private_dir, label):
    p = Path(private_dir)
    return {x: p / f"{label}.{x}.json" for x in ("gold", "salt", "session", "seal", "public")}


def exchange_dir(private_dir, label):
    p = Path(private_dir) / f"{label}.exchange"
    p.mkdir(parents=True, exist_ok=True)
    try:
        p.chmod(0o700)
    except OSError:
        pass
    return p


def counts(session):
    final = rejected = open_ = 0
    for s in session.values():
        if s.get("rejected") is not None:
            rejected += 1
        elif s.get("final") is not None:
            final += 1
        else:
            open_ += 1
    return {"assigned": len(session), "final": final, "rejected": rejected, "open": open_}


def open_ids(session):
    return {
        rid for rid, s in session.items()
        if s.get("rejected") is None and s.get("final") is None
    }


def run_astra(argv):
    if not ASTRA.is_file():
        raise DriverError(f"missing {ASTRA}")
    cp = subprocess.run(
        [sys.executable, str(ASTRA), *argv],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if cp.returncode:
        raise DriverError(cp.stdout.strip() or f"astra_batch.py exited {cp.returncode}")
    return cp.stdout.strip()


def validate_reply(path, label, session):
    rows = read_jsonl(path)
    expected = open_ids(session)
    ids = [r.get("id") for r in rows]
    if len(ids) != len(set(ids)):
        raise DriverError(f"{path}: duplicate reply id")
    if set(ids) != expected:
        raise DriverError(
            f"{path}: ids do not equal current open set "
            f"(expected {len(expected)}, got {len(ids)})"
        )
    for r in rows:
        rid = r["id"]
        if r.get("schema") != SCHEMA:
            raise DriverError(f"{path}: {rid}: wrong schema")
        if r.get("batch") != label:
            raise DriverError(f"{path}: {rid}: wrong batch")
        action = r.get("action")
        if action == "call":
            expected_round = len(session[rid].get("calls") or [])
            if r.get("round") != expected_round:
                raise DriverError(
                    f"{path}: {rid}: round {r.get('round')} != expected {expected_round}"
                )
            c = r.get("call")
            if not isinstance(c, dict) or not isinstance(c.get("name"), str) or not isinstance(c.get("arguments"), dict):
                raise DriverError(f"{path}: {rid}: malformed call")
        elif action == "final":
            f = r.get("final")
            if not isinstance(f, dict):
                raise DriverError(f"{path}: {rid}: malformed final")
            if f.get("tool_calls") != session[rid].get("calls"):
                raise DriverError(f"{path}: {rid}: final tool_calls differ from session")
        else:
            raise DriverError(f"{path}: {rid}: invalid action {action!r}")
    return rows


def find_reply(downloads, label, session, explicit=None):
    if explicit:
        p = Path(explicit).expanduser()
        validate_reply(p, label, session)
        return p
    candidates = sorted(
        [p for p in Path(downloads).expanduser().glob(f"{label}.reply*.jsonl") if p.is_file()],
        key=lambda p: (p.stat().st_mtime_ns, p.name),
        reverse=True,
    )
    valid = []
    errors = []
    for p in candidates:
        try:
            validate_reply(p, label, session)
            valid.append(p)
        except DriverError as exc:
            errors.append(str(exc))
    if len(valid) == 1:
        return valid[0]
    if len(valid) > 1:
        raise DriverError("multiple valid replies found; pass --reply explicitly")
    if errors:
        raise DriverError("no valid reply found; newest error: " + errors[0])
    raise DriverError(f"no {label}.reply*.jsonl found in {downloads}")


def next_cycle(private_dir, label, obs_dir):
    nums = []
    for base in (exchange_dir(private_dir, label), Path(obs_dir).expanduser()):
        for p in base.glob(f"{label}.reply*.jsonl"):
            m = re.search(r"\.reply(\d+)\.jsonl$", p.name)
            if m:
                nums.append(int(m.group(1)))
        for p in base.glob(f"{label}.obs*.jsonl"):
            m = re.search(r"\.obs(\d+)\.jsonl$", p.name)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 0


def cmd_status(args):
    private = Path(args.private_dir).expanduser()
    p = paths(private, args.label)
    if not p["session"].is_file():
        raise DriverError(f"no session: {p['session']}")
    out = {"label": args.label, **counts(load_json(p["session"])), "sealed": p["seal"].is_file()}
    if p["seal"].is_file():
        s = load_json(p["seal"])
        out["answers_sha256"] = s.get("answers_sha256")
        out["session_sha256"] = s.get("session_sha256")
    print(json.dumps(out, indent=2))


def cmd_begin(args):
    private = Path(args.private_dir).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    round0 = out_dir / f"{args.label}.round0.jsonl"
    if round0.exists():
        raise DriverError(f"refusing to overwrite {round0}")
    argv = [
        "export",
        "--episodes", str(Path(args.episodes).expanduser()),
        "--label", args.label,
        "--private-dir", str(private),
        "--out", str(round0),
        "--n", str(args.n),
    ]
    if args.ids:
        argv += ["--ids", str(Path(args.ids).expanduser())]
    print(run_astra(argv))
    archived = exchange_dir(private, args.label) / round0.name
    shutil.copy2(round0, archived)
    try:
        archived.chmod(0o600)
    except OSError:
        pass
    print(json.dumps({
        "next": "upload_round0_to_clean_teacher",
        "round0": str(round0),
        "round0_sha256": sha256_file(round0),
    }, indent=2))


def cmd_next(args):
    private = Path(args.private_dir).expanduser()
    obs_dir = Path(args.obs_dir).expanduser()
    obs_dir.mkdir(parents=True, exist_ok=True)
    p = paths(private, args.label)
    if p["seal"].exists():
        raise DriverError("batch is sealed; no more step calls are permitted")
    if not p["session"].is_file():
        raise DriverError("no session; run begin/export first")
    session = load_json(p["session"])
    before_counts = counts(session)
    if before_counts["open"] == 0:
        print(json.dumps({**before_counts, "next": "seal"}, indent=2))
        return
    if before_counts["rejected"]:
        raise DriverError("session already contains rejected ids; inspect before continuing")

    reply = find_reply(args.downloads, args.label, session, args.reply)
    validate_reply(reply, args.label, session)
    cycle = next_cycle(private, args.label, obs_dir)
    ex = exchange_dir(private, args.label)
    pending = ex / f".{args.label}.reply{cycle}.pending.jsonl"
    archived = ex / f"{args.label}.reply{cycle}.jsonl"
    obs = obs_dir / f"{args.label}.obs{cycle}.jsonl"
    if pending.exists() or archived.exists():
        raise DriverError(f"reply archive collision for cycle {cycle}")
    if obs.exists():
        if obs.stat().st_size == 0:
            obs.unlink()
        else:
            raise DriverError(f"refusing to overwrite {obs}")

    session_before = sha256_file(p["session"])
    shutil.copy2(reply, pending)
    try:
        pending.chmod(0o600)
    except OSError:
        pass
    try:
        raw = run_astra([
            "step",
            "--private-dir", str(private),
            "--label", args.label,
            "--reply", str(pending),
            "--out", str(obs),
        ])
    except DriverError as exc:
        session_after = sha256_file(p["session"])
        if session_after != session_before:
            danger = ex / f".{args.label}.reply{cycle}.SESSION_MUTATED.jsonl"
            pending.replace(danger)
            raise DriverError(
                f"step failed after session mutation; DO NOT RETRY. reply preserved at {danger}. {exc}"
            ) from exc
        pending.unlink(missing_ok=True)
        raise DriverError(f"step failed with session unchanged; safe to fix/retry. {exc}") from exc

    pending.replace(archived)
    try:
        reply.unlink()
    except OSError:
        pass

    current = counts(load_json(p["session"]))
    try:
        astra_summary = json.loads(raw)
    except json.JSONDecodeError:
        astra_summary = {"raw": raw}
    if current["open"] == 0 and obs.exists() and obs.stat().st_size == 0:
        obs.unlink()
    print(json.dumps({
        "cycle": cycle,
        **current,
        "astra": astra_summary,
        "observations_file": str(obs) if obs.exists() else None,
        "next": "seal" if current["open"] == 0 else "upload_observations_to_same_clean_teacher",
    }, indent=2))


def cmd_seal(args):
    private = Path(args.private_dir).expanduser()
    p = paths(private, args.label)
    if p["seal"].is_file():
        print(json.dumps({"status": "already_sealed", **load_json(p["seal"])}, indent=2))
        return
    if not p["session"].is_file():
        raise DriverError("no session")
    c = counts(load_json(p["session"]))
    if c["open"] or c["rejected"] or c["final"] != c["assigned"]:
        raise DriverError(f"refusing to seal incomplete session: {c}")
    print(run_astra(["seal", "--private-dir", str(private), "--label", args.label]))


def ensure_replay(private, label, teacher):
    out = private / f"{label}-replay"
    kept = out / f"{label}.kept-rows.jsonl"
    results = out / f"{label}.results.jsonl"
    summary = out / f"{label}.summary.json"
    present = [x.exists() for x in (kept, results, summary)]
    if any(present) and not all(present):
        raise DriverError(f"partial replay output exists in {out}")
    if not all(present):
        out.mkdir(parents=True, exist_ok=True)
        print(run_astra([
            "replay", "--private-dir", str(private), "--label", label,
            "--out-dir", str(out), "--teacher", teacher,
        ]))
    s = load_json(summary)
    if s.get("kept_rows_sha256") != sha256_file(kept):
        raise DriverError("kept-row SHA mismatch")
    return out, s


def ensure_reveal(private, label):
    out = private / f"{label}.gold-reveal.json"
    if not out.exists():
        print(run_astra([
            "reveal", "--private-dir", str(private), "--label", label, "--out", str(out)
        ]))
    return out


def find_round0(private, label, explicit=None):
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            raise DriverError(f"round0 not found: {p}")
        return p
    for p in (
        exchange_dir(private, label) / f"{label}.round0.jsonl",
        DEFAULT_DESKTOP / f"{label}.round0.jsonl",
    ):
        if p.is_file():
            return p
    raise DriverError("round0 not found; pass --round0")


def build_audit_packet(private, label, replay_dir, teacher, round0):
    sys.path.insert(0, str(HERE))
    import astra_batch
    import common

    p = paths(private, label)
    reveal_path = private / f"{label}.gold-reveal.json"
    results_path = replay_dir / f"{label}.results.jsonl"
    kept_path = replay_dir / f"{label}.kept-rows.jsonl"
    summary_path = replay_dir / f"{label}.summary.json"

    gold = load_json(p["gold"])
    salt = load_json(p["salt"])
    session = load_json(p["session"])
    seal = load_json(p["seal"])
    public = load_json(p["public"])
    reveal = load_json(reveal_path)
    round0_rows = read_jsonl(round0)
    results = read_jsonl(results_path)
    kept_rows = read_jsonl(kept_path) if kept_path.stat().st_size else []
    summary = load_json(summary_path)

    problems = list(astra_batch.validate_seal(gold, session, public, seal))
    commitment = salt.get("commitment")
    if not commitment or not common.check_commitment(salt.get("salt"), gold, commitment):
        problems.append("gold commitment verification failed")
    if public.get("gold_commitment") != commitment:
        problems.append("public gold commitment mismatch")
    if reveal.get("commitment") != commitment:
        problems.append("reveal commitment mismatch")
    if summary.get("seal_answers_sha256") != seal.get("answers_sha256"):
        problems.append("replay does not bind current seal")
    if summary.get("kept_rows_sha256") != sha256_file(kept_path):
        problems.append("replay kept-row hash mismatch")

    sample = astra_batch.audit_sample(kept_path, 50)
    sample_keys = {(x["episode"], x["teacher"]) for x in sample["sample"]}
    gold_by_id = {x["id"]: x["episode"] for x in gold.get("records", [])}
    round0_by_id = {x["id"]: x for x in round0_rows}
    results_by_id = {x["id"]: x for x in results}
    if set(gold_by_id) != set(session):
        problems.append("gold/session id sets differ")
    if set(round0_by_id) != set(session):
        problems.append("round0/session id sets differ")
    if set(results_by_id) != set(session):
        problems.append("results/session id sets differ")

    records = []
    for rid in sorted(session):
        ep = gold_by_id.get(rid)
        rr = results_by_id.get(rid)
        r0 = round0_by_id.get(rid)
        if not ep or not rr or not r0:
            continue
        if (ep["id"], teacher) not in sample_keys:
            continue
        rows = [
            x for x in kept_rows
            if x.get("episode") == ep["id"] and x.get("teacher") == teacher
        ]
        records.append({
            "id": rid,
            "round0": r0,
            "episode": ep,
            "session": session[rid],
            "replay_result": rr,
            "kept_rows": rows,
        })
    if len(records) != sample.get("sampled"):
        problems.append("audit record count differs from deterministic sample")

    packet = {
        "schema": "haven-w2-astra-batch-audit-1",
        "batch": label,
        "source_receipts": {
            "round0_sha256": sha256_file(round0),
            "gold_file_sha256": sha256_file(p["gold"]),
            "session_sha256": sha256_file(p["session"]),
            "seal_file_sha256": sha256_file(p["seal"]),
            "public_file_sha256": sha256_file(p["public"]),
            "gold_reveal_file_sha256": sha256_file(reveal_path),
            "results_sha256": sha256_file(results_path),
            "kept_rows_sha256": sha256_file(kept_path),
            "summary_sha256": sha256_file(summary_path),
            "gold_commitment": commitment,
            "answers_sha256": seal.get("answers_sha256"),
        },
        "audit_sample": sample,
        "records": records,
    }
    out = private / f"{label}.audit-v1.json"
    blob = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    candidate = hashlib.sha256(blob).hexdigest()
    if out.exists():
        if sha256_file(out) != candidate:
            raise DriverError(f"existing audit packet differs: {out}")
    else:
        out.write_bytes(blob)
        try:
            out.chmod(0o600)
        except OSError:
            pass

    return {
        "status": "STRUCTURAL_PRECHECK_PASS" if not problems else "STRUCTURAL_PRECHECK_FAIL",
        "batch": label,
        "offered": summary.get("offered"),
        "accepted": summary.get("accepted"),
        "zero_pass": summary.get("zero_pass"),
        "audit_population": sample.get("traces"),
        "audit_sampled": sample.get("sampled"),
        "kept_sft_rows": len(kept_rows),
        "gold_commitment": commitment,
        "answers_sha256": seal.get("answers_sha256"),
        "kept_rows_sha256": sha256_file(kept_path),
        "audit_packet_sha256": sha256_file(out),
        "audit_packet_path": str(out),
        "structural_problem_count": len(problems),
        "problems": problems,
    }


def cmd_finalize(args):
    private = Path(args.private_dir).expanduser()
    p = paths(private, args.label)
    if not p["seal"].is_file():
        raise DriverError("refusing to finalize before explicit seal")
    replay_dir, summary = ensure_replay(private, args.label, args.teacher)
    seal = load_json(p["seal"])
    if summary.get("seal_answers_sha256") != seal.get("answers_sha256"):
        raise DriverError("replay does not match seal")
    ensure_reveal(private, args.label)
    round0 = find_round0(private, args.label, args.round0)
    print(json.dumps(
        build_audit_packet(private, args.label, replay_dir, args.teacher, round0),
        indent=2,
    ))


def make_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--private-dir", default=str(DEFAULT_PRIVATE))
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status")
    s.add_argument("--label", required=True)
    s.set_defaults(func=cmd_status)

    b = sub.add_parser("begin")
    b.add_argument("--label", required=True)
    b.add_argument("--episodes", required=True)
    b.add_argument("--ids")
    b.add_argument("--n", type=int, default=50)
    b.add_argument("--out-dir", default=str(DEFAULT_DESKTOP))
    b.set_defaults(func=cmd_begin)

    n = sub.add_parser("next")
    n.add_argument("--label", required=True)
    n.add_argument("--downloads", default=str(DEFAULT_DOWNLOADS))
    n.add_argument("--obs-dir", default=str(DEFAULT_DESKTOP))
    n.add_argument("--reply")
    n.set_defaults(func=cmd_next)

    z = sub.add_parser("seal")
    z.add_argument("--label", required=True)
    z.set_defaults(func=cmd_seal)

    f = sub.add_parser("finalize")
    f.add_argument("--label", required=True)
    f.add_argument("--teacher", default="astra-6.2")
    f.add_argument("--round0")
    f.set_defaults(func=cmd_finalize)
    return ap


def main(argv=None):
    args = make_parser().parse_args(argv)
    try:
        args.func(args)
    except (DriverError, OSError, ValueError, KeyError) as exc:
        print(f"haven-w2: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
