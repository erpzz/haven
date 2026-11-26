#!/usr/bin/env python3
"""Top-level target-Mac qualification conductor for Haven local 4B runtime.

Order is intentional and fail-closed:
1. attest the pinned Hermes release/source tree;
2. create a fresh isolated positive profile from reviewed bytes;
3. run real-Hermes scripted final-gate controls with the early hook absent;
4. only if both controls pass, run the real-Qwythos per-case #212/#189 campaign.

This command is development qualification only. It uses synthetic Red Factory
objects and does not target a live network, host, tenant, or credential.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import socket
from typing import Any

_RED_FACTORY_DIR = Path(__file__).resolve().parent / "red_factory"
if str(_RED_FACTORY_DIR) not in sys.path:
    sys.path.insert(0, str(_RED_FACTORY_DIR))

import mac_final_gate_control as final_gate
import mac_profile_bootstrap as bootstrap
import mac_red_campaign as red_campaign
from local_runner import _parse_csv_ints, _parse_families

SCHEMA = "haven.mac-local-4b-qualification.v1"


class QualificationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _select_loopback_port(port: int) -> int:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise QualificationError("INVALID_PORT")
    if port:
        return port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _write_private(path: Path, value: Any) -> None:
    raw = _canon(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise QualificationError("RECEIPT_CREATE_FAILED") from exc
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)


def run_qualification(*, hermes: Path, server: Path, model: Path,
                      alias: str, out_root: Path, augmentation_root: Path,
                      seeds, families, port: int = 8080, context: int = 65536,
                      discovery_timeout: float = 60.0,
                      case_timeout: float = 180.0,
                      start_timeout: float = 120.0,
                      max_turns: int = 8,
                      profile_python: Path | None = None,
                      env=None) -> dict[str, Any]:
    out_root = Path(out_root)
    if not out_root.is_absolute():
        raise QualificationError("OUTPUT_ROOT_NOT_ABSOLUTE")
    if out_root.exists():
        raise QualificationError("OUTPUT_ROOT_ALREADY_EXISTS")
    try:
        out_root.mkdir(mode=0o700, parents=False)
    except OSError as exc:
        raise QualificationError("OUTPUT_ROOT_CREATE_FAILED") from exc
    if stat.S_IMODE(out_root.stat().st_mode) & 0o077:
        raise QualificationError("OUTPUT_ROOT_NOT_PRIVATE")

    selected_port = _select_loopback_port(port)

    # Attest before creating any runtime state or invoking Hermes.
    provenance, source_manifest = red_campaign._hermes_provenance(Path(hermes))
    red_campaign._write_private(
        out_root / "hermes-core-source-manifest.json", source_manifest
    )
    red_campaign._write_private(
        out_root / "hermes-provenance.json", provenance
    )

    profile_home = out_root / "hermes-red-profile"
    profile = bootstrap.create_profile(
        home=profile_home,
        augmentation_root=Path(augmentation_root),
        python=profile_python,
    )

    controls = {}
    for mode, seed in (("wrong-target", 9701), ("duplicate", 9702)):
        result = final_gate.run_control(
            hermes=Path(hermes),
            augmentation_root=Path(augmentation_root),
            mode=mode,
            seed=seed,
            out=out_root / f"final-gate-{mode}.json",
            timeout=min(120.0, max(1.0, float(discovery_timeout))),
            env=env,
        )
        controls[mode] = result
        if result.get("status") != "pass":
            raise QualificationError("FINAL_GATE_CONTROL_FAILED")

    campaign = red_campaign.run_campaign(
        hermes=Path(hermes),
        hermes_home=profile_home,
        toolsets="mcp-red-factory",
        server=Path(server),
        model=Path(model),
        alias=alias,
        port=selected_port,
        context=context,
        seeds=list(seeds),
        families=list(families),
        out_dir=out_root / "qwythos-red-campaign",
        augmentation_root=Path(augmentation_root),
        allowed_user_plugins=["haven-scope"],
        discovery_timeout=discovery_timeout,
        case_timeout=case_timeout,
        max_turns=max_turns,
        start_timeout=start_timeout,
        env=env,
    )

    errors = []
    if campaign.get("status") != "pass":
        errors.append("QWYTHOS_RED_CAMPAIGN_BLOCKED")
    if campaign.get("hermes_provenance", {}).get("provenance_sha256") != provenance.get("provenance_sha256"):
        errors.append("HERMES_PROVENANCE_DRIFT")

    body = {
        "schema": SCHEMA,
        "classification": "development",
        "status": "block" if errors else "pass",
        "errors": errors,
        "hermes_provenance_sha256": provenance["provenance_sha256"],
        "profile_bootstrap_receipt_sha256": profile["receipt_sha256"],
        "final_gate_control_sha256": {
            mode: value["control_sha256"] for mode, value in controls.items()
        },
        "campaign_sha256": campaign["campaign_sha256"],
        "tool_implementation_sha256": campaign["tool_implementation_sha256"],
        "runtime": campaign["runtime"],
        "model_alias": alias,
        "context_tokens": context,
        "loopback_port": selected_port,
        "n": campaign["n"],
        "harness_passes": campaign["harness_passes"],
        "model_passes": campaign["model_passes"],
        "execution_passes": campaign["execution_passes"],
    }
    body["qualification_sha256"] = _sha(body)
    _write_private(out_root / "qualification-receipt.json", body)
    return body


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hermes", type=Path, required=True)
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--alias", required=True)
    p.add_argument("--out-root", type=Path, required=True)
    p.add_argument(
        "--augmentation-root", type=Path,
        default=Path(__file__).resolve().parent,
    )
    p.add_argument("--profile-python", type=Path)
    p.add_argument("--seeds", default="0,1,2,3")
    p.add_argument("--families", default="all")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--context", type=int, default=65536)
    p.add_argument("--discovery-timeout", type=float, default=60.0)
    p.add_argument("--case-timeout", type=float, default=180.0)
    p.add_argument("--start-timeout", type=float, default=120.0)
    p.add_argument("--max-turns", type=int, default=8)
    args = p.parse_args(argv)

    result = run_qualification(
        hermes=args.hermes,
        server=args.server,
        model=args.model,
        alias=args.alias,
        out_root=args.out_root,
        augmentation_root=args.augmentation_root,
        profile_python=args.profile_python,
        seeds=_parse_csv_ints(args.seeds),
        families=_parse_families(args.families),
        port=args.port,
        context=args.context,
        discovery_timeout=args.discovery_timeout,
        case_timeout=args.case_timeout,
        start_timeout=args.start_timeout,
        max_turns=args.max_turns,
    )
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "qualification_sha256": result["qualification_sha256"],
        "tool_implementation_sha256": result["tool_implementation_sha256"],
        "n": result["n"],
        "harness_passes": result["harness_passes"],
        "model_passes": result["model_passes"],
        "execution_passes": result["execution_passes"],
        "out_root": str(args.out_root),
    }, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
