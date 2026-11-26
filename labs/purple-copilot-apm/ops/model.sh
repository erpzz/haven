#!/usr/bin/env bash
set -euo pipefail
umask 077
state=${APM_STATE:-"$HOME/.local/state/purple-copilot-apm"}
mkdir -p "$state"
cd "$state"
model=${APM_MODEL_FILE:-"$state/qwen3-8b.gguf"}
sum=38833d850e00f75bac26c0c848f2fde9100a5a21c18aae89cfd8611efca6194b
if [[ ! -f "$model" ]]; then
    curl -fL --retry 2 https://huggingface.co/bartowski/Qwen_Qwen3-8B-GGUF/resolve/0b69f75b7472688e6808490aa2b85efdb81b5ce7/Qwen_Qwen3-8B-IQ2_M.gguf -o "$model.part"
    echo "$sum  $model.part" | sha256sum --check --status
    mv "$model.part" "$model"
fi
echo "$sum  $model" | sha256sum --check --status
if [[ ! -e llama.tgz ]]; then
    curl -fL --retry 2 https://github.com/ggml-org/llama.cpp/releases/download/b12608/llama-b12608-bin-ubuntu-x64.tar.gz -o llama.tgz
fi
echo '437a78088609f8faac6eddb8654614a0bafd761d3e9803b304c1b623074f599c  llama.tgz' | sha256sum --check --status
tar xzf llama.tgz
exec llama-b12608/llama-server --host 127.0.0.1 --port 8135 -m "$model" --alias purple-qwen3-8b -c 2048 -ngl 0 -t 2 -np 1
