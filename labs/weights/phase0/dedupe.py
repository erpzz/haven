#!/usr/bin/env python3
"""Contamination check: training items against every development set.

  dedupe.py fingerprint                         # list sources, counts and the fingerprint digest
  dedupe.py check --episodes FILE --kind hare   # exit 1 if any training item overlaps a dev item
  dedupe.py check --episodes FILE --kind query

An item is rejected if it shares, with any development item:
  * a long word sequence: any NGRAM-token run (generator.norm_tokens, within one text field), or
  * an entity identifier: principal, note owner, note topic, device id, evidence id, code-like
    value (WORD-123), proposal id, tenant user / group / service-principal id, or an identifier-
    like token in free text (8+ characters with a separator and a digit, dot or @). Dates are values,
    not identifiers, and are excluded.

Parameters are fixed here and recorded in every report, so they are set before any training
data is drawn. What counts as a development set is the list in DEV_SOURCES; every source is
read from a hash-pinned file (deps.json) or regenerated from a pinned seed.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
from common import BAKEOFF, PURPLE, SYSTEM0, generator as G  # noqa: E402

PARAMS = {"ngram": 8, "text_id_min_len": 8, "dates_are_ids": False,
          "tokenizer": "adjudicated/generator.py norm_tokens"}
_CODE = re.compile(r"\b[A-Z]{3,}-\d{2,}\b")
_PROPOSAL = re.compile(r"\bproposal-[0-9a-f]{10}\b")
_TEXT_ID = re.compile(r"[A-Za-z0-9]+(?:[.@_\-][A-Za-z0-9]+)+")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:t[0-9:]+z?)?$")


def text_ids(text: str) -> set[str]:
    out = set()
    for tok in _TEXT_ID.findall(text or ""):
        tok = tok.casefold()
        if len(tok) >= PARAMS["text_id_min_len"] and re.search(r"[0-9.@]", tok) and not _DATE.match(tok):
            out.add(tok)
    out |= {m.casefold() for m in _CODE.findall(text or "")}
    out |= set(_PROPOSAL.findall(text or ""))
    return out


def ngrams(text: str, n: int | None = None) -> set[str]:
    n = n or PARAMS["ngram"]
    toks = G.norm_tokens(text)
    return {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


# ------------------------------------------------------------------ items
def hare_item(e: dict, source: str = "train") -> dict:
    """Prompt, note texts and device causes; identifiers from the structured world."""
    world = e.get("world") or {}
    texts = [e.get("prompt") or ""] + [n.get("text") or "" for n in world.get("notes", [])] + \
            [d.get("cause") or "" for d in world.get("devices", []) if d.get("cause")]
    ids = {str(e.get("principal", "")).casefold()}
    for n in world.get("notes", []):
        ids |= {str(n["id"]).casefold(), str(n["topic"]).casefold()}
        if n.get("owner") != "shared":
            ids.add(str(n["owner"]).casefold())
    for d in world.get("devices", []):
        ids.add(str(d["device_id"]).casefold())
    for t in texts:
        ids |= text_ids(t)
    ids.discard("")
    return {"id": e["id"], "source": source, "texts": texts, "ids": ids}


def query_item(q: dict, tenant: dict, source: str = "train") -> dict:
    ids = {u["id"].casefold() for u in tenant["users"]} | {g.casefold() for g in tenant["groups"]} | \
          {s.casefold() for s in tenant["sps"]}
    return {"id": q["id"], "source": source, "texts": [q["question"]], "ids": ids | text_ids(q["question"])}


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def text_item(item_id: str, texts, source: str) -> dict:
    texts = [t for t in texts if t]
    ids = set()
    for t in texts:
        ids |= text_ids(t)
    return {"id": item_id, "source": source, "texts": texts, "ids": ids}


# ------------------------------------------------------------------ development sources
def _hare_file(path, name):
    return [hare_item(e, name) for e in common.read_jsonl(path)]


def _query_dev():
    T, qrun = common.load_querywriter()
    items = []
    for block in T.make_suite(qrun.SUITE_SEED, 12):
        items += [query_item(q, block["tenant"], "querywriter-dev-84") for q in block["questions"]]
    return items


def _json_file(path, name):
    data = json.loads(pathlib.Path(path).read_text())
    rows = data if isinstance(data, list) else [data]
    return [text_item(f"{name}:{i}", list(_strings(r)), name) for i, r in enumerate(rows)]


def _py_strings(path, name):
    tree = ast.parse(pathlib.Path(path).read_text())
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    return [text_item(f"{name}:{i}", [s], name) for i, s in enumerate(strings)]


TOOL_SFT = BAKEOFF / "distillation" / "tool_sft" / "frozen"
# Sources read and hashed but holding only labels and short codes (verdict enums, "G1"), so they
# contribute no n-gram or identifier. Listed so the test can tell this from a broken loader.
LABEL_ONLY = {"purple-investigator-gold"}
DEV_SOURCES = {
    "hare-frozen-180": lambda: _hare_file(BAKEOFF / "adjudicated" / "frozen" / "episodes.jsonl", "hare-frozen-180"),
    "hare-fresh-s0-179": lambda: _hare_file(SYSTEM0 / "fresh-s0-20261121.jsonl", "hare-fresh-s0-179"),
    "hare-untouched-179": lambda: _hare_file(SYSTEM0 / "fresh-x-untouched.jsonl", "hare-untouched-179"),
    "tool-sft-train": lambda: _hare_file(TOOL_SFT / "train.jsonl", "tool-sft-train"),
    "tool-sft-dev": lambda: _hare_file(TOOL_SFT / "dev.jsonl", "tool-sft-dev"),
    "tool-sft-heldout": lambda: _hare_file(TOOL_SFT / "heldout.jsonl", "tool-sft-heldout"),
    "querywriter-dev-84": _query_dev,
    "purple-h2h-questions": lambda: _json_file(PURPLE / "eval" / "questions.json", "purple-h2h-questions"),
    "purple-investigator-inputs": lambda: _json_file(PURPLE / "investigator_eval" / "inputs.json",
                                                     "purple-investigator-inputs"),
    "purple-investigator-gold": lambda: _json_file(PURPLE / "investigator_eval" / "gold.json",
                                                   "purple-investigator-gold"),
    "purple-phase3-cases": lambda: _json_file(PURPLE / "phase3_contract" / "cases.json", "purple-phase3-cases"),
    "purple-hermes-questions": lambda: _py_strings(PURPLE / "tests" / "hermes_questions.py",
                                                   "purple-hermes-questions"),
}


_CACHE: dict = {}


def load_fingerprint() -> dict:
    if "fp" in _CACHE:
        return _CACHE["fp"]
    grams, ids, counts = {}, {}, {}
    for name, load in DEV_SOURCES.items():
        items = load()
        counts[name] = len(items)
        for it in items:
            for t in it["texts"]:
                for g in ngrams(t):
                    grams.setdefault(g, f"{name}:{it['id']}")
            for i in it["ids"]:
                ids.setdefault(i, f"{name}:{it['id']}")
    digest = common.sha256_bytes(common.canonical({"params": PARAMS, "ngrams": sorted(grams), "ids": sorted(ids)}))
    _CACHE["fp"] = {"grams": grams, "ids": ids, "counts": counts, "sha256": digest}
    return _CACHE["fp"]


def check_items(items, fp) -> dict:
    rejected = []
    for it in items:
        gram_hits = sorted({g for t in it["texts"] for g in ngrams(t) if g in fp["grams"]})
        id_hits = sorted(i for i in it["ids"] if i in fp["ids"])
        if gram_hits or id_hits:
            rejected.append({"id": it["id"], "ngram_hits": [(g, fp["grams"][g]) for g in gram_hits[:3]],
                             "n_ngram_hits": len(gram_hits),
                             "id_hits": [(i, fp["ids"][i]) for i in id_hits[:5]]})
    return {"params": PARAMS, "fingerprint_sha256": fp["sha256"], "dev_items": fp["counts"],
            "checked": len(items), "accepted": len(items) - len(rejected), "rejected": rejected}


def items_from_file(path, kind):
    rows = common.read_jsonl(path)
    if kind == "hare":
        return [hare_item(e) for e in rows]
    return [query_item(r["question"], r["tenant"]) for r in rows]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fingerprint")
    c = sub.add_parser("check")
    c.add_argument("--episodes", required=True)
    c.add_argument("--kind", choices=("hare", "query"), required=True)
    c.add_argument("--report")
    args = ap.parse_args(argv)
    fp = load_fingerprint()
    if args.cmd == "fingerprint":
        print(json.dumps({"params": PARAMS, "sources": fp["counts"], "ngrams": len(fp["grams"]),
                          "ids": len(fp["ids"]), "fingerprint_sha256": fp["sha256"]}, indent=2))
        return
    report = check_items(items_from_file(args.episodes, args.kind), fp)
    if args.report:
        pathlib.Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rejected"} |
                     {"rejected": len(report["rejected"]), "first_rejections": report["rejected"][:5]}, indent=2))
    if report["rejected"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
