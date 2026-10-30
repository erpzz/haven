#!/bin/sh
# Install or update Haven's Open WebUI frontend on Slink. Idempotent; never prints secrets.
#   sh ops/haven-core/openwebui/install.sh          # production instance, 127.0.0.1:8878
#   HAVEN_OWUI_INSTANCE=test HAVEN_OWUI_PORT=8879 sh ops/haven-core/openwebui/install.sh
# Rollback: sh ops/haven-core/openwebui/rollback.sh (stops the frontend, revokes its key, keeps chats).
set -eu
REPO=$(cd "$(dirname "$0")/../../.." && pwd)
VERSION=0.12.5
# One venv per version, side by side: an upgrade never modifies the venv that is serving, and the
# previous one stays for rollback. 0.12.5 (2026-10-30) fixes the advisories haven-sentinel found in
# 0.11.4's pins (pillow 13.0.0, pypdf 6.21.2, aiohttp 3.14.5, brotli 1.2.1, mcp 2.3.0).
INSTANCE=${HAVEN_OWUI_INSTANCE:-prod}
PORT=${HAVEN_OWUI_PORT:-8878}
LAB_DATA=${HAVEN_LAB_DATA:-$HOME/.local/share/haven-model-lab}
BASE=$HOME/.local/share/haven-openwebui
UNIT=haven-openwebui.service
CONF=$HOME/.config/haven-openwebui
DATA=$BASE/data
PRINCIPAL=open-webui
if [ "$INSTANCE" != prod ]; then
  UNIT=haven-openwebui-$INSTANCE.service; CONF=$CONF-$INSTANCE; DATA=$BASE/data-$INSTANCE; PRINCIPAL=open-webui-$INSTANCE
fi
umask 077
mkdir -p "$BASE" "$CONF" "$DATA"

VENV=${HAVEN_OWUI_VENV:-$BASE/venv-$VERSION}
if ! "$VENV/bin/open-webui" --help >/dev/null 2>&1 || \
   [ "$("$VENV/bin/pip" show open-webui 2>/dev/null | sed -n 's/^Version: //p')" != "$VERSION" ]; then
  [ -x "$VENV/bin/pip" ] || python3 -m venv "$VENV"
  # CPU torch only: the frontend must never take GPU memory from the inference runtime.
  "$VENV/bin/pip" install --disable-pip-version-check \
    --extra-index-url https://download.pytorch.org/whl/cpu "open-webui==$VERSION"
fi

# The Lab gateway stores only digests; the plaintext key goes straight into the 0600 env file.
# Reuse a key that is still registered; issue a new one only when it was revoked or never existed
# (HAVEN_OWUI_ROTATE=1 forces rotation).
KEY=$(sed -n 's/^OPENAI_API_KEY=//p' "$CONF/env" 2>/dev/null || true)
if [ -z "$KEY" ] || [ "${HAVEN_OWUI_ROTATE:-0}" = 1 ] || ! python3 -c "
import hashlib, json, sys
rows = json.load(open(sys.argv[1])).get('keys', [])
sys.exit(0 if hashlib.sha256(sys.argv[2].encode()).hexdigest() in {r['sha256'] for r in rows} else 1)
" "$LAB_DATA/gateway-keys.json" "$KEY" 2>/dev/null; then
  KEY=$(cd "$REPO/labs/model-lab" && python3 -c "
import sys; from pathlib import Path; from gateway import Gateway
print(Gateway.issue_key(Path(sys.argv[1]), sys.argv[2], 'frontend'))" "$LAB_DATA" "$PRINCIPAL")
fi
JWT_FILE=$LAB_DATA/gateway-frontend-jwt.secret
[ -s "$JWT_FILE" ] || python3 -c "import secrets; print(secrets.token_urlsafe(48))" > "$JWT_FILE"
chmod 600 "$JWT_FILE" "$LAB_DATA/gateway-keys.json"
SESSION=$(sed -n 's/^WEBUI_SECRET_KEY=//p' "$CONF/env" 2>/dev/null || true)
[ -n "$SESSION" ] || SESSION=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

cat > "$CONF/env.new" <<EOF
DATA_DIR=$DATA
# Configuration as code: these settings, not values saved in the admin UI, apply at every start.
ENABLE_PERSISTENT_CONFIG=false
WEBUI_SECRET_KEY=$SESSION
WEBUI_NAME=Haven
OPENAI_API_BASE_URL=http://127.0.0.1:8877/v1
OPENAI_API_KEY=$KEY
ENABLE_OPENAI_API=true
ENABLE_OLLAMA_API=false
ENABLE_DIRECT_CONNECTIONS=false
ENABLE_FORWARD_USER_INFO_HEADERS=true
FORWARD_USER_INFO_HEADER_JWT_SECRET=$(cat "$JWT_FILE")
DEFAULT_USER_ROLE=pending
ENABLE_SIGNUP=true
ENABLE_COMMUNITY_SHARING=false
ENABLE_ADMIN_CHAT_ACCESS=false
ENABLE_WEB_SEARCH=false
ENABLE_TITLE_GENERATION=false
ENABLE_TAGS_GENERATION=false
ENABLE_FOLLOW_UP_GENERATION=false
ENABLE_AUTOCOMPLETE_GENERATION=false
ENABLE_SEARCH_QUERY_GENERATION=false
ENABLE_RETRIEVAL_QUERY_GENERATION=false
ENABLE_EVALUATION_ARENA_MODELS=false
# Scheduled prompts would start unattended inference on the one GPU slot; opt in deliberately.
ENABLE_AUTOMATIONS=false
# No embedding model is downloaded (offline): attached files go to the model as full text.
BYPASS_EMBEDDING_AND_RETRIEVAL=true
AIOHTTP_CLIENT_TIMEOUT=1800
OFFLINE_MODE=true
HF_HUB_OFFLINE=1
ENABLE_VERSION_UPDATE_CHECK=false
SCARF_NO_ANALYTICS=true
DO_NOT_TRACK=true
ANONYMIZED_TELEMETRY=false
EOF
mv "$CONF/env.new" "$CONF/env"

sed -e "s#%h/.config/haven-openwebui/env#$CONF/env#" -e "s#--port 8878#--port $PORT#" \
    -e "s#%h/.local/share/haven-openwebui/venv/#$VENV/#" \
    "$REPO/ops/haven-core/openwebui/haven-openwebui.service" > "$HOME/.config/systemd/user/$UNIT"
systemctl --user daemon-reload
systemctl --user enable "$UNIT" >/dev/null
systemctl --user restart "$UNIT"
echo "$UNIT -> http://127.0.0.1:$PORT (loopback). Gateway principal: $PRINCIPAL. Open WebUI $VERSION."
echo "From the Mac: ssh -N -L $PORT:127.0.0.1:$PORT haven   then open http://127.0.0.1:$PORT"
