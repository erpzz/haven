# R08 — primary-source register and evidence limitations

**Research/access date: 2026-09-28.** Sources below support external facts, not Haven capability. Recommendations and numerical trial thresholds are this handback's proposals. Rolling documentation is not an installation pin. No source's code, model, dataset, printer or experimental apparatus was executed or acquired here.

S01–S20 are **local R08 source aliases**. Existing canonical IDs are noted where applicable; H12 must reconcile additions rather than overwrite the cumulative registry.

## Tooling and interfaces

**S01 — CadQuery introduction.** Primary project documentation, checked 2026-09-28: https://cadquery.readthedocs.io/en/latest/intro.html . Script-based parametric CAD using the OpenCASCADE ecosystem. Supports a template-first recommendation; does not establish local installation, containment or part validity. Canonical starter link: R17.

**S02 — CadQuery importing/exporting.** Primary project documentation, checked 2026-09-28: https://cadquery.readthedocs.io/en/latest/importexport.html . Documents STEP, STL, 3MF and other exchanges, and distinguishes the Python parametric source from non-parametric exported exchange data. No local round-trip test or printer compatibility is claimed.

**S03 — OpenSCAD about/documentation.** Primary project pages, checked 2026-09-28: https://openscad.org/about.html and https://openscad.org/documentation.html . Script-oriented solid modeling makes it a bounded alternative. This is not qualification of every library, command-line build or geometry class.

**S04 — FreeCAD official repository.** Primary project documentation, checked 2026-09-28: https://github.com/FreeCAD/FreeCAD . Describes parametric history, drawing support, Python API and OpenCASCADE. Supports a human review/editing role, not independent mechanical acceptance. Exact FEM/CalculiX installation/version claims are deliberately not made because the official FEM wiki was inaccessible in the research session.

**S05 — PrusaSlicer official repository.** Primary project documentation, checked 2026-09-28: https://github.com/prusa3d/PrusaSlicer . Documents command-line automation, print-instruction generation and preview. Exact compatible machine/profile/runtime is unselected.

**S06 — OctoPrint Job Operations.** Primary API documentation, checked 2026-09-28: https://docs.octoprint.org/en/main/api/job.html . Defines job commands and response/permission semantics. A pause with omitted action defaults to toggle; restart can cancel and restart the selected job. Supports explicit operations and non-replayable starts. Canonical starter R18.

**S07 — OctoPrint Printer Operations.** Primary API documentation, checked 2026-09-28: https://docs.octoprint.org/en/main/api/printer.html . Broad control operations include commands, temperatures and motion. HTTP acceptance is not a full synchronous device execution trace. No safety-rated stop guarantee is inferred.

**S08 — Moonraker Printer Administration.** Primary API documentation, checked 2026-09-28: https://moonraker.readthedocs.io/en/latest/external_api/printer/ . Documents printer status, G-code execution and distinct print actions. It is a possible machine-specific adapter, not a supervisory safety system.

**S19 — PrusaLink official repository.** Primary project repository, checked 2026-09-28: https://github.com/prusa3d/Prusa-Link . Retained as a possible alternative for a future compatible device. No ownership, universal model support, granular authorization or exact firmware interoperability was qualified.

## Metrology and engineering discipline

**S09 — NIST/SEMATECH handbook, Gauge R & R studies.** Primary government statistical guidance, checked 2026-09-28: https://www.itl.nist.gov/div898/handbook/mpc/section4/mpc4.htm . Provides a framework for characterizing measurement repeatability and reproducibility. It does not certify Haven's gauge or define this fixture's tolerance.

**S10 — NIOSH, Approaches to Safe 3D Printing.** Primary government guidance, DHHS (NIOSH) Publication 2024-103, checked 2026-09-28: https://www.cdc.gov/niosh/docs/2024-103/pdfs/2024-103.pdf . Reviews printing hazards and controls. Supports a process/workspace-specific control plan; no material or household setting is declared safe by citation alone. Canonical R19.

**S11 — NASA, Evolved Structures Guide.** Primary technical guide, NTRS 20240005675, 2024, checked 2026-09-28: https://ntrs.nasa.gov/api/citations/20240005675/downloads/Evolved%20Structures%20Guide_Paper.pdf . Separates design/optimization, detailed analysis and fabrication/inspection. Aerospace allowables, factors and certification are not transferred to Haven fixtures. Canonical R34.

## CAD generation and bounded optimization research

**S12 — Text2CAD.** NeurIPS 2024 / arXiv 2409.17106, checked 2026-09-28: https://arxiv.org/abs/2409.17106 and https://github.com/SadilKhan/Text2CAD . Evidence for text-conditioned parametric sequence generation. Results do not establish arbitrary engineering intent, tolerance compliance, fabrication or independent acceptance.

**S13 — CAD-Recode.** arXiv 2412.14042, checked 2026-09-28: https://arxiv.org/abs/2412.14042 . Demonstrates reconstruction toward editable CAD code from point-cloud input. Reconstructed geometry is not metrology ground truth, inferred design intent or evidence of manufactured performance.

**S14 — Text2CAD-Bench.** arXiv 2605.18430, May 2026, checked 2026-09-28: https://arxiv.org/abs/2605.18430 . Presents broader text-to-CAD evaluation and reports remaining difficulty on complex tasks. No independent benchmark run or model ranking is claimed.

**S15 — Samani and Atkeson, Programming Manufacturing Robots with Imperfect AI.** arXiv 2603.22118v1, March 23 2026, checked 2026-09-28: https://arxiv.org/abs/2603.22118 and https://arxiv.org/html/2603.22118v1 . Uses bounded LLM guidance inside optimization with an approximate evaluator. Quantitative comparisons use that evaluator; physical validation is a qualitative subset. Proxy failure prediction is not an observed fleet failure rate.

**S16 — Guidetti et al., Data-Driven Process Optimization of Fused Filament Fabrication based on In Situ Measurements.** arXiv 2210.15239v1, checked 2026-09-28: https://arxiv.org/abs/2210.15239 . Reports sensor-guided process optimization in a specialized material/process setting. It does not validate ordinary Haven fixtures or authorize copying the apparatus/process.

## Autonomous-laboratory context and corrections

**S17 — NIST, Development of Standards to Support a Modular and Autonomous Laboratory Ecosystem.** Checked 2026-09-28: https://www.nist.gov/programs-projects/development-standards-support-modular-and-autonomous-laboratory-ecosystem . Evidence for modular contracts and provenance needs, not a finished standard Haven already meets. Canonical R13.

**S18 — Ceder Group, Autonomous experimentation for accelerated materials discovery.** Checked 2026-09-28: https://ceder.berkeley.edu/research-areas/autonomous-experimentation-for-accelerated-materials-discovery/ . Describes A-Lab's specialized autonomous materials experimentation. Inspiration for closed-loop evidence handling, not a general workshop agent or household chemistry procedure. Canonical R14.

**S20 — Author Correction: An autonomous laboratory for the accelerated synthesis of inorganic materials.** DOI 10.1038/s41586-025-09992-y, published January 19 2026, checked 2026-09-28: https://www.nature.com/articles/s41586-025-09992-y . Correction metadata was verified but the full correction body was inaccessible, so substantive correction details were not independently reverified. Preserve canonical R15.

## Project sources

**P1 — Cumulative starter v1.0.** Supplied archive SHA-256 `55f693f64c56a9d8f13a6cd5725ab4c427af6ade2e127fe8e71829eca1f1d412`. Establishes project intent and deliberately inert examples, not actual runtime/device acceptance.

**P2 — NIGHT-01 review archive and independent review.** Archive SHA-256 `4bea43265cbc4f7cbe45c31fb76ad2368aa7bc1802bf3f4bdb95a1e7ec5cb67b`. The reported tests and R1 reproduction remain attributed review evidence; none was re-run in R08. The same-author numerical checker is not independent physical qualification.

**P3 — NIGHT-01 MORNING_REPORT.md.** Reports N1/N2 synthetic implementation and preservation checks. No actual CAD/slicer/device interface was delivered by that reported notebook.

**P4 — H00 R02 integration review.** Recommends thin coordination, domain authority separation, frozen mock schemas, reuse of N1/N2 and R1 before live expansion. Recommendation is not operator approval.

**P5 — R02 integration/package design.** Maps R08 to H09, calls for EX28/N2 reuse and distinguishes Hxx/Rxx ownership. Proposed readiness/costs are not permissions.

**P6 — R08 research assignment.** Defines the bounded research/design scope. It does not authorize implementation or physical action.

## Research stop and access limits

This was a bounded design-oriented primary-source review, not an exhaustive literature ranking. Software compatibility, local model efficacy, physical apparatus, current implementation state and vendor-specific safety behavior remain qualification work. Inaccessible details were not replaced with uncited secondary claims.
