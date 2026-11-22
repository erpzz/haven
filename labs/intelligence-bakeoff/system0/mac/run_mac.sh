#!/bin/bash
# HARE-S0-2-MAC: first measurement on a candidate deployment host (Apple Silicon Mac).
#
#   curl -fsSL https://raw.githubusercontent.com/erpzz/haven/claude/hare-s0-20261121/labs/intelligence-bakeoff/system0/mac/run_mac.sh -o run_mac.sh
#   bash run_mac.sh            # about 2-3 hours unattended; keep the Mac plugged in and awake
#
# It builds llama.cpp b11146 with Metal (UI off), downloads the pinned Qwen3.5-4B GGUF
# (sha256-checked), runs 4B plain and 4B full on the 179 untouched episodes, runs the
# query-writing arms (code, cypher, prose) on the development suite, and writes
# ~/Desktop/haven-mac-results.tgz (summaries and latency only, no transcripts).
# Re-running resumes: finished arms whose receipts cover every expected episode are kept.
# Nothing is installed system-wide: everything lives in ~/haven-mac.
set -eu

ROOT="$HOME/haven-mac"
REPO="https://github.com/erpzz/haven"
HARE_BRANCH="claude/hare-s0-20261121"
QW_BRANCH="claude/querywriter-20261121"
LLAMA_TAG="b11146"
GGUF_URL="https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/e87f176479d0855a907a41277aca2f8ee7a09523/Qwen3.5-4B-Q4_K_M.gguf"
GGUF_SHA="00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4"
PORT=18931

say() { printf '\n== %s\n' "$*"; }
die() { printf '\nSTOPPED: %s\n' "$*" >&2; exit 1; }

say "Checking the machine"
[ "$(uname -s)" = "Darwin" ] || die "this script is for macOS"
[ "$(uname -m)" = "arm64" ] || die "needs an Apple Silicon Mac (arm64)"
xcode-select -p >/dev/null 2>&1 || die "install the command line tools first: xcode-select --install"
command -v git >/dev/null || die "git missing (comes with the command line tools)"
command -v python3 >/dev/null || die "python3 missing (comes with the command line tools)"
CHIP="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Apple Silicon')"
MEM_GB="$(( $(sysctl -n hw.memsize) / 1073741824 ))"
HW="$CHIP, ${MEM_GB} GB unified memory, Metal, macOS $(sw_vers -productVersion)"
echo "$HW"
FREE_GB="$(df -g "$HOME" | awk 'NR==2 {print $4}')"
[ "${FREE_GB:-0}" -ge 8 ] || die "need at least 8 GB free disk space (have ${FREE_GB} GB)"
mkdir -p "$ROOT"

say "Python environment (cmake, kuzu) in $ROOT/venv"
[ -x "$ROOT/venv/bin/python" ] || python3 -m venv "$ROOT/venv"
"$ROOT/venv/bin/pip" install -q --upgrade pip >/dev/null
"$ROOT/venv/bin/pip" install -q "cmake>=3.28,<4.2"
QW_OK=1
"$ROOT/venv/bin/pip" install -q "kuzu==0.11.3" || { QW_OK=0; echo "kuzu unavailable for this Python: the query arms will be skipped"; }
PY="$ROOT/venv/bin/python"
CMAKE="$("$PY" -c 'import cmake,os;print(os.path.join(cmake.CMAKE_BIN_DIR,"cmake"))')"

say "Haven code"
for pair in "hare:$HARE_BRANCH" "qw:$QW_BRANCH"; do
  name="${pair%%:*}"; branch="${pair#*:}"
  if [ -d "$ROOT/$name/.git" ]; then
    git -C "$ROOT/$name" fetch -q origin "$branch" && git -C "$ROOT/$name" checkout -q -B "$branch" FETCH_HEAD
  else
    git clone -q --depth 1 --branch "$branch" "$REPO" "$ROOT/$name"
  fi
  echo "$name: $(git -C "$ROOT/$name" log -1 --format='%h %s' | cut -c1-80)"
done
S0="$ROOT/hare/labs/intelligence-bakeoff/system0"
QW="$ROOT/qw/labs/intelligence-bakeoff/querywriter"
(cd "$S0/.." && "$PY" -m unittest discover -s system0/tests >/dev/null 2>&1) || die "HARE tests failed"
(cd "$S0/.." && "$PY" system0/bench_s0.py check >/dev/null) || die "HARE frozen-suite check failed"
if [ "$QW_OK" = 1 ]; then (cd "$QW/.." && "$PY" querywriter/run.py check >/dev/null) || die "query suite check failed"; fi
echo "tests and suite checks pass"

say "llama.cpp $LLAMA_TAG with Metal"
ENGINE="$ROOT/llama.cpp/build/bin/llama-server"
if [ ! -x "$ENGINE" ]; then
  [ -d "$ROOT/llama.cpp/.git" ] || git clone -q --depth 1 --branch "$LLAMA_TAG" https://github.com/ggml-org/llama.cpp "$ROOT/llama.cpp"
  T0=$(date +%s)
  "$CMAKE" -S "$ROOT/llama.cpp" -B "$ROOT/llama.cpp/build" -DGGML_METAL=ON -DLLAMA_CURL=OFF \
    -DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
    > "$ROOT/cmake.log" 2>&1 || { tail -30 "$ROOT/cmake.log"; die "cmake configure failed (log: $ROOT/cmake.log)"; }
  "$CMAKE" --build "$ROOT/llama.cpp/build" --target llama-server -j "$(sysctl -n hw.ncpu)" \
    > "$ROOT/build.log" 2>&1 || { tail -40 "$ROOT/build.log"; die "build failed (log: $ROOT/build.log)"; }
  echo "built in $(( $(date +%s) - T0 )) s"
fi
DEVICES="$("$ENGINE" --list-devices 2>&1 || true)"
echo "$DEVICES" | grep -q "(none)" && { echo "$DEVICES"; die "llama-server does not see the Metal GPU"; }
"$ENGINE" --list-devices 2>&1 | sed -n '1,4p'

say "Model (pinned, sha256-checked)"
GGUF="$ROOT/models/Qwen3.5-4B-Q4_K_M.gguf"
mkdir -p "$ROOT/models"
if [ ! -f "$GGUF" ] || [ "$(shasum -a 256 "$GGUF" | cut -d' ' -f1)" != "$GGUF_SHA" ]; then
  curl -fL --retry 5 -o "$GGUF.part" "$GGUF_URL" && mv "$GGUF.part" "$GGUF"
fi
[ "$(shasum -a 256 "$GGUF" | cut -d' ' -f1)" = "$GGUF_SHA" ] || die "model checksum mismatch"
echo "ok"

say "HARE: 4B plain and 4B full on 179 untouched episodes (about 1-2 h)"
OUT="$ROOT/results"
mkdir -p "$OUT/hare" "$OUT/querywriter"
caffeinate -dimsu -w $$ &   # keep the Mac awake while this script runs
(cd "$S0" && "$PY" run_extension.py --engine "$ENGINE" --model-4b "$GGUF" --out "$OUT/hare" \
   --hardware "$HW" --arms 4b-plain,4b-full --prereg PREREGISTRATION_S0X_MAC.json)

if [ "$QW_OK" = 1 ]; then
say "Query-writing arms on the development suite (84 questions each)"
"$ENGINE" -m "$GGUF" --host 127.0.0.1 --port $PORT -c 16384 -ngl 99 --jinja -np 1 -fa auto --fit off --no-webui \
  > "$OUT/querywriter/server.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
for i in $(seq 1 200); do curl -fs "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q ok && break; sleep 3; done
for arm in code cypher prose; do
  if [ ! -f "$OUT/querywriter/4b-$arm.summary.json" ]; then
    rm -f "$OUT/querywriter/4b-$arm.jsonl"
    (cd "$QW" && "$PY" run.py eval --arm "$arm" --base-url "http://127.0.0.1:$PORT/v1" --model qwen35-4b \
       --label "mac-4b-$arm" --out "$OUT/querywriter/4b-$arm.jsonl")
  fi
done
kill $SRV 2>/dev/null || true
fi

say "Latency summary and results bundle"
"$PY" - "$OUT" "$HW" <<'PYEOF'
import json, math, pathlib, sys
out, hw = pathlib.Path(sys.argv[1]), sys.argv[2]
def p95(v):
    v = sorted(v); return round(v[max(0, math.ceil(0.95 * len(v)) - 1)], 3) if v else None
lat = {"hardware": hw, "gate": "warm p95 <= 15 s per request (issue #117)", "arms": {}}
for f in sorted((out / "hare").glob("*-untouched.jsonl")):
    secs = [json.loads(l)["elapsed_seconds"] for l in open(f)]
    lat["arms"][f.stem] = {"n": len(secs), "mean_s": round(sum(secs) / len(secs), 3), "p95_s": p95(secs),
                           "meets_gate": (p95(secs) or 99) <= 15}
for f in sorted((out / "querywriter").glob("*.jsonl")):
    secs = [json.loads(l)["seconds"] for l in open(f)]
    lat["arms"]["qw-" + f.stem] = {"n": len(secs), "mean_s": round(sum(secs) / len(secs), 3), "p95_s": p95(secs)}
load = out / "hare" / "load-seconds-4b.json"
if load.exists():
    lat["cold_load_seconds"] = json.loads(load.read_text())["cold_load_seconds"]
(out / "latency.json").write_text(json.dumps(lat, indent=2) + "\n")
print(json.dumps(lat, indent=2))
PYEOF
(cd "$OUT" && tar czf "$HOME/Desktop/haven-mac-results.tgz" latency.json hare/*.summary.json hare/results-extension.json \
   hare/load-seconds-4b.json querywriter/*.summary.json 2>/dev/null || tar czf "$HOME/Desktop/haven-mac-results.tgz" latency.json hare/*.summary.json querywriter/*.summary.json)
say "Done. Send ~/Desktop/haven-mac-results.tgz back to Claude."
