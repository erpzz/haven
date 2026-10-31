#!/bin/bash
# Controlled three-way comparison (ADAPTER_SELECTION_PREREGISTRATION.md) on Slink.
#   scripts/run_compare_slink.sh base=<gguf> adapter-A=<gguf> adapter-B=<gguf>
# One model at a time on :8095 with identical flags. Per model: thinking off, A/B/C on all 55 cases; then thinking on,
# condition C on the 20 held-out cases. The forge teacher and its timer are paused for the window (owner-approved via
# the forge session) and ALWAYS restarted on exit. Writes runs/cmp/<label>-{nothink,think}/ and runs/cmp/receipt.jsonl.
set -u
cd "$(dirname "$0")/.."
E=$HOME/.local/share/haven-model-lab/engines/b11146/llama-b11146/llama-server
FLAGS="--host 127.0.0.1 --port 8095 -c 24576 -np 1 --threads 12 -b 2048 -ub 2048 -fa auto --jinja"
OUT=runs/cmp
mkdir -p $OUT
restore() {
  systemctl --user stop haven-cyber-cmp 2>/dev/null
  systemctl --user start forge-teacher-server haven-forge.timer
  echo "{\"t\": \"$(date -u +%FT%TZ)\", \"event\": \"forge_restored\", \"teacher\": \"$(systemctl --user is-active forge-teacher-server)\", \"timer\": \"$(systemctl --user is-active haven-forge.timer)\"}" >> $OUT/receipt.jsonl
}
trap restore EXIT
systemctl --user stop haven-cyber-eval haven-cyber-qwythos 2>/dev/null
systemctl --user stop haven-forge.timer forge-teacher-server
echo "{\"t\": \"$(date -u +%FT%TZ)\", \"event\": \"forge_paused\", \"teacher\": \"$(systemctl --user is-active forge-teacher-server)\"}" >> $OUT/receipt.jsonl
for spec in "$@"; do
  label=${spec%%=*}; gguf=${spec#*=}
  sha=$(sha256sum "$gguf" | cut -d' ' -f1)
  systemctl --user reset-failed haven-cyber-cmp 2>/dev/null
  systemd-run --user --unit=haven-cyber-cmp --property=Nice=5 $E -m "$gguf" --alias "$label" $FLAGS >/dev/null
  for i in $(seq 1 120); do curl -sf 127.0.0.1:8095/health >/dev/null && break; sleep 5; done
  gpu=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader)
  offload=$(journalctl --user -u haven-cyber-cmp --no-pager | grep -o "offloaded [0-9]*/[0-9]* layers to GPU" | tail -1)
  t0=$(date -u +%FT%TZ)
  python3 -m haven_cyber.eval.harness --endpoint http://127.0.0.1:8095/v1 --model "$label" --conditions A,B,C --out $OUT/$label-nothink
  python3 -m haven_cyber.eval.harness --endpoint http://127.0.0.1:8095/v1 --model "$label" --think --conditions C --split heldout --out $OUT/$label-think
  python3 - "$label" "$gguf" "$sha" "$t0" "$gpu" "$offload" "$E $FLAGS" >> $OUT/receipt.jsonl <<'PY'
import hashlib, json, sys, datetime, pathlib
label, gguf, sha, t0, gpu, off, cmd = sys.argv[1:]
h = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
print(json.dumps({"event": "model_run", "label": label, "gguf": gguf, "gguf_sha256": sha, "start": t0,
                  "end": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "gpu_mem_after_load": gpu, "offload": off, "server": cmd + f" -m {gguf} --alias {label}",
                  "teacher_state": "paused", "harness_version": pathlib.Path("VERSION").read_text().strip() if pathlib.Path("VERSION").exists() else None,
                  "scenarios_sha256": h("eval/scenarios/v1.json"), "answers_sha256": h("eval/answers/v1.json")}))
PY
  systemctl --user stop haven-cyber-cmp
done
