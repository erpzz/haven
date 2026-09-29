# Haven IP-01 local assistant

A local development application for two invented people. Notes, sharing, source-linked answers, drafts and tasks use persistent SQLite state. The demo selector represents simulated login. It is not household enrollment or protection from a host administrator.

This directory is the runnable application. Campaign reports and independent findings are in [`../../campaigns/IP-01/ip01-v2-20260929`](../../campaigns/IP-01/ip01-v2-20260929/). The application and evidence are under active implementation; the final MORNING_REPORT will state exactly which journeys were executed and which remain unqualified.

## Prepare on Windows with Python 3.12

From this repository root in PowerShell:

```powershell
New-Item -ItemType Directory -Force .ip01-runtime/tmp, .ip01-runtime/cache/pip | Out-Null
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.ip01-runtime/cache/pip'
$env:TEMP = Join-Path (Get-Location) '.ip01-runtime/tmp'
$env:TMP = $env:TEMP
python -m venv .ip01-runtime/venv
& ./.ip01-runtime/venv/Scripts/python.exe -m pip install --only-binary=:all: --require-hashes -r labs/ip01/requirements.lock
& ./.ip01-runtime/venv/Scripts/python.exe -m pip check
```

The lock records actual Windows CPython 3.12 wheels, including all resolved transitive dependencies. Another platform needs an explicitly reviewed lock. There is no elevated install, persistent service, hosted provider or database outside the isolated runtime.

## Start, inspect and stop

```powershell
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py start
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py status
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py stop
```

`start` prints the exact URL, using the first free loopback port from **8765–8767**. Open that URL in a browser. It binds only `127.0.0.1`, runs one Uvicorn worker and does not restart after a crash. `stop` requests graceful shutdown for the recorded process instance and reports observations. An `UNKNOWN` stop is a reason to inspect the recorded identity and logs; it is not permission to kill unrelated processes. The dedicated model backend has a separate ownership/stop record.

For a time-bounded run, append `--deadline` with a future UTC timestamp to `start`. The campaign itself uses its fixed original deadline; restarting does not renew it. A second `start` against a live owned identity returns its existing URL. Logs, process receipts, database, images, caches and model assets stay under `.ip01-runtime/` and must never be committed.

## What the interface means

- Select demo Person A or B. Each browser session is separate; private notes must remain inaccessible to the other person until an eligible explicit share.
- Notes have immutable revisions. Editing, withdrawing a share or tombstoning an influencing note prevents stale new output.
- Deterministic answers are labeled as such. The model route stays unavailable until its exact local artifact and owned lifecycle gates are satisfied.
- A job status is separate from whether computation has stopped and whether an answer may be released. A cancel request is not proof of termination.
- A fresh output consumption can return the answer once. Repeating consumption returns receipt history; a reload does not silently replay a consumed answer. A new answer is a new operation with current eligibility and quota checks.
- A saved draft or task is local state. This app does not send a message, schedule an external action or operate a device.
- A delivery report records what the browser reported. It cannot prove a person perceived the answer, recall already displayed bytes or turn a missing acknowledgment into “not sent.”

The [public walkthrough notes](fixtures/demo-notes.json) provide invented content to enter in the interface. They are separate from the evaluator's pilot assets. Create the notes as A, keep one private, and explicitly share the materials note with B if you want to explore a one-use grant. Choose a future expiry when sharing.

## Browser test runtime

The independent test setup uses Playwright's official Chromium distribution in the campaign cache:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.ip01-runtime/cache/ms-playwright'
& ./.ip01-runtime/venv/Scripts/python.exe -m playwright install chromium
```

Final test commands, candidate hashes, observed outcomes and retained failures will be bound in the campaign handoff. Development tests and the model pilot do not establish canonical CORE/MF/P03/VA-01, real authentication, OS isolation or physical qualification.

The local model has a separate, expiring campaign gate and a finite call ledger. Restarting the app does not reset that ledger or extend the campaign. After the gate expires, the deterministic application remains usable; a later model evaluation requires a new explicit bounded authorization. The preparation script can inspect/download the single permitted artifact, but it never authorizes inference by itself.

## Database migrations and continuity

The application applies its versioned SQLite migrations in [haven/store.py](haven/store.py) when it starts. Version 1 creates the JSON record tables, immutable-history triggers and unique release/consume/grant-claim indexes; version 2 adds the unique model-allocation index. An unknown schema or an existing unversioned database is preserved and refused.

The database, WAL files and separate continuity record are private runtime state. A current restart invalidates old sessions and fences old jobs and permits. Missing or mismatched continuity enters a fresh epoch in review-only mode. There is no public command to clear that state or replay old output.

## Run the producer regression tests

These tests use synthetic state and owned benign processes. They do not execute the local model or start the final pilot. Run them from the repository root:

```powershell
$ip01TestRun = Join-Path (Get-Location) ('.ip01-runtime/manual-tests/' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force $ip01TestRun | Out-Null
$env:PYTHONPATH = Join-Path (Get-Location) 'labs/ip01'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:TEMP = $ip01TestRun
$env:TMP = $ip01TestRun
$env:HYPOTHESIS_STORAGE_DIRECTORY = Join-Path $ip01TestRun 'hypothesis'
& ./.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/app labs/ip01/tests/runtime -q --basetemp "$ip01TestRun/tmp" -o "cache_dir=$ip01TestRun/pytest-cache"
```

Retain the exit status and output for the source revision you tested. Producer checks, independently executed QA, and the final pilot are reported separately in the campaign; rerunning this command cannot transfer an earlier verdict to changed code.

## Source and scope

Implementation is confined to `labs/ip01/`; coordination and review to the IP-01 campaign. The accepted R03/P01 composites define influence closure, four output records, once-only finite grant accounting and restore semantics. The original ASTRA store's transaction/receipt patterns were inspected from its clean pinned source; exact source and private-copy identities are recorded in the campaign. The new Windows supervisor is a laboratory implementation, not a repair or qualification of the original NIGHT-01/R1 workspace.

Broader speech/video, spatial/RF, wearables, engineering, robotics, aircraft and Observatory work remains retained in the research baseline and outside this implementation phase.
