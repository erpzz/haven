# R06 — one-page integration summary

**Haven / PROJECT ASTRA · H08 spatial research · 2026-09-28 · DESIGN_PROPOSAL**

**Decision:** accept a local, replay-first RF evidence module. Begin with honest motion/unknown states, then cooperative device localization, controlled geometry and separately evaluated semantics. Presence is a deliberate engineering bridge; stronger geometry may require different radios, apertures and algorithms. Haven remains the daily assistant for two independently consenting people, with all cumulative branches retained.

**Architecture:** a bounded acquisition adapter produces typed observations; admission checks source, clocks, calibration and current scope; deterministic/local processing produces framed estimates with provenance and uncertainty; R07 projects separate map layers. A selector ranks a finite set of permitted observations. Authenticated authority and domain executors alone authorize acquisition or movement. No generic shell, unconstrained radio control or model-granted permission.

**Interfaces:** preserve all starter v1 schemas. Propose `RFObservationBatch`, `FrameTransform`, `CalibrationRecord`, mandatory `SpatialSemantics`, `ObservationProposal` and `ObservationOutcome`. The spatial sidecar distinguishes unavailable, stale, ambiguous and revoked data; keeps support masks; and prevents legacy consumers from presenting incomplete semantics as current claims. H00 receives five explicit change requests covering spatial semantics, consent/data bindings, acquisition authority, runtime lifecycle and qualification. M0 has no changes or new dependencies.

**Evidence:** 22 primary-source records cover CSI/RSSI, RTT/UWB, radar, tomography/diffraction, mobile apertures, platform access and regulatory limits. IEEE 802.11bf is published; it does not itself supply a working consumer imaging API [R06-S01]. Recent RISE and GeRaF 2.0 work supports continued research while depending on specialized apparatus, priors and constrained evaluation [R06-S16, R06-S17]. No reviewed paper demonstrates a Haven capability.

**Hardware:** buy nothing now. Later choose one qualified fixed CSI configuration or one ranging/radar alternative after proving exact data access, permitted footprint, full BOM and independent test protocol. Phone/accessory, handheld, fixture, rover and drone paths remain distinct. Airborne UWB under the cited FCC subpart is blocked without an established alternative authorization [R06-S21]. No price or stock claim is made.

**Next package:** P0/E0, at most eight engineering hours, one CPU worker, 4 GiB RAM, 1 GiB artifacts, $0 new spend. Use 60 synthetic episodes with protected tests to compare fixed, random and deterministic adaptive selection. Required outcome: zero unauthorized selections, fabricated positions, false freshness or post-revocation disclosure. Success proves replay integrity only. Dataset rights/version issues keep the first measured-CSI experiment conditional.

**Later ambitious experiment:** E4 compares controlled multi-view edge/surface reconstruction against independent metrology and hidden test configurations. Evaluate false geometry, uncertainty coverage and acquisition cost; promote adaptive scanning only if it saves measurements at matched quality. Generated completion stays visibly separate from measurement-supported reconstruction. No physical trial is authorized here.

**Integration and stop:** R07 consumes estimates; H04 owns consent; H09 provides measured fixtures; H10/H05 own movement; H02 budgets jobs; H06 independently reviews evidence. Every RF acceptance test remains **NOT_EXECUTED**. Sources and protocols are linked in [R06_HANDOFF.md](R06_HANDOFF.md). Stop at review; do not begin implementation automatically.
