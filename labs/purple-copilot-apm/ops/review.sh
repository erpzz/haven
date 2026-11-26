#!/usr/bin/env bash
# Ask Purple Copilot questions through Hermes Agent with a local model. Run from the lab directory after
# ./ops/lab.sh up (CE does not need to be running; the review reads the local history).
#   ./ops/review.sh                      interactive Hermes chat
#   ./ops/review.sh "What should we fix first in AD?"
# Sets up, once, under $APM_STATE: Hermes v2026.9.24 (with its MCP extra), llama.cpp b11146 (Metal on macOS,
# CUDA when nvcc is present, otherwise CPU), the hash-checked Qwen3.5-4B Q4_K_M model and a Hermes profile.
# Overrides: LLAMA_SERVER=/path/to/llama-server, APM_MODEL_FILE=/path/to/model.gguf (still hash-checked),
# REVIEW_PORT (default 8091). Works with the bash 3.2 that ships with macOS.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
LAB=$PWD
export APM_STATE=${APM_STATE:-"$HOME/.local/state/purple-copilot-apm"}
PORT=${REVIEW_PORT:-8091}
HERMES_REF=v2026.9.24
LLAMA_TAG=b11146
MODEL_URL=https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/e87f176479d0855a907a41277aca2f8ee7a09523/Qwen3.5-4B-Q4_K_M.gguf
MODEL_SHA=00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4
ALIAS=qwen3.5-4b
if command -v sha256sum >/dev/null; then sha() { sha256sum "$1" | cut -d' ' -f1; }
else sha() { shasum -a 256 "$1" | cut -d' ' -f1; }; fi

[[ -f "$APM_STATE/history.sqlite3" ]] || { echo "No Purple Copilot history yet; run ./ops/lab.sh up first" >&2; exit 1; }
command -v uv >/dev/null || { echo "Install uv first: https://docs.astral.sh/uv/" >&2; exit 1; }

# Hermes Agent: upstream supports editable installs only. The mcp extra is needed for MCP servers.
HERMES_DIR="$APM_STATE/hermes-agent"
if [[ ! -x "$HERMES_DIR/.venv/bin/hermes" ]]; then
    rm -rf "$HERMES_DIR"
    git clone -q --depth 1 --branch "$HERMES_REF" https://github.com/NousResearch/hermes-agent "$HERMES_DIR"
    (cd "$HERMES_DIR" && uv venv -q .venv --python 3.11 && uv pip install -q -p .venv/bin/python -e ".[mcp]")
fi
HERMES="$HERMES_DIR/.venv/bin/hermes"

# llama.cpp at the engine Haven pins for Qwen.
if [[ -z "${LLAMA_SERVER:-}" ]]; then
    LLAMA_DIR="$APM_STATE/llama.cpp"
    LLAMA_SERVER="$LLAMA_DIR/build/bin/llama-server"
    if [[ ! -x "$LLAMA_SERVER" ]]; then
        command -v cmake >/dev/null || { echo "Install cmake first (macOS: brew install cmake)" >&2; exit 1; }
        rm -rf "$LLAMA_DIR"
        git clone -q --depth 1 --branch "$LLAMA_TAG" https://github.com/ggml-org/llama.cpp "$LLAMA_DIR"
        flags="-DLLAMA_CURL=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF"
        if [[ "$(uname -s)" != Darwin ]] && command -v nvcc >/dev/null; then flags="$flags -DGGML_CUDA=ON"; fi
        # shellcheck disable=SC2086
        cmake -S "$LLAMA_DIR" -B "$LLAMA_DIR/build" $flags >/dev/null
        cmake --build "$LLAMA_DIR/build" --target llama-server -j "$(getconf _NPROCESSORS_ONLN)" >/dev/null
    fi
fi

# Model, hash-checked whether downloaded here or supplied.
MODEL=${APM_MODEL_FILE:-"$APM_STATE/models/Qwen3.5-4B-Q4_K_M.gguf"}
if [[ ! -f "$MODEL" ]]; then
    mkdir -p "$(dirname "$MODEL")"
    curl --fail --location --retry 3 "$MODEL_URL" --output "$MODEL.part" && mv "$MODEL.part" "$MODEL"
fi
[[ "$(sha "$MODEL")" == "$MODEL_SHA" ]] || { echo "Model checksum mismatch: $MODEL" >&2; exit 1; }

# Model server: loopback only, 64k context (Hermes's minimum). CPU-only hosts use an 8-bit KV cache.
if ! curl -fs "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    extra=""
    if [[ "$(uname -s)" != Darwin ]] && ! command -v nvidia-smi >/dev/null; then extra="-ctk q8_0 -ctv q8_0 -ub 256"; fi
    # shellcheck disable=SC2086
    nohup "$LLAMA_SERVER" -m "$MODEL" --host 127.0.0.1 --port "$PORT" -c 65536 -np 1 --jinja -ngl 99 \
        --alias "$ALIAS" $extra > "$APM_STATE/review-model.log" 2>&1 &
    for _ in $(seq 1 120); do
        curl -fs "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break
        sleep 2
    done
    curl -fs "http://127.0.0.1:$PORT/health" >/dev/null || { echo "Model server failed; see $APM_STATE/review-model.log" >&2; exit 1; }
fi

# Hermes profile for review: the Purple Copilot plugin, its tools offered directly, nothing else.
export HERMES_HOME="$APM_STATE/hermes-home"
mkdir -p "$HERMES_HOME"
cat > "$HERMES_HOME/config.yaml" <<YAML
model:
  provider: custom
  base_url: http://127.0.0.1:$PORT/v1
  default: $ALIAS
  api_key: local
plugins:
  enabled:
    - purple-copilot
tools:
  tool_search:
    enabled: "off"
YAML
export HERMES_ENABLE_PROJECT_PLUGINS=1 PURPLE_COPILOT_LAB="$LAB" OPENAI_API_KEY=local
if [[ $# -gt 0 ]]; then
    exec "$HERMES" chat --oneshot --toolsets purple-copilot --provider custom --model "$ALIAS" -q "$*"
fi
echo "Purple Copilot review (Hermes $HERMES_REF, $ALIAS). Model server: 127.0.0.1:$PORT. Ctrl-D to leave."
exec "$HERMES" chat --toolsets purple-copilot --provider custom --model "$ALIAS"
