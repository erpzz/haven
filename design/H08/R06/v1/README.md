# Haven / PROJECT ASTRA — R06 RF spatial research handback

Version 1.0 · 2026-09-28 UTC · **DESIGN_PROPOSAL**

Start with the [one-page integration summary](design/H08/INTEGRATION_SUMMARY.md), then the [specialist handback](design/H08/R06_HANDOFF.md), which follows the supplied starter's actual `agents/HANDOFF_TEMPLATE.md`.

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](design/H08/ARCHITECTURE.md) | Decisions, measurement/carrier comparison, maturity, frames/calibration, active perception, hardware gates and failure behavior |
| [CONTRACT_PROPOSALS.md](design/H08/CONTRACT_PROPOSALS.md) | Typed record boundaries, shared contract gaps, exact semantics and five change requests |
| [EXPERIMENTS.md](design/H08/EXPERIMENTS.md) | Smallest synthetic experiment through ambitious controlled reconstruction; held-out evaluation and stop rules |
| [EVIDENCE_REGISTER.md](design/H08/EVIDENCE_REGISTER.md) | 22 primary-source findings, versions, access limits and applicability |
| [INTEGRATION_AND_PACKAGES.md](design/H08/INTEGRATION_AND_PACKAGES.md) | Cross-branch mappings, all RF requirements and future coding packages |
| [INPUT_AUDIT.json](design/H08/INPUT_AUDIT.json) | Input archive and per-file hashes, required-read coverage and unchanged-starter verification |
| [VALIDATION.md](design/H08/VALIDATION.md) / [VALIDATION.json](design/H08/VALIDATION.json) | Documentation-only checks and explicit non-executed capability status |
| [MANIFEST.sha256](MANIFEST.sha256) | Integrity hashes for this delivery, excluding the manifest itself |

This archive is an additive documentation handback, not a replacement starter repository or an implementation patch. All proposed project artifacts live under `design/H08/`; README and manifest are delivery wrappers. Import/reconcile through H00 without overwriting unrelated work. Source papers/software/data are linked, not redistributed.

No hardware purchase, physical sensing, native test, benchmark, coding package, extra agent or M0 modification was performed. Every RF acceptance test and future experiment remains **NOT_EXECUTED**. Stop at review.
