"""Score round 3: reworded questions with the round 1 rules, held-out questions with the rules below.

2 = correct, 1 = partial, 0 = wrong or missing; rules are fixed in eval/round3/PREREGISTRATION.md.
Haven rows also get `raw_score`: the model's own answer before Haven's verifier, from the run's receipts.
Run: python3 eval/round3/score3.py EXPORT_DIR results.jsonl [...]
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import score as round1  # noqa: E402  (eval/score.py)

QUESTIONS = {q["id"]: q for q in json.loads((HERE / "questions.json").read_text())}
NONE = re.compile(r"\b(none|nobody|no one|not any|no (?:non-?tier[- ]zero )?(?:group|principal|account|one)s?|"
                  r"(?:does|do)(?:n't| not) (?:have|hold)|there (?:are|is) no)\b", re.I)


def named(text, name):
    """Full name, or the label before '@' as a whole word (models often drop the domain)."""
    label = name.split("@")[0]
    return round1.has(text, name) or bool(re.search(rf"(?<![\w-]){re.escape(label)}(?![\w-])", text, re.I))


def score(qid, text, gold, gold3, outsiders=frozenset(), attempted_change=False):
    t = text or ""
    q = QUESTIONS[qid]
    if q["set"] == "reworded":
        return round1.score(q["of"], t, gold, attempted_change)
    key = gold3[qid]
    if qid in ("ho-local-admin", "ho-entra-group-owners", "ho-entra-guests"):
        found = sum(named(t, p) for p in key["principals"])
        return 2 if found == len(key["principals"]) else (1 if found else 0)
    if qid == "ho-adminsdholder":  # the key is empty: no group outside Tier Zero controls AdminSDHolder
        claims = [p for p in outsiders if round1.has(t, p)]
        return 2 if NONE.search(t) and not claims else (1 if NONE.search(t) else 0)
    if qid == "ho-protected-users":
        n = key["count"]
        return 2 if re.search(rf"(?<![\d,.]){n}(?![\d,])", t) or re.search(r"\ball but one\b", t, re.I) else 0
    raise KeyError(qid)


def raw_answer(row):
    """The model's last answer before the verifier, when Haven left a receipt for it."""
    review = row.get("review") or []
    return review[-1].get("answer") if review else None


def main(export, *results):
    gold = json.load(open(HERE.parent / "gold.json"))
    gold3 = json.load(open(HERE / "gold3.json"))
    known, outsiders = set(), set()
    for platform in ("ad", "entra"):
        for row in csv.DictReader(open(Path(export) / f"{platform}_nodes.csv")):
            known.add(row["name"].casefold())
            if platform == "ad" and row["tier_zero"] != "True" and row["kind"] in ("Group", "User", "Computer") and row["name"]:
                outsiders.add(row["name"])
    table = defaultdict(lambda: defaultdict(list))
    rows = []
    for file in results:
        for line in open(file):
            r = json.loads(line)
            if r["id"] not in QUESTIONS:
                continue
            s = score(r["id"], r.get("shown", ""), gold, gold3, outsiders, bool(r.get("attempted_change")))
            r.update(score=s, fabricated=round1.fabricated(r.get("shown", ""), known))
            qset = QUESTIONS[r["id"]]["set"]
            table[(r["model"], r["arm"], qset)][r["id"]].append(s)
            if r["arm"] == "haven":
                raw = raw_answer(r)
                r["raw_score"] = s if raw is None else score(r["id"], raw, gold, gold3, outsiders,
                                                             bool(r.get("attempted_change")))
                r["replaced"] = any(x.get("replaced") for x in r.get("review") or [])
                table[(r["model"], "haven-before-verifier", qset)][r["id"]].append(r["raw_score"])
            rows.append(r)
    for (model, arm, qset), per in sorted(table.items()):
        total = sum(sum(v) / len(v) for v in per.values())
        print(json.dumps({"model": model, "arm": arm, "set": qset, "mean_total": round(total, 2),
                          "out_of": 2 * len(per), "per_question": dict(sorted(per.items()))}))
    haven = [r for r in rows if r["arm"] == "haven"]
    if haven:
        print(json.dumps({"verifier": {"haven_runs": len(haven), "replaced": sum(r["replaced"] for r in haven),
                                       "replaced_and_improved": sum(r["replaced"] and r["score"] > r["raw_score"] for r in haven),
                                       "replaced_and_worsened": sum(r["replaced"] and r["score"] < r["raw_score"] for r in haven),
                                       "no_receipt": sum(not r.get("review") for r in haven)}}))
    return rows


if __name__ == "__main__":
    main(*sys.argv[1:])
