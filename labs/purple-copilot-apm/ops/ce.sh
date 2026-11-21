#!/usr/bin/env bash
set -euo pipefail
umask 077
unset DOCKER_CONTEXT DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH
export DOCKER_HOST=unix:///var/run/docker.sock
state=${APM_STATE:-"$HOME/.local/state/purple-copilot-apm"}
export COMPOSE_PROJECT_NAME=purple-apm XDG_CONFIG_HOME="$state/xdg"
export BH_CONFIG="$XDG_CONFIG_HOME/bloodhound/bloodhound.config.json"
if [[ ! -e "$state/pgsecret" ]]; then
    python3 -c 'import secrets,sys; open(sys.argv[1],"x").write(secrets.token_hex(32))' "$state/pgsecret"
fi
export POSTGRES_PASSWORD
POSTGRES_PASSWORD=$(cat "$state/pgsecret")
compose=$(realpath "$(dirname "$0")/compose.yaml")
case "${1:-}" in
    install)
        "$state/bloodhound-cli" pg
        "$state/bloodhound-cli" -f "$compose" install ;;
    up) docker compose -f "$compose" up -d ;;
    down) docker compose -f "$compose" down ;;
    *) echo 'Usage: ce.sh install|up|down' >&2; exit 2 ;;
esac
