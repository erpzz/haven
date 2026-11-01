#!/usr/bin/env bash
# Install the Haven operator surface into Hermes from a commit (never from a worktree path).
#
#   labs/hermes/scripts/install.sh [COMMIT] [--observe] [--no-strata] [--dry-run]
#
# 1. Exports labs/{hermes,engineer,cyber} at COMMIT to ~/.local/share/haven-hermes/releases/<sha> and
#    points ~/.local/share/haven-hermes/current at it (rollback: repoint the symlink, or install an older sha).
# 2. Runs the offline smoke test from the release.
# 3. Backs up ~/.hermes/config.yaml, then through `hermes config set`:
#      mcp_servers.haven        stdio server, trust: untrusted (the owner approves every change)
#      mcp_servers.haven-cyber  PYTHONPATH moved from the PR worktree to the release
#      platform_toolsets.cli    + mcp-haven, mcp-haven-cyber
# 4. Copies the haven-operator skill to ~/.hermes/skills/devops/.
set -euo pipefail

REPO=${HAVEN_REPO:-$HOME/.local/share/haven-git/haven}
DEST=${HAVEN_HERMES_HOME:-$HOME/.local/share/haven-hermes}
COMMIT=HEAD MODE=operate STRATA=--allow-strata DRY=0
for a in "$@"; do
  case $a in
    --observe) MODE=observe ;;
    --no-strata) STRATA= ;;
    --dry-run) DRY=1 ;;
    -*) echo "unknown option $a" >&2; exit 2 ;;
    *) COMMIT=$a ;;
  esac
done

PY=$(command -v python3)
SHA=$(git -C "$REPO" rev-parse --short=12 "$COMMIT^{commit}")
REL="$DEST/releases/$SHA"
run() { if [ "$DRY" = 1 ]; then printf 'would run:'; printf ' %q' "$@"; echo; else "$@"; fi; }

if [ ! -d "$REL/labs/hermes" ]; then
  run mkdir -p "$REL"
  if [ "$DRY" = 1 ]; then echo "would export $SHA labs/{hermes,engineer,cyber} to $REL"
  else git -C "$REPO" archive "$SHA" labs/hermes labs/engineer labs/cyber | tar -x -C "$REL"; fi
fi
if [ "$DRY" = 0 ]; then
  (cd "$REL/labs/hermes" && "$PY" scripts/smoke.py >/dev/null) || { echo "smoke test failed in $REL; nothing installed" >&2; exit 1; }
fi
run ln -sfn "releases/$SHA" "$DEST/current"
CUR="$DEST/current/labs"

CFG=$(hermes config path)
run cp "$CFG" "$CFG.bak-haven-$(date +%Y%m%dT%H%M%S)"

STRATA_ARG=${STRATA:+, \"$STRATA\"}
HAVEN_JSON=$(cat <<EOF
{"command": "$PY", "args": ["-m", "haven_hermes.server", "--mode", "$MODE"$STRATA_ARG],
 "env": {"PYTHONPATH": "$CUR/hermes"}, "trust": "untrusted", "timeout": 120, "enabled": true}
EOF
)
run hermes config set mcp_servers.haven "$HAVEN_JSON"
if hermes config get mcp_servers.haven-cyber >/dev/null 2>&1; then
  run hermes config set mcp_servers.haven-cyber.env.PYTHONPATH "$CUR/cyber"
fi

TOOLSETS=$(hermes config get platform_toolsets.cli 2>/dev/null | "$PY" -c '
import sys
have = [l.strip()[2:].strip() for l in sys.stdin if l.strip().startswith("- ")]
for t in ("mcp-haven", "mcp-haven-cyber"):
    if t not in have:
        have.append(t)
print("[" + ", ".join(f"\"{t}\"" for t in have) + "]")')
run hermes config set platform_toolsets.cli "$TOOLSETS"

SKILLS="$HOME/.hermes/skills/devops/haven-operator"
run mkdir -p "$SKILLS"
run cp "$REL/labs/hermes/skill/haven-operator/SKILL.md" "$SKILLS/SKILL.md"

echo "installed $SHA (mode $MODE${STRATA:+, strata allowed}); verify with: hermes mcp test haven"
