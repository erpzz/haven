# R02-P01 source register

Read/verification date: 2026-09-28. New primary research was deliberately limited to lifecycle and transaction semantics. Broad model/license/rate survey is reused from exact REV-R02, not represented as a new P01 benchmark. No media, model weights, packages or private source bytes were downloaded.

## Primary sources checked in P01

- P01-S01: SQLite, [Isolation](https://www.sqlite.org/isolation.html), live official documentation, checked2026-09-28. Supports serialized single-writer transactions; does not make a remote display atomic with a database commit.
- P01-S02: SQLite, [Transactions](https://www.sqlite.org/lang_transaction.html), live official documentation, checked2026-09-28. Supports BEGIN IMMEDIATE and explicit busy/commit handling; read transactions retain snapshots. Exact SQLite runtime version has not been inspected here.
- P01-S03: Python, [multiprocessing, version3.12](https://docs.python.org/3.12/library/multiprocessing.html), page identified3.12.14, checked2026-09-28. terminate may skip finally and leaves descendants; kill uses SIGKILL on POSIX. Methods such as join belong to the creating process; future surviving supervisor must own the process it observes. Documentation is not evidence that the prototype has that supervisor.

Primary web response byte hashes: NOT_CAPTURED. Licensing/hosted-model capabilities and prices remain dated documentary findings in REV-R02; recheck changed versions at any implementation/procurement gate. No new pricing claim is necessary for this zero-paid-call proposal.

## Exact local source identities

Paths are relative to campaign root. R02 incoming files correspond to https://github.com/erpzz/haven PR15 commit d9bc23e848be9af44b6d07f9526f7badf7245b52, original path design/H02/R02/v2/<filename>. Recovered files are exact selected archive members with mappings in PROVENANCE.json/SUPPLEMENT-1..3.json; they are not asserted to represent active M0/R1. Reviews are root-persisted campaign artifacts; no commit for those artifacts was supplied to this author.

| Path | SHA-256 |
|---|---|
| inputs/recovered/night01/lab/CONTRACT_MAPPING.json | 7cfadceae9a30c8f56df7d13a872dbd836bf76c7f8aa81b6435eb42e5e5d6790 |
| inputs/recovered/night01/lab/README.md | 1a9ac8ce41cef3cb3c13d0047ca26e8fd2fd642fd1d62c112203b221f287b847 |
| inputs/recovered/night01/lab/requirements.txt | 64e075e72257bd94140f25d25b9ed05e0997323f50094293780f664b975930b9 |
| inputs/recovered/night01/lab/run_checks.py | 0046d02c4fcf90a3e4ecdf586180c2fc77b91bb1152940aa7ac64a3a6557e412 |
| inputs/recovered/night01/lab/fixtures/context.json | dc078b743931add0b86f96a2cf379929bce98a6e18a948994f2519862fb3d9b9 |
| inputs/recovered/night01/lab/fixtures/engineering.json | a25de0ebb56447ff6f0423c78bd4aa0c854bd7dfd223f0b4965038b046d66b64 |
| inputs/recovered/night01/lab/haven_lab/__init__.py | 16c4d5c0b3499ebaf385aa52b5edf573d50d57b8c8ff3f9104902763ab00b523 |
| inputs/recovered/night01/lab/haven_lab/__main__.py | 79ee6f134c5c5193377cf9b189cbdcc3e2095e49ba9cec310114441c15a917c4 |
| inputs/recovered/night01/lab/haven_lab/backend.py | 897ad93277399e08903f72e5e25e8dcd4e0aab6379618cb1703d3abf63d64a81 |
| inputs/recovered/night01/lab/haven_lab/cli.py | 9f72fe8ebd03e524711747ac2a1eb2bcff690197bfaa5f3631494eb621e19237 |
| inputs/recovered/night01/lab/haven_lab/context.py | 7c536a2bdd52ec543204d213e69c1811134eb7d90d7f124a3d9eb0b48b911fe8 |
| inputs/recovered/night01/lab/haven_lab/coordinator.py | 29001252a1b450587f746610c88b93e25f963eb117f8bb87f5e132b41c145345 |
| inputs/recovered/night01/lab/haven_lab/design_check.py | b6ca5348a1393b67e0c56ab361cea8d69d67f05f54fefef0570257ce0746e3b4 |
| inputs/recovered/night01/lab/haven_lab/notebook.py | 6cb81f737325fd6625e96230b9a688e048479db801e525add29fccb9f6c3cbac |
| inputs/recovered/night01/lab/haven_lab/render.py | dae6b79597220dea72a661684b926d47d75f867ff738e36102bf0f3ccc05dd93 |
| inputs/recovered/night01/lab/haven_lab/store.py | cf1244197cbb86a9d7488f2c2714ca987cb3b23228a53050beca471c6dfb8273 |
| inputs/recovered/night01/lab/haven_lab/synthetic_score.py | f1927882db9174b10da7e96cb9850c451d9884f990155d642e96a34edbf85721 |
| inputs/recovered/night01/lab/haven_lab/types.py | 1830730ea641cc9d4b1997113816f293c12f40d5593b91da22f23058eb01b955 |
| inputs/recovered/night01/lab/haven_lab/validation.py | 803e7565bf490155160e18c79d43a59900a481f73a5a76b9641978f31bbd0a96 |
| inputs/recovered/night01/lab/tests/test_n1.py | c21608db960e39d9773823157d87958f057eeaba53209faf2a817afbc115dfd0 |
| inputs/recovered/night01/lab/tests/test_n2.py | 3ae28ae1fd0390b284473e2e4ddad449ab45d8dfe3a4327688bd21e3719dbd4a |
| reviews/REV-R02/REVIEW.md | 69cf8d1644361fa521a7c458ea08dda0aa4b4843eec9a9b4326bde978d981746 |
| reviews/EVIDENCE-0/REVIEW.md | edd0f92e12e909a5df089ed735f9a8812515003eb30af57cae67da14d66c426d |
| inputs/recovered/PROVENANCE.json | 1d60bb74ab3e6de17274009a66d157b4a5edf59654f6e7ee6ea2dba0db3beb7d |
| inputs/recovered/SUPPLEMENT-1.json | 64856c4902836ef94e7f13235abd75c164f741f3b27f9e1988dc1f63a77e6811 |
| inputs/recovered/SUPPLEMENT-2.json | 7e5f84fab9a6ef137e60db1ffa4f3fbe0e5c06686a90bd8cc1036812f5987a09 |
| inputs/recovered/SUPPLEMENT-3.json | abc7ccb96dd3e64d97f10263b44a3bf3e6b3febb363d71a51b9e233861f8d80e |
| inputs/recovered/night01/REDACTION_MANIFEST.json | a662d067ee7723b123ceb617bf6e529726787fd3bbd42e66747be5722e94aca0 |
| inputs/recovered/night01/outputs/N1_GATE.json | d1e330280582a181a5a7750b24ff56b12ad9740b12a09d47e3adc1d9749da66c |
| inputs/recovered/night01/outputs/logs/n1-20260928T032012Z-94d095.json | ba7bac7e8e87353edb5b6d2a6b250c807a3962a5cacc464fdc7304f04a5d0df8 |
| inputs/recovered/night01/outputs/logs/n2-20260928T032102Z-341135.json | f3c91075cbf52200190e58d9478b143c0a870479a07132fa3ad3e4a8f21d5f69 |
| inputs/recovered/night01/outputs/n2-fe154a18-0dd5-48f7-a9da-afc9842414d3/results.json | 580cc97ba33a1f4c4a6ec3b1a0a0942e713b9175bc46771ca0a248d2846b6aa0 |
| inputs/incoming/R02/ARTIFACT_CHECKS.json | 089d2a1171c1398e76a987b2e94178f7de115701a959f348475e9a24980ff9aa |
| inputs/incoming/R02/BENCHMARK_AND_EXPERIMENTS.md | 641e6f1b409eee0cd69ab182e586957ec17db22e916692bedcd68c7988e665cd |
| inputs/incoming/R02/CONTRACT_DESIGN.md | 9cc1ce4ce5d2d240b244513aa7680ba0015d86829216497877f3f90cd51856d7 |
| inputs/incoming/R02/INPUT_AUDIT.json | 55dba1e5603f3e1aca31e6de40a64fcd5eb428fc7e080bf44012531f0ab5f4d7 |
| inputs/incoming/R02/INTEGRATION_AND_PACKAGES.md | f8da2b37bd1310b56aebc0887296c938b2a5e3586af5bed4bef4511c18d4471a |
| inputs/incoming/R02/INTEGRATION_SUMMARY.md | fd271448a08ecaa8f8300b4d3e33fc1970c13db5e6be0a85db5c0b4bab7d02f1 |
| inputs/incoming/R02/MANIFEST.sha256 | 208216b9bcac32c9e658bbfb3279d625f4451c8f571e5916147aa15b55974cd0 |
| inputs/incoming/R02/PUBLICATION_RECEIPT.md | 600f21bd3befa6c2aec64116b25217a2ed9b3f822c333df05d020aef6aa256c2 |
| inputs/incoming/R02/PUBLICATION_SOURCE_AUDIT.json | b0f2a877d66ee9bf3df0d7ad6f3d90b97eeaf2e6664a80708285ea6726780225 |
| inputs/incoming/R02/R02_HANDOFF.md | c44552107a9e1130d4dd977d2130a1a81a9b6d8308fa939b27f352ad8b4f115f |
| inputs/incoming/R02/README.md | 1162aad578dc5109b2d6ca74ac16e93d3b5ab4f31002c37c81fececfacef01ae |
| inputs/incoming/R02/SOURCES.md | 05d2e874c971dc21952fecb0cbbee6d25051173e432382ed8f33ed9b0afa9afa |
| inputs/recovered/starter/scope/requirements.json | b904206fefcd553003129bfc30ede87785ff3325a13657f162125b3868492f56 |
| inputs/recovered/starter/tests/acceptance_catalog.json | d41660b25a5b105024083cf4c3c0e914c92dc4b68afef60be4649153ab06b478 |
| inputs/recovered/night01/outputs/REVIEW_FINDINGS.md | be0b48a67523a38935fd55cc61967332774dbb53d52ec0c942cf26b1eeefdede |

Core source/test/fixture files, logs, gates, R02 substantive packet and the review/redaction records were read. Hashing inventory also includes small entry-point/requirements files; a hash record alone is not a claim that every inventoried file was substantively analyzed. CASE_CROSSWALK names the specific evidence used for each claim.

## Fidelity and missing inputs

N1 final log:33 unique methods; N2 final log:11. Each has17 recorded source hashes; all17 match recovered bytes. This is data/identity checking, not execution. Historical commands are evidence strings and were not run.

N2 original gate f2b62ee7cdb926032b6d846c6adb91f990179e94c06b71782ffe8c7113a63019 maps to review gate d1e330280582a181a5a7750b24ff56b12ad9740b12a09d47e3adc1d9749da66c in producer redaction receipt a662d067ee7723b123ceb617bf6e529726787fd3bbd42e66747be5722e94aca0. P01 did not inspect private originals or reproduce this transformation.

Original H00 R02 review, later independent R1 review, R02 original ZIP, active M0/R1 source and actual host/model artifacts: SOURCE_UNAVAILABLE to this assignment. Historical NIGHT-01 REVIEW_FINDINGS is a different review. No guessed hashes or reconstructed approvals.

R03 actual consultation Q-R02P01-R03-01 is attributed to /root/ri01_privacy via root; its full report/hash was pending when incorporated. CODE-0 static anchors were also relayed by root and their exact source paths read directly. INPUT_USE preserves these as messages, not invented files.

## Rights and modality

Project source is used under campaign authorization; no new open-source license is asserted. Original authorship and third-party terms remain. No private raw data or new third-party media imported. Inspection mode TEXT_CODE_JSON and DOCUMENTATION_ONLY; no image/audio/video/sensor observation or runtime modality test. No suitable media asset was supplied in this task's campaign inputs. Source hashes establish identity, not semantic truth, permission or measured capability.

