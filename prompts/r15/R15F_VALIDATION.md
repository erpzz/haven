# R15F — Independent Observatory evaluation and first useful slice

Act as the bounded evaluation-design reviewer, aligned with H06/R13. Do not implement competing features or promote the author's claims merely because the interface looks impressive.

## Inputs

Pin https://github.com/erpzz/haven main and read its root instructions, `coordination/R15_OBSERVATORY.md`, the full R15 prompt and issue #12. Review whatever actual R15A–E or integrated R15 handbacks exist, plus available R02/R03/R06/R07/R08/R13 requirements. Identify absent inputs. Compare claims to the exact owner's GEV fork and source/terms records. Earlier synthetic, document or hash checks are not new runtime acceptance.

## Work

Choose one small Observatory demonstration worth building and a comparison baseline of GEV plus a separate event table. Define what improvement would matter: correct evidence selection, quicker investigation, better uncertainty comprehension or meaningful scenario comparison. Distinguish a smoke test, contract test, usability study, model benchmark and physical qualification.

Provide at least 18 cases spanning stale/unavailable feeds, quota errors, historical imagery or traffic animation mislabeled live, shader thermal mistaken for measurements, contradictory times, coarse geometry, bad coordinate/altitude frames, unknown sensor coverage, revoked private output, private data in share links, malicious source/import, cancellation, background browser limits, scenario escape, unavailable resources and concurrent users. Each case has actor, setup, expected result, forbidden result, retained evidence and reviewer.

Review conditional privacy semantics rather than freezing an unapproved H04 policy. Record whether cancellation stops publication, the owned process, shared-server work and billing separately. Verify every proposed success gate has a source version and scope. Do not accept requirements by test-count arithmetic, a screenshot or a source hash alone.

## Return and boundaries

Proposed output `design/H00/R15/inputs/R15F/v1/`: ACCEPTANCE_MATRIX.md, FINDINGS.md, FIRST_SLICE_GATE.md and SUMMARY.md. Provide accept/amend/defer recommendations, highest-value missing tests and one bounded implementation proposal with prerequisites and stop conditions. Do not require every frontier branch to finish before a public/synthetic demonstration, but do not silently discard retained requirements.

This task is design and source review, not execution. No installations, benchmarks, model calls, private fixtures, human trials, code edits, account/device connections, workflow execution or repo writes. Execution would need a separate disposable environment and explicit scoped approval. Stop at the review handback.
