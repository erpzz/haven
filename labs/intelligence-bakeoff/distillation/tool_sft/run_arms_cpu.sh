#!/usr/bin/env bash
# TS-2 on the CPU lane: build verified Claude-teacher data, train the teacher and the matched
# oracle-control arms with identical settings and step counts, then evaluate both once.
# Usage: run_arms_cpu.sh PRIVATE_RUN_DIR PYTHON   (teacher records at RUN_DIR/claude-train.jsonl)
set -euo pipefail
umask 077
R="$1"
PY="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
REV=c1899de289a04d12100db370d81485cdf75e47ca
export HF_HUB_OFFLINE=1 TRANSFORMERS_VERBOSITY=error
cd "$HERE"

/usr/bin/python3 run.py build --teacher "$R/claude-train.jsonl" --output "$R/data"
"$PY" cpu_lane.py train --data "$R/data/teacher_sft.jsonl" --revision "$REV" --output "$R/adapter-claude" --execute
steps=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["completed_steps"])' "$R/adapter-claude/training-receipt.json")
"$PY" cpu_lane.py train --data "$R/data/oracle_sft.jsonl" --revision "$REV" --output "$R/adapter-oracle" --max-steps "$steps" --execute
for arm in claude oracle; do
  "$PY" cpu_lane.py eval --revision "$REV" --adapter "$R/adapter-$arm" \
    --label "student-0.6b-$arm-sft-cpu" --sets heldout,legacy --out "$R/eval-$arm-sft.jsonl"
done
echo "ARMS COMPLETE"
