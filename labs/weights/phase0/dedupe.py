#!/usr/bin/env python3
"""Contamination check: training items against every development set.

  dedupe.py fingerprint                         # list sources, counts and the fingerprint digest
  dedupe.py check --episodes FILE --kind hare   # exit 1 if any training item overlaps a dev item
  dedupe.py check --episodes FILE --kind query

An item is rejected if it shares, with any development item:
  * a normalized structure (Amendment 1, section 2): for HARE, the same prompt skeleton (template
    lineage) or the same whole-item skeleton (pools.structure); for query tasks, the same question
    skeleton on a Weisfeiler-Lehman-equivalent tenant graph, or any tenant graph that is
    WL-equivalent to a development tenant (isomorphic graphs always collide; WL may also merge a
    rare non-isomorphic pair, which only makes the check stricter), or
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


# ------------------------------------------------------------------ structure
def wl_hash(t: dict, rounds: int = 4) -> str:
    """Weisfeiler-Lehman hash of a tenant graph with typed nodes and attributed edges. Role nodes keep
    their names (the role table is part of the schema); principals are anonymous."""
    import pools  # noqa: F401  (keeps import order: common first)
    T, _ = common.load_querywriter()
    label = {u["id"]: f"U:{u['enabled']}" for u in t["users"]}
    label.update({g: "G" for g in t["groups"]})
    label.update({sp: "S" for sp in t["sps"]})
    label.update({f"role:{r}": f"R:{r}:{tier}" for r, tier in T.ROLES})
    edges = [(a, g, "M") for a, g in t["member"]]
    edges += [(p, f"role:{r}", f"H:{m}:{'/' if sc == '/' else 'scoped'}") for p, r, m, sc in t["has_role"]]
    edges += [(o, sp, "O") for o, sp in t["owns"]]
    nbr = {n: [] for n in label}
    for a, b, k in edges:
        nbr[a].append(("out", k, b))
        nbr[b].append(("in", k, a))
    cur = dict(label)
    for _ in range(rounds):
        cur = {n: common.sha256_bytes((cur[n] + "|" + ",".join(sorted(f"{d}:{k}:{cur[m]}" for d, k, m in nbr[n])))
                                      .encode())[:16] for n in label}
    return common.sha256_bytes(",".join(sorted(cur.values())).encode())[:16]


def query_skeleton(q: dict, t: dict) -> str:
    text = q["question"]
    for x in sorted([u["id"] for u in t["users"]] + t["groups"] + t["sps"], key=len, reverse=True):
        text = text.replace(f"'{x}'", "'<ENTITY>'")
    return common.sha256_bytes(" ".join(text.casefold().split()).encode())[:16]


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
    import pools
    return {"id": e["id"], "source": source, "texts": texts, "ids": ids,
            "structures": {"lineage:" + pools.lineage(e), "structure:" + pools.structure(e)}}


def query_item(q: dict, tenant: dict, source: str = "train") -> dict:
    ids = {u["id"].casefold() for u in tenant["users"]} | {g.casefold() for g in tenant["groups"]} | \
          {s.casefold() for s in tenant["sps"]}
    g = wl_hash(tenant)
    return {"id": q["id"], "source": source, "texts": [q["question"]], "ids": ids | text_ids(q["question"]),
            "structures": {f"graph:{g}", f"question:{g}:{query_skeleton(q, tenant)}"}}


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
    return {"id": item_id, "source": source, "texts": texts, "ids": ids, "structures": set()}


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
    "rule8-flip-pairs": lambda: [hare_item(side, "rule8-flip-pairs") for p in common.read_jsonl(
        HERE / "rule8" / "evidence_flip_pairs.jsonl") for side in (p["a"], p["b"])],
}


_CACHE: dict = {}


def load_fingerprint() -> dict:
    if "fp" in _CACHE:
        return _CACHE["fp"]
    grams, ids, structs, counts = {}, {}, {}, {}
    for name, load in DEV_SOURCES.items():
        items = load()
        counts[name] = len(items)
        for it in items:
            for t in it["texts"]:
                for g in ngrams(t):
                    grams.setdefault(g, f"{name}:{it['id']}")
            for i in it["ids"]:
                ids.setdefault(i, f"{name}:{it['id']}")
            for k in it.get("structures", ()):
                structs.setdefault(k, f"{name}:{it['id']}")
    digest = common.sha256_bytes(common.canonical({"params": PARAMS, "ngrams": sorted(grams), "ids": sorted(ids),
                                                   "structures": sorted(structs)}))
    _CACHE["fp"] = {"grams": grams, "ids": ids, "structures": structs, "counts": counts, "sha256": digest}
    return _CACHE["fp"]


def check_items(items, fp) -> dict:
    rejected = []
    for it in items:
        gram_hits = sorted({g for t in it["texts"] for g in ngrams(t) if g in fp["grams"]})
        id_hits = sorted(i for i in it["ids"] if i in fp["ids"])
        st_hits = sorted(k for k in it.get("structures", ()) if k in fp["structures"])
        if gram_hits or id_hits or st_hits:
            rejected.append({"id": it["id"], "ngram_hits": [(g, fp["grams"][g]) for g in gram_hits[:3]],
                             "n_ngram_hits": len(gram_hits),
                             "id_hits": [(i, fp["ids"][i]) for i in id_hits[:5]],
                             "structure_hits": [(k, fp["structures"][k]) for k in st_hits[:3]]})
    return {"params": PARAMS, "fingerprint_sha256": fp["sha256"], "dev_items": fp["counts"],
            "checked": len(items), "accepted": len(items) - len(rejected), "rejected": rejected}


# ------------------------------------------------------------------ general-data mix vs regression set
REGRESSION_DIR = common.DEPS_DIR / "regression"


def regression_texts() -> dict:
    """Item texts of the pinned regression slices (fetch_deps.py --regression)."""
    import fetch_deps
    pins = list(fetch_deps.regression_files())
    missing = [f for repo, _, f, _ in pins if not (REGRESSION_DIR / repo / f).exists()]
    if missing:
        raise FileNotFoundError(f"run fetch_deps.py --regression (missing {missing[:2]})")
    for repo, _, f, want in pins:
        if common.sha256_file(REGRESSION_DIR / repo / f) != want:
            raise ValueError(f"regression file {f} does not match its pin")
    out = {}
    ife = REGRESSION_DIR / "google/IFEval/ifeval_input_data.jsonl"
    out["ifeval"] = [json.loads(x)["prompt"] for x in ife.read_text().splitlines() if x.strip()]
    bfcl = []
    for p in sorted((REGRESSION_DIR / "gorilla-llm/Berkeley-Function-Calling-Leaderboard").glob("BFCL_v3_*.json")):
        for line in p.read_text().splitlines():
            if line.strip():
                bfcl += [m.get("content", "") for turn in json.loads(line)["question"] for m in turn]
    out["bfcl"] = bfcl
    import pyarrow.parquet as pq
    keep = {q for v in json.loads((HERE / "regression" / "mmlu_pro_subset.json").read_text())["categories"].values()
            for q in v}
    rows = pq.read_table(REGRESSION_DIR / "TIGER-Lab/MMLU-Pro/data/test-00000-of-00001.parquet",
                         columns=["question_id", "question", "options"]).to_pylist()
    out["mmlu_pro"] = [r["question"] + " " + " ".join(r["options"]) for r in rows if r["question_id"] in keep]
    return out


def check_general(texts) -> dict:
    """Amendment 1, section 2: the general-data mixture must share no NGRAM run with the regression set."""
    reg = regression_texts()
    grams, whole = {}, {}
    for name, ts in reg.items():
        for i, t in enumerate(ts):
            whole.setdefault(" ".join(G.norm_tokens(t)), f"{name}:{i}")
            for g in ngrams(t):
                grams.setdefault(g, f"{name}:{i}")
    rejected = []
    for i, t in enumerate(texts):
        hits = sorted(g for g in ngrams(t) if g in grams)
        exact = whole.get(" ".join(G.norm_tokens(t)))
        if hits or exact:
            rejected.append({"index": i, "n_hits": len(hits), "exact": exact,
                             "first": (hits[0], grams[hits[0]]) if hits else None})
    return {"params": PARAMS, "regression_items": {k: len(v) for k, v in reg.items()},
            "checked": len(texts), "accepted": len(texts) - len(rejected), "rejected": rejected}


# ------------------------------------------------------------------ fingerprint for Astra's private reserve check
def prompt_scope(item: dict, episode: dict | None = None) -> dict:
    """Stage 1 (Amendment 2, D3): only what round 0 reveals anyway, the request text and the principal."""
    texts = item["texts"][:1]
    ids = text_ids(texts[0]) if texts else set()
    if episode is not None:
        ids.add(str(episode.get("principal", "")).casefold())
    return {"id": item["id"], "texts": texts, "ids": ids - {""},
            "structures": {k for k in item.get("structures", ()) if k.startswith(("lineage:", "question:"))}}


def export_fingerprint(items, scope: str = "full") -> dict:
    """Hashed training fingerprints for the reserve holder, who reports only pass/fail (Amendment 1,
    section 2; Amendment 2, D3). scope="prompts" (stage 1, before any batch) holds no note text, cause or
    hidden id; scope="full" (stage 2) is only for a pool whose teacher batches are sealed and revealed."""
    def h(x):
        return common.sha256_bytes(x.encode())[:16]
    return {"schema": "haven-weights-train-fingerprint-1", "scope": scope, "params": PARAMS,
            "hash_rule": "first 16 hex of sha256(utf-8 string); n-grams are space-joined norm_tokens",
            "items": len(items),
            "ngram_hashes": sorted({h(g) for it in items for t in it["texts"] for g in ngrams(t)}),
            "id_hashes": sorted({h(i) for it in items for i in it["ids"]}),
            "structure_keys": sorted({k for it in items for k in it.get("structures", ())})}


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
    g = sub.add_parser("check-general", help="general-data mixture (one JSON string per line) vs the regression set")
    g.add_argument("--texts", required=True)
    x = sub.add_parser("export-fingerprint", help="hashed training fingerprint for the reserve holder")
    x.add_argument("--episodes", required=True)
    x.add_argument("--kind", choices=("hare", "query"), required=True)
    x.add_argument("--out", required=True)
    x.add_argument("--scope", choices=("prompts", "full"), required=True,
                   help="prompts: stage 1, before any batch; full: stage 2, after the pool's batches are revealed")
    args = ap.parse_args(argv)
    if args.cmd == "check-general":
        rep = check_general([json.loads(line) for line in open(args.texts) if line.strip()])
        print(json.dumps({k: v for k, v in rep.items() if k != "rejected"} | {"rejected": len(rep["rejected"])}, indent=2))
        raise SystemExit(1 if rep["rejected"] else 0)
    if args.cmd == "export-fingerprint":
        items = items_from_file(args.episodes, args.kind)
        if args.scope == "prompts":
            rows = common.read_jsonl(args.episodes)
            eps = rows if args.kind == "hare" else [None] * len(rows)
            items = [prompt_scope(it, ep) for it, ep in zip(items, eps)]
        out = export_fingerprint(items, args.scope)
        pathlib.Path(args.out).write_text(json.dumps(out) + "\n")
        print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items()}, indent=2))
        return
    fp = load_fingerprint()
    if args.cmd == "fingerprint":
        print(json.dumps({"params": PARAMS, "sources": fp["counts"], "ngrams": len(fp["grams"]),
                          "ids": len(fp["ids"]), "structures": len(fp["structures"]),
                          "fingerprint_sha256": fp["sha256"]}, indent=2))
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
