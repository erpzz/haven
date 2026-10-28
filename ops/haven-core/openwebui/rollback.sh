#!/bin/sh
# Stop Haven's Open WebUI frontend and revoke its gateway key. Chats and accounts stay in
# ~/.local/share/haven-openwebui/data* so a later install.sh resumes them.
#   sh ops/haven-core/openwebui/rollback.sh            # production instance
#   HAVEN_OWUI_INSTANCE=test sh ops/haven-core/openwebui/rollback.sh
set -eu
INSTANCE=${HAVEN_OWUI_INSTANCE:-prod}
LAB_DATA=${HAVEN_LAB_DATA:-$HOME/.local/share/haven-model-lab}
UNIT=haven-openwebui.service; PRINCIPAL=open-webui
if [ "$INSTANCE" != prod ]; then UNIT=haven-openwebui-$INSTANCE.service; PRINCIPAL=open-webui-$INSTANCE; fi
systemctl --user disable --now "$UNIT" 2>/dev/null || true
python3 - "$LAB_DATA/gateway-keys.json" "$PRINCIPAL" <<'EOF'
import json, os, sys
path, principal = sys.argv[1], sys.argv[2]
if os.path.exists(path):
    rows = json.load(open(path)).get('keys', [])
    kept = [r for r in rows if r.get('principal') != principal]
    fd = os.open(path + '.tmp', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump({'keys': kept}, f, indent=1)
    os.replace(path + '.tmp', path)
    print(f'Revoked {len(rows) - len(kept)} gateway key(s) for {principal}.')
EOF
echo "$UNIT stopped and disabled. The Model Lab keeps running."
