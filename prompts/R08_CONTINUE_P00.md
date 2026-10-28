# R08 continuation — P00 reconciliation

Continue the existing R08 / H09 engineering-and-fabrication thread. Do **not** repeat the broad R08 literature survey and do not implement physical capability.

## Required repository context

Record the exact `main` commit read. Read:

- `START_HERE.md`, `PRECEDENCE.md`, `CURRENT_STATUS.md`
- `coordination/PROTOCOL.md`, `coordination/THREAD_STATUS.md`
- `design/H09/R08/v1/README.md`
- `design/H09/R08/v1/R08_HANDOFF.md`
- `design/H09/R08/v1/INTERFACES_AND_CONTRACTS.md`
- `design/H09/R08/v1/EXPERIMENTS_AND_ACCEPTANCE.md`
- the preserved NIGHT-01/N2 evidence and the latest accepted R1 evidence, if any
- relevant R02/H02, R03/H04, R06/H08 and R13/H06 decisions actually present in the repo

Issue: #5.

## Assignment

Produce **R08-P00 only**: reconcile the actual current N2 implementation/evidence with CR-R08-01 through CR-R08-05 and with the latest shared owner decisions.

For each proposed R08-T case and each affected existing test, classify evidence as:
`COVERED_BY_EQUIVALENT_EVIDENCE`, `PARTIALLY_COVERED`, `NEW_GAP`, `NEEDS_OWNER_DECISION`, or `NOT_IN_THIS_SLICE`.

Return:
1. exact case-to-test/evidence crosswalk;
2. accept/amend/defer recommendation for CR-R08-01–05, naming required owners;
3. minimal inert provenance/measurement delta that would be worth coding next;
4. required measured inputs for the first sensor-fixture campaign;
5. explicit separate gates for CAD preparation, supervised physical fabrication, and any later device gateway;
6. unresolved questions to H04, H06, H08/H05, H02 and H10 as applicable.

Write a new versioned packet under `design/H09/R08/reconciliation-v1/` on a dedicated branch and open a PR. Preserve R08 v1 unchanged.

## Hard boundaries

No M0 edits. No printer/robot/device connection. No CAD/slicer execution. No arbitrary generated Python. No model download or hosted call. No purchase. No unattended heating/printing. No safety-limit edits. No automatic next package.

Do not treat the 20% and 30% illustrative thresholds found in different research artifacts as interchangeable or approved for unidentified hardware. Do not choose a printer merely to fill a BOM. Do not reinterpret synthetic arithmetic as physics. A second LLM is not independent engineering acceptance. Unknown physical outcomes are not retried automatically.

Stop after the P00 handback/PR and wait for integration review.
