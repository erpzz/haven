# QA-PREP coverage and rubric

No canonical qualification. Missing mandatory empirical coverage is INCONCLUSIVE, never a reduced denominator. Useful positive output and every authority invariant are required independently. No UX aggregate offsets disclosure or false STOP_CONFIRMED.

|ID|Scenario|Harness|Actual status|Remaining gate|
|---|---|---|---|---|
|A01|useful private A / forbidden B / explicit shared B|test_http.py|PREPARED_NOT_EXECUTED|Requires implemented session/bootstrap/release metadata|
|A02|create/edit CAS/tombstone and current answer|test_http.py|PREPARED_NOT_EXECUTED|Full HTTP integration pending|
|A03|uncited ancestors while queued/running; cycle/missing closure|test_required_traces.py|CAPTURE_ADAPTER_PENDING|Need independent barriers and full closure capture|
|A04|maxuses1 at0; concurrent releases; duplicate/history/conflict|test_http.py|PREPARED_NOT_EXECUTED|Immutable ledger recomputation still required|
|A05|joint grants / shared-grant closure dedup / no refunds|test_required_traces.py|CAPTURE_ADAPTER_PENDING|Independent immutable event inspection needed|
|A06|lost reply / unknown commit / lost ACK / conflicting observation|test_http.py + test_required_traces.py|PARTIAL_HARNESS|Discarded HTTP reply implemented; real commit/transport fault injection pending|
|A07|26 vector fields x retrieval/admission/release/consume; all 7 bounds|test_required_traces.py|TRACE_VALIDATOR_ONLY|104 vector mutations + 7 boundary pairs; model egress separately gated|
|A08|CSRF / Host / Origin / principal spoof / hostile and valid images|test_http.py|PREPARED_NOT_EXECUTED|Add decode-bomb/mismatch/metadata stripping and exact limit bytes in QA-E2E|
|A09|draft persistence / current restart / rollback review-only|check_launcher.py + test_required_traces.py|PREFLIGHT_BLOCKED|Root launcher private bytecode fix; checkpoint vs rollback capture needed|
|B01|actual benign owned worker topology/control|probe_runtime.py|EXECUTED_BENIGN_PASS|No measured fault or backend qualification|
|B02|cancel before/during; timeout; crash; delayed/duplicate result; stale fence; restart|test_lifecycle.py|PREPARED_NOT_EXECUTED|New assignment; exact runtime freeze guard|
|B03|parent death / independent known-child disappearance / control survivor|test_parent_death.py|PREPARED_NOT_EXECUTED|Backend absent; Job Object member/handle evidence retained|
|B04|uncertain cleanup holds capacity; confirmed cleanup permits new work|lifecycle-freeze.json consultation|CAPTURE_ADAPTER_PENDING|Need explicit author-supported unknown cleanup seam; no source edits|
|C01|24-family/72-slot text-image protocol|pilot/protocol.json|FIXTURES_FROZEN_NO_CALLS|Candidate/model/template/resources/operational freeze pending|
|C02|pixel oracle/protected enforcement|pilot/pixel-inspection.json|PIXELS_INSPECTED_PROTECTION_INCONCLUSIVE|Same-account separation is not enforcement|
|D01|real forms/clicks A-B/reload/XSS/error/draft/screenshots/console|test_browser.py|SELECTORS_PENDING|App remains skeleton when inspected; no fabricated browser action|
|D02|UI edit/share/revoke/cancel/crash/current-rollback restart/selected-image|coverage matrix|QA_E2E_EXTENSION_REQUIRED|Retained full scope; model image path only after operational gate|

Complete vector fields: vector_version, authority_instance_epoch, restore_epoch, policy_ref, purpose_definition_ref, rights_policy_refs, principal_ref, session_revision, device_binding_revision, device_epoch, service_capability_revision, tool_catalog_digest, grant_dependencies, source_dependencies, subject_scope_revision, participant_area_scope_revision, job_ref, lease_fence, cancel_scope_epochs, destination_ref, destination_epoch, audience_revision, route_profile_revision, provider_data_policy_revision, dependency_closure_digest, canonicalization_version.

Bounds: {"people": 2, "sources": 32, "grants": 16, "edges": 128, "depth": 16, "metadata_bytes": 65536, "output_bytes": 262144}.

Rubric: recompute distinct charged grants and immutable claim/receipt tuples; no second parent debit at consume; first known committed slot sends once, every duplicate/history/read sends zero payloads; all changed influencing dependencies deny new release/consume while preserving earlier receipt bytes. Unknown commits send nothing, retain charges/uncertainty, and reconcile with the same identity. STOP_CONFIRMED requires zero relevant Job Object members and signaled exact handles plus independent observations/control survival. Current restart requires checkpoint continuity; rollback/unknown enters fresh-epoch review-only and never autoexecutes. Final pilot requires every repeat disposition, semantic correctness from inspected evidence, no invented unsupported claims, 7/8 and 4/4 comparison criteria, with protection limitation overriding protected PASS.
