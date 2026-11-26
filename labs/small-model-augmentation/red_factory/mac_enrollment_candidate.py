#!/usr/bin/env python3
"""Create an UNREVIEWED Mac qualification enrollment candidate.

The output schema is intentionally different from the enrollment schema consumed by
mac_case_qualification.py. The qualification runner must reject this wrapper. An operator
reviews the measured bytes/profile/runtime provenance and only then creates the accepted
haven.mac-red-case-enrollment.v1 document from the reviewed inner candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import mac_case_qualification as mac
from local_runner import _write_private_json

CANDIDATE_SCHEMA = "haven.mac-red-case-enrollment-candidate.v1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def build_candidate(*, hermes: Path, hermes_home: Path,
                    env: Mapping[str, str] | None = None) -> dict[str, Any]:
    hermes = Path(hermes).expanduser().resolve()
    hermes_home = Path(hermes_home).expanduser().resolve()
    base_env = dict(os.environ if env is None else env)
    base_env.pop("PYTHONPATH", None)
    base_env.pop("PYTHONHOME", None)
    base_env["PYTHONNOUSERSITE"] = "1"
    base_env["HERMES_ENABLE_PROJECT_PLUGINS"] = "0"

    runtime = mac._runtime_package_snapshot(hermes, base_env)
    hermes_sha = mac._sha_file(hermes, executable=True)
    # Cross-check that the console script reports the same package identity measured
    # through its shebang interpreter. This still MEASURES; it does not bless the bytes.
    mac._version_probe(
        hermes, hermes_home,
        {
            "hermes_sha256": hermes_sha,
            "hermes_version": runtime["version"],
            "hermes_release_date": runtime["release_date"],
        },
        base_env,
    )

    candidate = {
        "schema": mac.ENROLLMENT_SCHEMA,
        "hermes_sha256": hermes_sha,
        "hermes_version": runtime["version"],
        "hermes_release_date": runtime["release_date"],
        "hermes_python_sha256": runtime["python_sha256"],
        "hermes_runtime_source_sha256": runtime["source_sha256"],
        "hermes_config_sha256": mac._sha_private_profile_file(
            hermes_home / "config.yaml"
        ),
        "hermes_profile_env_sha256": mac._sha_private_profile_file(
            hermes_home / ".env"
        ),
    }
    for key, path in mac.SOURCE_BINDINGS.items():
        candidate[key] = mac._sha_file(path)

    if set(candidate) != mac.ENROLLMENT_KEYS:
        raise mac.QualificationError("CANDIDATE_SHAPE_MISMATCH")

    candidate_sha = hashlib.sha256(_canon(candidate)).hexdigest()
    review = {
        "hermes_path": str(hermes),
        "hermes_home": str(hermes_home),
        "runtime_source_files": list(mac.HERMES_RUNTIME_FILES),
        "source_binding_paths": {
            key: str(path.resolve()) for key, path in mac.SOURCE_BINDINGS.items()
        },
    }
    body = {
        "schema": CANDIDATE_SCHEMA,
        "review_status": "unreviewed",
        "qualification_runner_accepts_this_wrapper": False,
        "candidate_sha256": candidate_sha,
        "candidate": candidate,
        "review": review,
    }
    body["wrapper_sha256"] = hashlib.sha256(_canon(body)).hexdigest()
    return body


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hermes", type=Path, required=True)
    p.add_argument("--hermes-home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    value = build_candidate(hermes=args.hermes, hermes_home=args.hermes_home)
    _write_private_json(args.out, value)
    print(json.dumps({
        "schema": value["schema"],
        "review_status": value["review_status"],
        "candidate_sha256": value["candidate_sha256"],
        "wrapper_sha256": value["wrapper_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
