# R09-P0 — Small inert skill-evidence replay

Status: **AUTHORIZATION_REQUIRED; NOT_STARTED; no operational grant.**

Proposed implementation owner H10; H00 reviews authority/ordering, H08/MM-VISION review evidence profile, H09 reviews qualification exclusions; H06 is a distinct evaluator/reviewer. Supervisor chooses a separate branch/workspace and exact application paths after authorization. Candidate file set within a new isolated package: `robotics_mock/contracts`, `robotics_mock/state_machine`, `robotics_mock/fixtures`, `robotics_mock/replay`, `robotics_mock/tests`, README and manifest. These are proposals, not files created by this research task.

## Concrete deliverable

A standard-library-only mock consumes synthetic SkillIntent and evidence records, displays six separate observation/interpretation/intent/dispatch/outcome/recovery states, and emits an append-only replay report with reasons and full record identities. It handles useful positive cases and all 24 E09-A fixtures. The adapter has no network, serial, USB, ROS, camera, subprocess, arbitrary file-path, package-loader or model hook. Mock domain admission can create only mock dispatch records. Physical-profile inputs explicitly reject even if otherwise structurally valid.

Prefer integration with existing simple application storage/contracts if the actual baseline is available; no broker/vector database is required. Current application's source and tests were not inspected or run in R09, so interface fit is CODE_NOT_VERIFIED, not claimed complete. If source is unavailable, implement a standalone inert fixture validator only and mark application integration CODE_NOT_AVAILABLE. Do not silently build a generic executor.

## Before implementation freeze

1. Owner accepts exact R09 contract/profile version after independent documentary review, and maps it to CORE I01–I07 without shortening AuthorityVector or merging output records.
2. Pin accepted CORE/R07/R08-P00/MM-VISION inputs and their limitations. R08 one-axis result cannot populate full pose or physical evidence; its E01 methods gate remains on E01, not a reason to hold the no-worker mock indefinitely.
3. H06 freezes all 24 fixture identities, development/protected assignment and independent oracle; retain unchanged original REQ/AT/EX records. A developer cannot edit its evaluator or make aggregate success excuse an authority escape.
4. Approve package scope, isolated output path, runtime and resource bounds. No hardware, models, packages, accounts, private data or paid calls. R1/P01 containment gates are prerequisites before any later inference-worker package, not evidence supplied by this mock.

## Proposed caps and stop conditions

3 hours implementation plus 1 hour independent review; single 5-minute replay run; one CPU process;256 MiB fixture ceiling;50 MiB output ceiling; zero new spending, device calls, downloads or external traffic. These are requested ceilings, not executed measurements or a promise the host meets them. Stop on unexpected egress/device access, inability to isolate physical profiles, unbounded work, missing authority dependencies or evaluator disagreement. Preserve output and residual unknowns rather than automatically retrying.

## Completion and promotion

Require24/24 correct frozen outcomes, all useful positive cases succeed, zero false admissions/duplicate sends/premature exclusion releases, and all four evaluator mutations are detected. Verify record digests and source/unit/clock/frame identity, all failed attempts and reasons. Distinct H06 reviewer returns PASS/FAIL/INCONCLUSIVE tied to exact implementation/evaluator/input hashes. This would qualify only the inert contract slice. No physical skill, model accuracy, real-time recovery, hosted cancellation, metrology, camera, robot safety or original AT completion can be claimed from it.

Next gates are independently chosen: simulation study E09-B; rights/resource-pinned ACT comparison; or an apparatus qualification package before EX26. No purchase, training run, teleoperation, unattended dispatch or human augmentation starts automatically. A successful kit-carrier demonstration never replaces independent urgent-help communications.

