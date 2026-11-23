"""Summarize observations available at a selected clock without asserting effective access."""

from collections import defaultdict

from .formats import utc


def observation_groups(rows, receipts, *, posture):
    groups = defaultdict(list)
    for row in rows:
        prefix = (
            row["dataset"],
            row["tenant"],
            row["native_kind"],
            (row["native_id"] or "").casefold(),
        )
        if posture:
            key = (
                *prefix,
                row["test_id"],
                row.get("catalog") or receipts[row["artifact"]]["producer_revision"],
            )
        elif "assignment_mode" in row:
            system = row["rbac_system"]
            instance = row.get("assignment_instance_id") or row.get("assignment_id")
            if not instance and row.get("edge_kind", "").endswith("RoleAssignment"):
                instance = row["target"]
            if not instance:
                # A role-level projection can summarize several assignment instances.
                # Retain it among the raw observations; it adds no independent entitlement.
                continue
            key = (*prefix, system, instance.casefold(), row.get("scope"))
        else:
            continue
        groups[key].append(row)
    summaries = []
    field = "result" if posture else "assignment_mode"
    for key, observations in groups.items():
        timeline = sorted(
            observations, key=lambda r: utc(receipts[r["artifact"]]["collected"])
        )
        latest = utc(receipts[timeline[-1]["artifact"]]["collected"])
        current = [
            r for r in timeline if utc(receipts[r["artifact"]]["collected"]) == latest
        ]
        values = sorted({r[field] for r in current})
        summaries.append(
            dict(
                key=key,
                latest_observed=latest.isoformat(),
                values=values,
                conflict=len(values) > 1,
                historical_disagreement=len({r[field] for r in timeline}) > 1,
                observations=[[r["artifact"], r["record"]] for r in timeline],
                latest_records=[[r["artifact"], r["record"]] for r in current],
            )
        )
    return summaries
