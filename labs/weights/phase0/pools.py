"""Pool manifests, scenario groups, template lineage and the no-action stratum (Amendment 1, section 2).

Every accessible pool gets a frozen manifest row per item: id, pool, family, template lineage,
scenario group, entity group, paired variants, disposition, split and sampling weight. Dev pools
are listed in Phase 0 (dev_manifest.jsonl); the training pool's manifest is written by
gen_hare.py when its secret seed is drawn.

Definitions (fixed here, before any collection):
* template lineage: sha256 of the prompt's normalized skeleton (entities, numbers, codes, times and
  dates replaced by typed placeholders). Two items share a lineage iff they use the same wording.
* disposition (the oracle's terminal disposition, from the contract alone):
    refusal               an expected claim is "refused"
    insufficient_evidence every expected claim is "unavailable" or "unknown"
    no_action_needed      a proposal is forbidden although the request asks for one conditionally
    answer                anything else
* no-action stratum: no_action_needed + insufficient_evidence. Its share in the training pool must
  equal its share in the public HARE development sets (frozen 180, fresh 179, untouched 179).
"""
from __future__ import annotations

import collections
import re

import common

_NUM = re.compile(r"\b\d+\b")
_CODE = re.compile(r"\b[A-Z]{3,}-\d{2,}\b")
_TIME = re.compile(r"\b\d{1,2}:\d{2}\b")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T[0-9:]+Z?)?\b")
_PROPOSAL_ASK = common.enforce._PROPOSAL_ASK
NO_ACTION = ("no_action_needed", "insufficient_evidence")


def entity_strings(e: dict) -> list[tuple[str, str]]:
    world = e.get("world") or {}
    out = [(str(e.get("principal", "")), "<PERSON>")]
    for n in world.get("notes", []):
        out += [(str(n["id"]), "<EV>"), (str(n["topic"]), "<TOPIC>")]
        if n.get("owner") != "shared":
            out.append((str(n["owner"]), "<PERSON>"))
        out += [(str(a), "<PERSON>") for a in n.get("audience", []) if a != "shared"]
    out += [(str(d["device_id"]), "<DEVICE>") for d in world.get("devices", [])]
    return [(s, t) for s, t in out if s]


def normalize(text: str, entities) -> str:
    """Typed placeholders for entities (longest first), then dates, times, codes and numbers."""
    for s, tag in sorted(set(entities), key=lambda x: -len(x[0])):
        text = re.sub(r"(?<![A-Za-z0-9_-])" + re.escape(s) + r"(?![A-Za-z0-9_-])", tag, text)
    text = _DATE.sub("<DATE>", text)
    text = _TIME.sub("<TIME>", text)
    text = _CODE.sub("<CODE>", text)
    text = _NUM.sub("<N>", text)
    text = re.sub(r"proposal-[0-9a-f]{10}", "<PROPOSAL>", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def lineage(e: dict) -> str:
    return common.sha256_bytes(normalize(e["prompt"], entity_strings(e)).encode())[:16]


def structure(e: dict) -> str:
    """Normalized structure of the whole item: prompt, note texts and roles, device states and causes."""
    ents = entity_strings(e)
    p = e.get("principal")
    world = e.get("world") or {}
    notes = sorted((normalize(n["text"], ents), "self" if n["owner"] == p else ("shared" if n["owner"] == "shared" else "other"),
                    p in n.get("audience", []), n.get("revision")) for n in world.get("notes", []))
    devices = sorted((d.get("kind"), d.get("state"), normalize(d.get("cause") or "", ents))
                     for d in world.get("devices", []))
    return common.sha256_bytes(common.canonical({"family": e.get("family"), "prompt": normalize(e["prompt"], ents),
                                                 "notes": notes, "devices": devices}))[:16]


def disposition(e: dict) -> str:
    c = e.get("contract") or {}
    statuses = [x["status"] for x in c.get("expect_claims", [])]
    if "refused" in statuses:
        return "refusal"
    if statuses and all(s in ("unavailable", "unknown") for s in statuses):
        return "insufficient_evidence"
    forbids = any(f["name"] == "haven_propose_action" for f in c.get("forbidden_calls", []))
    if forbids and _PROPOSAL_ASK.search(e.get("prompt", "")):
        return "no_action_needed"
    return "answer"


def entity_group(e: dict) -> str:
    return common.sha256_bytes(common.canonical(sorted({s for s, _ in entity_strings(e)})))[:16]


def manifest_row(e: dict, pool: str, split: str, scenario_group: str | None = None,
                 paired_variants=(), weight: float | None = None) -> dict:
    return {"id": e["id"], "pool": pool, "family": e.get("family"), "template_lineage": lineage(e),
            "structure": structure(e), "scenario_group": scenario_group or e["id"], "entity_group": entity_group(e),
            "paired_variants": sorted(paired_variants), "disposition": disposition(e), "split": split,
            "sampling_weight": weight}


def no_action_share(episodes) -> dict:
    d = collections.Counter(disposition(e) for e in episodes)
    n = sum(d.values())
    return {"n": n, "dispositions": dict(sorted(d.items())),
            "no_action_share": round(sum(d[k] for k in NO_ACTION) / n, 4) if n else None}


def dev_hare_pools() -> dict:
    return {"hare-frozen-180": common.bench.load_episodes(),
            "hare-fresh-s0-179": common.read_jsonl(common.SYSTEM0 / "fresh-s0-20261121.jsonl"),
            "hare-untouched-179": common.read_jsonl(common.SYSTEM0 / "fresh-x-untouched.jsonl")}


def frozen_no_action_rate() -> dict:
    pools = dev_hare_pools()
    allp = [e for v in pools.values() for e in v]
    return {"source": sorted(pools), "by_pool": {k: no_action_share(v) for k, v in pools.items()},
            **no_action_share(allp)}


def match_rate(episodes, target: float, key=lambda e: disposition(e) in NO_ACTION):
    """Largest subset whose stratum share equals the target (to 1 item): drops surplus from the
    over-represented side, last generated first. Deterministic."""
    yes = [e for e in episodes if key(e)]
    no = [e for e in episodes if not key(e)]
    if not episodes or target is None:
        return list(episodes)
    if len(yes) / len(episodes) > target:
        keep_yes = min(len(yes), round(target * len(no) / (1 - target))) if target < 1 else len(yes)
        yes = yes[:keep_yes]
    else:
        keep_no = min(len(no), round(len(yes) * (1 - target) / target)) if target > 0 else len(no)
        no = no[:keep_no]
    chosen = {id(e) for e in yes + no}
    return [e for e in episodes if id(e) in chosen]


# ------------------------------------------------------------------ dev manifest (Phase 0, public)
DEV_MANIFEST = common.HERE / "pools" / "dev_manifest.jsonl"


def _query_rows():
    import dedupe
    T, qrun = common.load_querywriter()
    rows = []
    for block in T.make_suite(qrun.SUITE_SEED, 12):
        t = block["tenant"]
        g = dedupe.wl_hash(t)
        for q in block["questions"]:
            rows.append({"id": q["id"], "pool": "querywriter-dev-84", "family": q["family"],
                         "template_lineage": dedupe.query_skeleton(q, t), "structure": g, "scenario_group": t["seed"],
                         "entity_group": t["seed"], "paired_variants": [],
                         "disposition": "nothing_found" if q["answer"] in ([], False, 0) else "answer",
                         "split": "dev", "sampling_weight": None})
    return rows


def _text_rows(name, path, key="id"):
    import json as _json
    data = _json.loads(path.read_text())
    rows = data if isinstance(data, list) else [data]
    return [{"id": str(r.get(key, i)), "pool": name, "family": r.get("family") or r.get("operation"),
             "template_lineage": None, "structure": None, "scenario_group": f"{name}:{r.get(key, i)}",
             "entity_group": None, "paired_variants": [], "disposition": None, "split": "dev",
             "sampling_weight": None} for i, r in enumerate(rows)]


def build_dev_manifest() -> list[dict]:
    rows = []
    for name, eps in dev_hare_pools().items():
        rows += [manifest_row(e, name, "dev") for e in eps]
    for p in common.read_jsonl(common.HERE / "rule8" / "evidence_flip_pairs.jsonl"):
        for side, other in (("a", "b"), ("b", "a")):
            rows.append(dict(manifest_row(p[side], "rule8-flip-pairs", "dev", scenario_group=p["pair_id"],
                                          paired_variants=[p[other]["id"]]), rule8_kind=p["kind"], rule8_side=side))
    rows += _query_rows()
    rows += _text_rows("purple-h2h-questions", common.PURPLE / "eval" / "questions.json")
    rows += _text_rows("purple-investigator", common.PURPLE / "investigator_eval" / "inputs.json")
    rows += _text_rows("purple-phase3-cases", common.PURPLE / "phase3_contract" / "cases.json")
    return rows


if __name__ == "__main__":
    import json as _json
    import sys as _sys
    rows = build_dev_manifest()
    if "--check" in _sys.argv:
        same = common.read_jsonl(DEV_MANIFEST) == _json.loads(_json.dumps(rows))
        print(_json.dumps({"rows": len(rows), "current": same}))
        raise SystemExit(0 if same else 1)
    DEV_MANIFEST.parent.mkdir(exist_ok=True)
    common.write_jsonl(DEV_MANIFEST, rows)
    print(_json.dumps({"rows": len(rows), "pools": dict(collections.Counter(r["pool"] for r in rows)),
                       "sha256": common.sha256_file(DEV_MANIFEST),
                       "no_action": {k: v for k, v in frozen_no_action_rate().items() if k != "by_pool"}}, indent=1))
