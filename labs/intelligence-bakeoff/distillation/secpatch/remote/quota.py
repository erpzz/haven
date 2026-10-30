"""Read precise Kaggle account quota; write private snapshots outside Git.

No job submission or interactive login. Uses the official authenticated SDK
bundled with Kaggle CLI 2.2.5. Never emits credentials or a complete environment.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=pathlib.Path, required=True)
    p.add_argument("--before", type=pathlib.Path, help="Compare account GPU usage in same quota window")
    p.add_argument("--require-remaining-seconds", type=int, default=0)
    a = p.parse_args()
    if any((d / ".git").exists() for d in (a.output.resolve(), *a.output.resolve().parents)):
        p.error("Store private account snapshots outside Git")
    from kaggle import api  # Official library performs authentication; fails closed.
    response = api.quota_view()
    q = response.gpu_quota
    if q is None or response.quota_refresh_time is None:
        p.error("No provider GPU quota or reset window available")
    used, total = q.time_used.total_seconds(), q.total_time_allowed.total_seconds()
    snapshot = {"provider": "Kaggle", "source": "official_api_get_accelerator_quota_statistics",
                "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "account": api.get_config_value(api.CONFIG_NAME_USER),
                "refresh_at": response.quota_refresh_time.isoformat(),
                "gpu_used_seconds": used, "gpu_total_seconds": total,
                "gpu_remaining_seconds": max(0, total-used)}
    if a.before:
        before = json.loads(a.before.read_text())
        if before["account"] != snapshot["account"] or before["refresh_at"] != snapshot["refresh_at"] or used < before["gpu_used_seconds"]:
            p.error("Quota identity/window changed; cannot attribute a consumption delta")
        snapshot["account_gpu_consumed_seconds_since_before"] = used - before["gpu_used_seconds"]
        snapshot["attribution_limit"] = "Account total; attributable to this experiment only if no other GPU sessions ran"
    os.umask(0o077)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x") as f:
        json.dump(snapshot, f, indent=2)
    if snapshot["gpu_remaining_seconds"] < a.require_remaining_seconds:
        p.error("Insufficient free GPU quota; snapshot saved, do not submit")
    print("Authenticated quota snapshot saved privately; GPU remaining seconds=" + str(snapshot["gpu_remaining_seconds"]))


if __name__ == "__main__":
    main()
