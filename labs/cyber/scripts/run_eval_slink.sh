#!/bin/bash
# Runs the A/B/C evaluation against the local Qwythos llama-server (port 8095): thinking off, then thinking on.
# Thinking on is ~4 min/row on the 2070S, so the 20 held-out scenarios (the decision set) run before the 35 dev ones.
# Sequential on purpose: one server slot, so runs never contend. Resumable: re-running skips finished rows.
set -u
cd "$(dirname "$0")/.."
EP=${EP:-http://127.0.0.1:8095/v1}
M=${M:-qwythos-9b-v2-q4km}
python3 -m haven_cyber.eval.harness --endpoint "$EP" --model "$M" --conditions A,B,C --out runs/eval/qwythos-nothink-v1
python3 -m haven_cyber.eval.harness --endpoint "$EP" --model "$M" --think --conditions A,B,C --split heldout --out runs/eval/qwythos-think-v1
python3 -m haven_cyber.eval.harness --endpoint "$EP" --model "$M" --think --conditions A,B,C --split dev --out runs/eval/qwythos-think-v1
