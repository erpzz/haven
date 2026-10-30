#!/usr/bin/env bash
# Weekly fresh evaluation set: security fixes published since the previous fresh build, never harvested,
# from repositories outside training. Nothing here trains anything; outputs stay in the private state dir.
#   fresh_weekly.sh            # build (downloads the public OSV PyPI export; fetches fix commits)
# Rollback: systemctl --user disable --now haven-secpatch-fresh.timer
set -euo pipefail
S=${SECPATCH_STATE:-$HOME/.local/state/haven-secpatch}
CODE=$(cd "$(dirname "$0")" && pwd)
BANDIT=${SECPATCH_BANDIT:-$HOME/.local/share/haven-secpatch-venv/bin/bandit}
stamp=$(date -u +%Y%m%d)
archive=$S/raw/pypi-all-$stamp.zip
if [ ! -s "$archive" ]; then
  curl -fsS --max-time 900 -o "$archive.part" https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip
  python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).testzip()" "$archive.part"
  mv "$archive.part" "$archive"
fi
# since = the day of the newest fresh build (fresh.py also drops anything already seen)
last=$(ls -1 "$S"/fresh/manifest-fresh-*.json 2>/dev/null | sort | tail -1 || true)
if [ -n "$last" ]; then
  since=$(python3 -c "import json,sys; b=json.load(open(sys.argv[1]))['built_at']; print(f'{b[:4]}-{b[4:6]}-{b[6:8]}')" "$last")
else
  since=$(date -u -d '7 days ago' +%Y-%m-%d)
fi
seen=("$S/candidates.jsonl")
for f in "$S"/fresh/harvest-fresh-*.jsonl; do [ -e "$f" ] && seen+=("$f"); done
python3 "$CODE/fresh.py" --archive "$archive" --since "$since" --seen "${seen[@]}" \
  --train "$S/data-v2/train.jsonl" --work "$S/git-fresh" --out "$S/fresh" --bandit "$BANDIT"
