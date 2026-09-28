# Start here — one cumulative project, separate workspaces

## For Eric

Keep the current Codex M0 thread running. This package is the comprehensive context for a **new lead integration/design agent**. It does not contain that thread's latest application code. Ask the new agent to inspect the actual workspace read-only only after you identify it and permit that read.

Save the ZIP and extract it into a fresh folder. The archive has exactly one top-level directory, `haven-astra-starter`. Select the directory that directly contains this file and `AGENTS.md`, not its parent and not the ZIP. The optional PowerShell helper supplied alongside the ZIP prints the exact Windows path. It only extracts/checks a new folder; it performs no host installation or networking change.

For future Linux-side engineering, a suitable separate location is `~/projects/haven-astra-starter`. This is a proposed documentation workspace, **not** the existing `~/projects/project-astra` application. Preserve the original archive. Inspect a destination before copying; never overwrite prior work silently.

## First message for the new agent

Use the full `CODEX_START_PROMPT.md`. The first authorized work package is `I00` in `workstreams/I00_RECONCILE_AND_PLAN.md`: read, verify coverage, identify actual M0 state if available, resolve ownership, and return a concrete integration plan plus proposed first parallel task. No device code, installation, account connection, purchase, network exposure or physical experiment is authorized by this first assignment.

If the user later explicitly approves a bounded implementation work package, code that package in an isolated branch/worktree and return evidence. Do not spend forever replanning, but do not treat a large backlog as a blanket permission to implement everything.

## Read in layers

**Orientation:** CURRENT_STATUS, PRECEDENCE, scope/COVERAGE and docs/00_CHARTER.

**Shared vocabulary:** docs/01_SYSTEM_ARCHITECTURE, contracts/README, docs/03_PRIVACY_AND_AUTHORITY, docs/13_RUNTIME_AGENTS.

**Assigned specialist:** its charter, owned design chapter, relevant baseline sections, source cards and experiment/test IDs. Specialists do not need unrelated personal context or raw partner data.

**Integration:** agents/THREAD_MAP, decisions/DECISIONS, roadmap/ROADMAP, tests/ACCEPTANCE_CATALOG.

## What the new agent must return first

A complete coverage check; actual input paths and hashes; status as reported versus observed; conflicts with the existing M0 contract; no more than three parallel work packages with disjoint ownership; shared contract revisions requiring review; stop conditions; and the next decision for Eric. An agent may not certify that another chat completed a task merely because a plan said it would.

## Reading the family guide

`family/HAVEN_IN_PLAIN_ENGLISH.pdf` is a short shareable explanation, not a technical feasibility report. It describes the ambition and distinguishes early usefulness from experimental future capability. The complete technical record remains in this repository.
