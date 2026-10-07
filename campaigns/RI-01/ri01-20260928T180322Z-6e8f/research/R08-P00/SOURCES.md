# R08-P00 source register and verification limits
Checked2026-09-28. SOURCE_REGISTER.json gives exact local SHA256, byte count, source commit when actually known, original path, and read scope. INPUT_USE.json maps52 input-use rows to concrete findings and decisions, including three actual consultation records. Additional hashed source files are explicitly HASH_ONLY rather than falsely described as substantively used.

Original main from frozen intake:376031e182c57495912baf6727093b0b188da568. R08 exact PR13 handback:5be0910420a9afd786d2ffd65054e5c4830ba714, original design/H09/R08/v1/. R02 exact publication edition2:d9bc23e848be9af44b6d07f9526f7badf7245b52. R06 exact source:5b85aa0e9106a484e4b5c571460c2d0010ce1eeb. No Git query was performed in this task. Campaign-only artifacts are hash-pinned with commit null; no commit identity is invented.

## Load-bearing input pins
| Artifact | SHA256 |
|---|---|
| R08 interfaces |01ed60d55591b3d4a2a03cafaf4c299d24c1c9f47d406d68bd3dd2bac6d02f03|
| R08 experiments |bfeff2b9e890c5e1e30833c748ea15b68567a9775e8ac062cb3ac6f716da60c8|
| REV-R08 |927079d45477d292a6d31f427e5cefba9c382263db03ffbce7a60f9395556d41|
| REV-R06 |b00b0e57f577b53d1c6728766569391be674449c8e483952e0b6e82028e16ca8|
| CORE MANIFEST.sha256 |7c0349a42c4345f68cd2e2abec6e3827a475177ff0d757509114fec05d1515e2|
| CORE architecture |abf33854c793fc58c6e6679348a34d546abe5051bdfd6d91978e24b75449eb82|
| CORE contracts |df19f37926b33851236aca230859adfef332a85120380ea04c24294237c2e6d0|
| VISION-ARCH |64615521c1e27c0bbc1f7e82eb919341f8493be60f2b568b08e785661f978e51|
| CODE-0 |066bbc38273320895dbd5cf1fc3fde31c209253103fa2e170dbf905ff8d4abc8|
| EVIDENCE-0 |edd0f92e12e909a5df089ed735f9a8812515003eb30af57cae67da14d66c426d|
| REVIEW-R12 |392ae8ceaf82e5dd07cb23c48e67d0e123870d42c0f16d87e46044a379e45600|
| R12 handoff manifest |fec9c4c223fa2370db6bcbe8fd61980d284d92a31a22b37d707dcd48db0a8d77|

## Narrow primary-source refresh
- W01: [Publisher correction](https://www.nature.com/articles/s41586-025-09992-y.pdf),19January2026. Publisher indexed text was accessible through search and corroborated the accepted R12 correction. Direct fetch failed; no PDF visual inspection or experimental reproduction. Used for correction/contamination/qualification lineage, not autonomous chemistry.
- W02: [NIST Gauge R&R](https://www.itl.nist.gov/div898/handbook/mpc/section4/mpc4.htm), primary text accessed2026-09-28. Used to distinguish measurement factors.
- W03: [NIST TN1297D4](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-d4-measurand-defined-measurement-method), primary text accessed2026-09-28. Used for method/reference uncertainty. The first guessed D4 URL returned404; corrected via the official parent-page link. Neither NIST source approves our thresholds, replication count or bootstrap coverage.

Web response bytes were not archived; SHA256 is null. Source indices are not full raw PDF downloads. No new tool/license/model recommendation requires adoption here, so the original broad survey was not repeated. A future executable CAD/model package must verify its exact artifact, dependencies and license at selection.

## Actual-versus-proposed ledger
| Work | Actual status |
|---|---|
| Read exact source/tests/logs, parse JSON, calculate hashes | PERFORMED; read-only |
| Native peer question/answer via root | PERFORMED forR07; H06 question pending independent review |
| Direct benign synthetic PNG inspection | PERFORMED; image observations only |
|20R08case/11N2test reconciliation and new docs | AUTHORED, submitted for independent review |
| New canonicalization/unit/authority/metrology tests | PROPOSED_NOT_EXECUTED |
| N1/N2 suites | Historical recorded33/11pass; no rerun here |
| Original AT-ENG acceptance | NOT_EXECUTED_BY_THIS_TASK |
| Real model/CAD/slicer/printer/robot/sensor work | NOT_EXECUTED |
| Physical thresholds/statistical interval validation | NOT_APPROVED; proposed owner/reviewer closure |
| Current M0/R1 repair evidence | SOURCE_UNAVAILABLE in this research slice |

Missing original R08 INPUT_AUDIT/146-file comparison, H00 original review and later independent R1 review stay explicit. Source identity does not fill these gaps. New CORE/R12 review records are additional actual inputs rather than substitutes.

## Maturity and affordable path
Historical synthetic arithmetic -> proposed inert scalar/correction sidecar -> separately qualified independent authority/holdout evaluation -> measured existing mount/manual stop -> restricted reviewed CAD template -> supervised fabrication and inspection -> qualified device gateway -> independent multi-specimen/carrier/sensor-effect study. Each stage keeps negative evidence and has its own prerequisite. Start with existing measured hardware and deterministic checks; do not buy a printer or use a model merely to populate the design.
