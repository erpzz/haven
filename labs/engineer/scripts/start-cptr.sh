#!/bin/zsh
# Start Open WebUI Computer for Haven: loopback only, isolated data dir, the personal Claude
# profile, OpenCode on PATH, and no automatic edits to workspace .gitignore files.
set -eu
W=${HAVEN_CPTR_HOME:-$HOME/.local/share/haven-workspace}
PORT=${HAVEN_CPTR_PORT:-8896}
export CPTR_DATA_DIR=$W/cptr-data CPTR_AUDIT_LOG_LEVEL=METADATA CPTR_AUTO_GITIGNORE_DOT_CPTR=false
export CLAUDE_CONFIG_DIR=${HAVEN_CLAUDE_CONFIG_DIR:-$HOME/.config/claude-haven-personal}
export PATH="$W/opencode-prefix/node_modules/.bin:/opt/homebrew/bin:$PATH"
unset ANTHROPIC_API_KEY OPENAI_API_KEY 2>/dev/null || true
mkdir -p "$CPTR_DATA_DIR" && chmod 700 "$CPTR_DATA_DIR"
nohup "$W/cptr-venv/bin/cptr" run --host 127.0.0.1 --port "$PORT" --headless > "$W/cptr.log" 2>&1 &
echo "cptr starting on http://127.0.0.1:$PORT (log: $W/cptr.log; first-run setup link is printed there)"
