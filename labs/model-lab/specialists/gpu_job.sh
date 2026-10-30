#!/usr/bin/env bash
# SPEC-2 job for a rented CUDA Linux box with this repository checked out.
# Usage: gpu_job.sh FAMILY STAGE SIZE --approved "<owner, budget, date>" [--max-hours N] [--upload NAME]
#   FAMILY: medical | cyber      STAGE: baseline | rft      SIZE: large | small
# baseline: serve the pinned model with vLLM on loopback and score the family's frozen eval sets.
# rft:      bounded self-improvement loop on the family's training pools, then score the final adapter.
# Speech uses NeMo and has its own path (spec_stt.py); it is not run here.
# Nothing here stops or bills anything by itself; the caller terminates the rented instance.
set -euo pipefail
umask 077
FAMILY="$1"; STAGE="$2"; SIZE="$3"; shift 3
APPROVED=""; MAX_HOURS=8; UPLOAD=""
while [ $# -gt 0 ]; do
  case "$1" in
    --approved) APPROVED="$2"; shift 2 ;;
    --max-hours) MAX_HOURS="$2"; shift 2 ;;
    --upload) UPLOAD="$2"; shift 2 ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
done
[ -n "$APPROVED" ] || { echo "Refusing: pass --approved with the owner's budget approval." >&2; exit 1; }
command -v nvidia-smi >/dev/null || { echo "Refusing: no NVIDIA GPU on this host." >&2; exit 1; }
[ -n "${HF_TOKEN:-}" ] || { echo "Refusing: HF_TOKEN is needed for gated weights and private uploads." >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
W="${SPEC2_WORK:-$HOME/spec2}/$FAMILY-$SIZE-$STAGE-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$W"
echo "{\"approved\": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$APPROVED"), \"family\": \"$FAMILY\", \"stage\": \"$STAGE\", \"size\": \"$SIZE\", \"max_hours\": $MAX_HOURS}" > "$W/job.json"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > "$W/gpu.txt"

VENV="${SPEC2_WORK:-$HOME/spec2}/venv"
[ -x "$VENV/bin/python" ] || { python3 -m venv "$VENV"; "$VENV/bin/pip" install -q torch transformers peft accelerate \
  bitsandbytes vllm huggingface_hub pandas pyarrow; }
PY="$VENV/bin/python"
read -r MODEL REV < <("$PY" -c 'import json,sys; f=json.load(open(sys.argv[1]))["families"][sys.argv[2]][sys.argv[3]]; print(f["repo"], f["revision"])' \
  "$HERE/families.json" "$FAMILY" "$SIZE")
EVALS=$("$PY" -c 'import json,sys; sys.path.insert(0,sys.argv[2]); import spec_bench as sb; print(" ".join(e for e in json.load(open(sys.argv[1]))["families"][sys.argv[3]]["eval"] if e in sb.SOURCES))' \
  "$HERE/families.json" "$HERE" "$FAMILY")
POOLS=$("$PY" -c 'import json,sys; sys.path.insert(0,sys.argv[2]); import spec_bench as sb; print(" ".join(e for e in json.load(open(sys.argv[1]))["families"][sys.argv[3]]["train_pools"] if e in sb.SOURCES))' \
  "$HERE/families.json" "$HERE" "$FAMILY")
BENCH="${SPEC2_WORK:-$HOME/spec2}/bench"
[ -f "$BENCH/manifest.json" ] || "$PY" "$HERE/spec_bench.py" freeze --pin "$HERE/results/spec2-bench-manifest-20261030.json" --out "$BENCH"

PORT=18900
serve() {  # $1: optional adapter directory
  "$PY" -c 'import secrets; print(secrets.token_hex(24))' > "$W/key"
  local args=(serve "$MODEL" --revision "$REV" --host 127.0.0.1 --port "$PORT" --api-key "$(cat "$W/key")"
              --served-model-name base --max-model-len 8192)
  [ -n "${1:-}" ] && args+=(--enable-lora --max-lora-rank 64 --lora-modules "tuned=$1")
  "$VENV/bin/vllm" "${args[@]}" > "$W/serve.log" 2>&1 &
  echo $! > "$W/serve.pid"
  for _ in $(seq 1 360); do
    curl -sf -H "Authorization: Bearer $(cat "$W/key")" "http://127.0.0.1:$PORT/v1/models" >/dev/null && return 0
    sleep 5
  done
  echo "vLLM did not become ready; see $W/serve.log" >&2; return 1
}
stop_serving() { kill "$(cat "$W/serve.pid")" 2>/dev/null || true; wait "$(cat "$W/serve.pid")" 2>/dev/null || true; }
evaluate() {  # $1: served model name, $2: label
  for b in $EVALS; do
    "$PY" "$HERE/spec_bench.py" run --bench "$BENCH/$b.jsonl" --base-url "http://127.0.0.1:$PORT/v1" --model "$1" \
      --api-key-file "$W/key" --label "$2" --out "$W/eval-$2.jsonl"
  done
  "$PY" "$HERE/spec_bench.py" score --records "$W/eval-$2.jsonl" > "$W/eval-$2.summary.json"
}
trap stop_serving EXIT

run_stage() {
  case "$STAGE" in
    baseline)
      serve ""; evaluate base "$FAMILY-$SIZE-base"; stop_serving ;;
    rft)
      for p in $POOLS; do cat "$BENCH/$p.jsonl"; done > "$W/pool.jsonl"
      local q=(); [ "$SIZE" = large ] && q=(--qlora)
      "$PY" "$HERE/rft.py" loop --model "$MODEL" --revision "$REV" --backend vllm --pool "$W/pool.jsonl" \
        --work "$W/rft" --rounds 3 --per-round 2000 --samples 4 "${q[@]}"
      local adapter
      adapter=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["final_adapter"] or "")' "$W/rft/loop-receipt.json")
      [ -n "$adapter" ] || { echo "No round cleared the dev gate; nothing to score." >&2; return 0; }
      serve "$adapter"; evaluate tuned "$FAMILY-$SIZE-rft"; stop_serving
      if [ -n "$UPLOAD" ]; then
        "$PY" -c 'import sys; from huggingface_hub import HfApi; a=HfApi(); r=a.create_repo(sys.argv[2], private=True, exist_ok=True).repo_id; a.upload_folder(repo_id=r, folder_path=sys.argv[1]); print("uploaded", r)' \
          "$adapter" "SlinkyHaven/$UPLOAD"
      fi ;;
    *) echo "unknown stage $STAGE" >&2; return 2 ;;
  esac
}
export -f run_stage serve stop_serving evaluate
export FAMILY STAGE SIZE W PY VENV MODEL REV EVALS POOLS BENCH PORT HERE UPLOAD
timeout "${MAX_HOURS}h" bash -c "set -euo pipefail; run_stage"
echo "JOB COMPLETE: receipts in $W"
