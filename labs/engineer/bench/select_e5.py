#!/usr/bin/env python3
"""Preregistered task selection for E5 (morphogenesis/PREREGISTRATION_E5.json).

Ranks the calibration runs (Qwen, arm none, seed 7) hardest first: failed before succeeded, then more
steps, then more wall time, and keeps the first 6. Calibration rows are never analysed.

  select_e5.py e5-calibration.jsonl
"""
import json
import pathlib
import sys

KEEP = 6


def select(rows):
    ranked = sorted(rows, key=lambda r: (bool(r["success"]), -(r["steps"] or 0), -(r["wall_s"] or 0), r["task"]))
    return [r["task"] for r in ranked[:KEEP]]


if __name__ == "__main__":
    rows = [json.loads(l) for l in pathlib.Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    print(",".join(select(rows)))
