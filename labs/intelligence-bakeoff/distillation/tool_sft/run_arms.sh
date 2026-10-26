#!/usr/bin/env bash
# Build verified data, train the teacher and oracle-control arms with identical
# settings and step counts, evaluate both once, then restore the fast 4B model.
# Usage: run_arms.sh PRIVATE_OUTPUT_DIR   (after the teacher session has stopped)
set -euo pipefail
umask 077
R="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HOME/.local/share/haven-training-venv/bin/python"
REV=c1899de289a04d12100db370d81485cdf75e47ca
export HF_HOME="$HOME/.local/share/haven-training-cache" HF_HUB_OFFLINE=1
cd "$HERE"

if systemctl --user is-active --quiet haven-strata; then
  echo "haven-strata is still running; one GPU owner at a time." >&2; exit 1
fi
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
if [ "$used" -gt 512 ]; then echo "GPU in use (${used} MiB)." >&2; exit 1; fi
# Leave a usable runtime even if a step fails.
trap '/usr/bin/python3 "$HOME/projects/haven/ops/haven-core/labctl.py" load qwen35-4b --wait --timeout 300 >/dev/null && echo "4B restored"' EXIT

/usr/bin/python3 run.py build --teacher "$R/teacher-train.jsonl" --output "$R/data"
"$PY" train.py --data "$R/data/teacher_sft.jsonl" --revision "$REV" --output "$R/adapter-teacher" --execute
steps=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["completed_steps"])' "$R/adapter-teacher/training-receipt.json")
"$PY" train.py --data "$R/data/oracle_sft.jsonl" --revision "$REV" --output "$R/adapter-oracle" --max-steps "$steps" --execute
for arm in teacher oracle; do
  "$PY" run.py eval --backend hf --model Qwen/Qwen3-0.6B --revision "$REV" --adapter "$R/adapter-$arm" \
    --label "student-0.6b-$arm-sft" --sets dev,heldout,legacy --out "$R/eval-$arm-sft.jsonl"
done
echo "ARMS COMPLETE"
