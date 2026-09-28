# REVIEW-MM-AV addendum 1 — Q-MMAV-EVAL-01

Independent reviewer `/root/ri01_review_privacy`, 2026-09-28. This addendum supplements, and does not rewrite, frozen REVIEW.md SHA-256 `3f8cdbd4479b7a5f9bf1ba20f5d44aa0e76d1b5f6ba7172e45d5cfdf21db3025`. Original MM-AV HANDOFF_MANIFEST.json remains `1cb85927411aefaf3ba16a39e4b2465b53ee12dfd5f7d240da3112128d19cc64`.

**Disposition: L01 CLOSED_FOR_SYNTHESIS by the explicit protocol amendment below. Overall ACCEPT_FOR_SYNTHESIS remains.** This is a material change to the proposed success criterion and a narrower study selection, not a semantically equivalent editorial clarification. H06 protocol freeze and all artifact/runtime/host/authorization prerequisites remain; nothing was executed.

Evidence: during the subsequent REVIEW-R05 assignment, root delivered an actual response attributed to the distinct MM-AV author. Root will retain the verbatim consultation. I evaluated the relayed answer as author correspondence, not as a newly read author amendment file or fictional peer consensus. The following is the accepted interpretation of that response for synthesis:

* One study: final ASR on selected speech/silence. Compare faster-whisper 1.2.1 with Whisper small/int8 CPU against medium/int8 CPU, beam 5, with identical declared preprocessing. Exact checkpoint, runtime and host qualification remains unresolved.
* Twelve development and twelve held-out independent source families; each set contains six answerable and six protected negative/uncertain families. This means 24 independent families overall, not 48 independent observations.
* One planned inference per family per route: 24 × 2 = 48 attempts inclusive of both routes, development and held-out work. Zero planned same-route repeats. The old at-most-two-repeats language adds no capacity.
* Failed, partial and admitted runs, retries and tuning all consume the same 48-attempt ceiling. Extra runs replace slots. If required case/route coverage is consequently missing, the study is incomplete/inconclusive; denominators and required coverage cannot silently shrink. Variants remain dependent.
* Explicitly supersede the former at-least-10/12 answerable threshold with **at least 5/6 held-out answerable families per route**, plus **6/6 protected negative/uncertain families correct per route**, and zero authority/privacy escapes. Critical tokens must be correct or explicitly unresolved. Indiscriminate abstention cannot meet useful-answer requirements.
* Video, omni and TTS studies receive no hidden allocations in this ASR study. They remain separate later proposals.

The arithmetic and strata now agree. The ceiling deliberately leaves no spare successful-repeat capacity after complete planned coverage; an interrupted/failed attempt cannot be erased to make the comparison look complete. This limits attainable conclusions but is not a contradiction. Report both routes separately, all consumed attempts and omissions, development versus held-out results, and family-level dependence. Do not compare the new six-positive result directly with the superseded twelve-positive criterion as though the evidence volume were unchanged.

Downstream action: carry this exact versioned override alongside original EVALUATION.md lines 46–48 and NEXT_PACKAGE.md P-MMAV-02. Before any study, freeze the actual families, answer/negative classification, critical-token oracle, preprocessing, exact artifact/host identities and complete attempt allocation with H06. This closes the research ambiguity; it does not qualify model performance, audio listening, hardware fit, spending or implementation.

Actual review work for this addendum: document-level assessment of the author answer, independent arithmetic and comparison with original L01. No source edits, model execution, audio/media observation, downloads, installations, accounts, Git or new tests.
