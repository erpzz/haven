"""Summarise scored head-to-head results as a Markdown table, per model and arm.

  python3 eval/report.py gold.json EXPORT_DIR results.jsonl > RESULTS.md
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402

ARMS = ("stock-model", "stock-hermes", "haven")


def main(gold, export, results):
    rows = score.main(gold, export, results)
    questions = [q["id"] for q in json.loads((Path(__file__).with_name("questions.json")).read_text())]
    by = defaultdict(list)
    for r in rows:
        by[(r["model"], r["arm"])].append(r)
    print("| Model | Arm | Mean total (of 16) | " + " | ".join(questions) + " | Median s | Fabricated names | State changes |")
    print("| --- | --- | ---: | " + " | ".join("---:" for _ in questions) + " | ---: | ---: | ---: |")
    for model in sorted({m for m, _ in by}):
        for arm in ARMS:
            rs = by.get((model, arm))
            if not rs:
                continue
            per = {q: [r["score"] for r in rs if r["id"] == q] for q in questions}
            total = sum(statistics.mean(v) for v in per.values() if v)
            cells = " | ".join(f"{statistics.mean(v):.1f}" if v else "—" for v in per.values())
            fab = sum(len(r["fabricated"]) for r in rs)
            changes = sum(bool(r.get("attempted_change")) for r in rs)
            print(f"| {model} | {arm} | {total:.2f} | {cells} | {statistics.median(r['seconds'] for r in rs):.0f} | "
                  f"{fab} | {changes} |")


if __name__ == "__main__":
    main(*sys.argv[1:])
