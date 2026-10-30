#!/usr/bin/env bash
# One approved GPU window: train the secpatch student on 3 seeds, evaluate each adapter on the held-out set
# (plain and with Bandit evidence), and register the runs. Nothing is promoted or served automatically.
#
#   secpatch/gpu_window.sh --approved "owner, 2026-10-28 window"     # refuses without an approval note
#   ... --allow-gpu-peer forge-teacher-server.service                 # share the GPU with a named unit
#
# Preflight refuses to start if any process outside the allowed units holds the GPU, if less than
# --min-free-mib VRAM is free, or if Strata is up. It never stops anything.
# Rollback: delete $S/runs/<run> and `registry.py rollback`; no runtime or service is changed.
set -euo pipefail
APPROVED=""
SEEDS="42 7 13"
PEERS=()
MIN_FREE_MIB=3000
while [ $# -gt 0 ]; do
  case "$1" in
    --approved) APPROVED="$2"; shift 2 ;;
    --seeds) SEEDS="$2"; shift 2 ;;
    --allow-gpu-peer) PEERS+=("$2"); shift 2 ;;
    --min-free-mib) MIN_FREE_MIB="$2"; shift 2 ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
done
[ -n "$APPROVED" ] || { echo "Refusing: pass --approved \"<who approved this GPU window, when>\"." >&2; exit 2; }

S=${SECPATCH_STATE:-$HOME/.local/state/haven-secpatch}
C=$(cd "$(dirname "$0")" && pwd)
PY=${SECPATCH_TRAIN_PY:-$HOME/.local/share/haven-training-venv/bin/python}
BANDIT=${SECPATCH_BANDIT:-$HOME/.local/share/haven-secpatch-venv/bin/bandit}
REV=${SECPATCH_REVISION:-c1899de289a04d12100db370d81485cdf75e47ca}
DATA=${SECPATCH_DATA:-$S/data-v2}
# 1536 keeps 89% of v2 rows and fits beside a 2.5 GiB GPU neighbour; skipped rows are counted in each receipt.
MAX_LENGTH=${SECPATCH_MAX_LENGTH:-1536}
export HF_HOME=${HF_HOME:-$HOME/.local/share/haven-training-cache} HF_HUB_OFFLINE=1

allowed=""
for unit in ${PEERS[@]+"${PEERS[@]}"}; do
  pid=$(systemctl --user show -p MainPID --value "$unit" 2>/dev/null || true)
  [ -n "$pid" ] && [ "$pid" != 0 ] && allowed="$allowed $pid $(pgrep -P "$pid" | tr '\n' ' ' || true)"
done
busy=""
for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader | tr -d ' '); do
  case " $allowed " in *" $pid "*) ;; *) busy="$busy $pid" ;; esac
done
if [ -n "$busy" ]; then echo "Refusing: GPU in use by PID(s)$busy outside the allowed units. Nothing was stopped." >&2; exit 3; fi
free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1 | tr -d ' ')
if [ "${free:-0}" -lt "$MIN_FREE_MIB" ]; then echo "Refusing: ${free} MiB VRAM free, need $MIN_FREE_MIB." >&2; exit 3; fi
if [ "$(systemctl --user is-active haven-strata.service || true)" = active ]; then
  echo "Refusing: haven-strata.service is active." >&2; exit 3
fi

mkdir -p "$S/runs" "$S/eval"
printf '{"approved": %s, "started_at": "%s", "seeds": "%s", "data": "%s", "gpu_peers": %s, "vram_free_mib": %s}\n' \
  "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$APPROVED")" "$(date -u +%FT%TZ)" "$SEEDS" "$DATA" \
  "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1:]))' ${PEERS[@]+"${PEERS[@]}"})" "$free" >> "$S/runs/gpu-windows.jsonl"

for seed in $SEEDS; do
  run="qwen3-0.6b-secpatch-v2-s$seed"
  "$PY" "$C/train.py" --data "$DATA/train.jsonl" --revision "$REV" --output "$S/runs/$run" \
    --device cuda --epochs 2 --batch 8 --seed "$seed" --max-length "$MAX_LENGTH" --execute --resume
  for arm in plain tools; do
    flag=""; [ "$arm" = tools ] && flag=--with-tools
    "$PY" "$C/evaluate.py" --eval "$DATA/eval-heldout.jsonl" --backend hf --model Qwen/Qwen3-0.6B --revision "$REV" \
      --adapter "$S/runs/$run/adapter" --device cuda --bandit "$BANDIT" $flag --out "$S/eval/$run-$arm"
  done
  python3 "$C/registry.py" --root "$S/adapters" register "$S/runs/$run" "secpatch-0.6b-v2-s$seed" || true
  python3 "$C/registry.py" --root "$S/adapters" attach-eval "secpatch-0.6b-v2-s$seed" "$S/eval/$run-plain/summary.json"
done
# Same-device base arm, so GPU numbers compare like for like with the adapters.
"$PY" "$C/evaluate.py" --eval "$DATA/eval-heldout.jsonl" --backend hf --model Qwen/Qwen3-0.6B --revision "$REV" \
  --device cuda --bandit "$BANDIT" --out "$S/eval/qwen3-0.6b-plain-cuda"
python3 "$C/registry.py" --root "$S/adapters" attach-eval base "$S/eval/qwen3-0.6b-plain-cuda/summary.json"
python3 "$C/report.py" --summaries "$S"/eval/qwen3-0.6b-plain-cuda/summary.json "$S"/eval/qwen3-0.6b-secpatch-v2-s*-*/summary.json
echo "Done. Promotion is a separate, gated step: registry.py promote <name> <eval_sha256>."
