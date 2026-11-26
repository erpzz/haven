#!/usr/bin/env bash
# One command for the sample lab. Run from the lab directory: ./ops/lab.sh up|scan|status|down
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
export APM_STATE=${APM_STATE:-"$HOME/.local/state/purple-copilot-apm"}
cli() { XDG_CONFIG_HOME="$APM_STATE/xdg" "$APM_STATE/bloodhound-cli" "$@"; }
password() { cli config get default_password 2>/dev/null | awk '/DEFAULT_PASSWORD/ {print $2}'; }
running() { docker ps --filter label=com.docker.compose.project=purple-apm --filter status=running -q | grep -q .; }
ready() {
    for _ in $(seq 1 120); do
        curl -fs -o /dev/null http://127.0.0.1:8080/ui/login && return 0
        sleep 5
    done
    echo "CE did not become ready on 127.0.0.1:8080" >&2; return 1
}
scan() {
    local rc=0
    python3 -m apm.collect || rc=$?
    python3 -m apm.path_history || rc=$?
    python3 -m apm.tier_zero || rc=$?
    # Exit 2 records a collection-quality warning after snapshots were committed (expected for the AD sample).
    [[ $rc -le 2 ]] || return $rc
}
need_docker() { docker info >/dev/null 2>&1 || { echo "Docker Engine is not running or not accessible" >&2; exit 1; }; }
case "${1:-}" in
    up)
        need_docker
        ./ops/fetch.sh
        if ! running; then
            if [[ -s "$APM_STATE/xdg/bloodhound/bloodhound.config.json" ]]; then ./ops/ce.sh up; else ./ops/ce.sh install; fi
        fi
        ready
        APM_SETUP_PASSWORD=$(password); export APM_SETUP_PASSWORD
        [[ -n "$APM_SETUP_PASSWORD" ]] || { echo "Could not read the generated CE password" >&2; exit 1; }
        [[ -f "$APM_STATE/ingest.json" ]] && grep -q '"phase": "terminal"' "$APM_STATE/ingest.json" || python3 -m apm.setup ingest
        [[ -f "$APM_STATE/reader.json" ]] || python3 -m apm.setup reader
        unset APM_SETUP_PASSWORD
        scan
        echo "Lab ready. Dashboard: python3 -m apm.dashboard, then open http://127.0.0.1:8134/tier-zero"
        echo "CE admin password (local only): XDG_CONFIG_HOME=\"$APM_STATE/xdg\" \"$APM_STATE/bloodhound-cli\" config get default_password" ;;
    scan) scan ;;
    status)
        running && echo "CE running on 127.0.0.1:8080" || echo "CE stopped"
        python3 - <<'PY'
import json
from apm import review
for platform in review.PLATFORMS:
    o = review.overview(platform)
    if o.get("available"):
        print(f"{platform}: snapshot {o['snapshot']} {o['principals_with_direct_control']} principals, "
              f"{o['control_edges']} control edges, {o['identities_able_to_reach_tier_zero']} identities exposed")
    else:
        print(f"{platform}: {o.get('reason')}")
PY
        ;;
    down) ./ops/ce.sh down ;;
    *) echo "Usage: ops/lab.sh up|scan|status|down" >&2; exit 2 ;;
esac
