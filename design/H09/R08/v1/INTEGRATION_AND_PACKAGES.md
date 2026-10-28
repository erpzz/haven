# R08 — integration, retained coverage and future packages

**Design only. No package has started; no owner permission is inferred from this plan.**

## Branch interfaces

- **H02 / R02 intelligence:** R08 sends bounded RA05/RA06 requests, declared resources and outcomes; H02 owns JobSpec, model eligibility, cancellation and budgets. Reuse N1/N2 and resolve reviewed R1 before reusable workers. No second coordinator.
- **H04 / R03 privacy and authority:** R08 sends subject/purpose/audience and fabrication/publication proposals; H04 owns authenticated principals, grant revisions and revocation/publication ordering. Household agreement, cloud sharing and machine permission are separate.
- **H08/H05 / R06–R07 spatial and sensors:** R08 returns measured specimen geometry, calibration history and transform uncertainty; H08/H05 owns sensor requirements, sensing keep-outs, frames and sensor-quality observations. Mechanical improvement does not imply sensing improvement.
- **H06 / R13 validation:** R08 supplies locked protocols, complete failures, raw evidence and qualification proposals; H06 owns protected evaluation and independent acceptance.
- **H10 / R09 robotics:** R08 may later supply cooled specimen identity and logical handling requests; H10 owns movement, resource leases and stop behavior. No hot-work automation.
- **H05 / R10 aircraft:** initial drone-related fabrication stays ground-side. Flight-mounted accessories require separate vehicle-specific consequence and qualification review.
- **H12 / R12 research:** reconcile R08 local source aliases with the canonical source registry without overwriting existing IDs.

## Retained engineering requirements

R08 retains REQ-ENG-01–10 and AT-ENG-01–10. The v1 handback specializes them with:
- no printer assumed and a purchase/workspace gate;
- editable source, parameter, drawing, BOM and specimen lineage;
- independent measurements with units, calibration, timestamps and uncertainty;
- separate proposal, fabrication, measurement and acceptance authority;
- bounded candidate/print/time/material/spend limits;
- unknown physical outcomes that are never automatically replayed;
- supervised manual-first fabrication;
- explicit exclusion of hazardous, medical and flight-critical qualification claims.

All other cumulative Haven branches remain retained. Absence from this short map is not deletion.

## Proposed package sequence

**R08-P00 — reconciliation only.** Compare the actual approved N2/R1 evidence with CR-R08-01–05 and R08-T01–20. Produce the exact evidence crosswalk, owner decisions, minimal inert provenance delta and measured-input checklist. No execution.

**R08-P01 — inert provenance/measurement delta.** Only after P00 approval, implement uncovered nonphysical record/validation behavior in the approved lab. Preserve frozen synthetic gates. No CAD or device adapter.

**R08-P02 — offline CAD preparation qualification.** Separately approve one pinned CadQuery/OpenSCAD path, deterministic checks, export round-trip tests and containment. No printer connection.

**R08-P03 — supervised fixture campaign.** Only after H04/H06/H08/H09 approve the actual sensor, metrology, thresholds, workspace and fabrication process. Manual transfer/start is acceptable; no gateway required.

**R08-P04 — optional read-only device telemetry.** Only for an identified owned/authorized machine after its API and state semantics are qualified.

**R08-P05 — optional narrow fabrication gateway.** Exact sealed job, local single-use start authorization, present operator, no toggle semantics, no automatic retry/resume, and explicit unknown-outcome reconciliation.

**R08-P06 — later cooled-object robot handling.** H10-qualified inert-object movement between known nests after human-mediated measurement works. No hot-bed access or automatic reprint.

Each package ends at review and does not automatically launch the next.

## Documentation versus implementation

The following remain documentation-only until separately authorized: software/version selection, generated CAD execution, model use, cloud inference, slicer execution, printer APIs, purchases, physical measurements, robot actions, FEA and all physical qualification.

Presence of this design on `main` is not implementation authorization or capability acceptance.
