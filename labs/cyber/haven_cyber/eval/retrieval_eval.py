"""Retrieval-only evaluation: recall@k of hand-labelled relevant documents (eval/retrieval_gold_v1.json).

    python -m haven_cyber.eval.retrieval_eval [--k 3]

Compares plain question retrieval (what the frozen v1 harness does) with opt-in artifact expansion.
"""
from __future__ import annotations

import argparse
import json

from .. import EVAL
from ..kb import KB


def run(k: int = 3) -> dict:
    sc = json.loads((EVAL / "scenarios" / "v1.json").read_text())["scenarios"]
    gold = json.loads((EVAL / "retrieval_gold_v1.json").read_text())["gold"]
    kb = KB()
    out = {}
    for mode in ("plain", "expanded"):
        hit, misses = 0, []
        for s in sc:
            _, hits = kb.retrieve(s["question"], k=k, artifacts=s.get("artifacts"), expand=(mode == "expanded"))
            ok = bool({h.doc_id for h in hits} & set(gold[s["id"]]))
            hit += ok
            if not ok:
                misses.append(s["id"])
        out[mode] = {"recall_at_k": round(hit / len(sc), 3), "hits": hit, "n": len(sc), "misses": misses}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    print(json.dumps(run(ap.parse_args().k), indent=1))
