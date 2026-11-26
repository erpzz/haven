# Phase 3 conformance laboratory — synthetic policy oracle

**Status:** Executed *reference-oracle* tests, not real EntraOps/Maester import tests. This standalone pack is designed to make future offline adapter behavior independently checkable. It intentionally does **not** require BloodHound, EntraOps, Maester, Microsoft Graph, a model, network access, elevated privileges, or other Python packages.

This branch is stacked on the **draft** [Phase 3 evidence contract (PR #110)](https://github.com/erpzz/haven/pull/110), which is stacked on #109 and #108. The objective is to freeze 20 synthetic examples with expected decisions so that future adapter implementations cannot redefine success after observing their own output.

## Contents

- `cases.json` — exactly 20 synthetic declarative tests, P3-01 through P3-20; expected results are explicitly specified in the file.
- `evaluator.py` — tiny stdlib reference policy evaluator for *simplified contract-level inputs*. It is **not** a production parser, importer, remediation engine, or parser for real exporter payloads.
- `test_evaluator.py` — independent harness tests including deliberately corrupted gold expectations, missing/mismatched adapter outputs, unknown Maester schemas, denied cross-dataset joins, and safe tool lists.

## Commands (Python 3.11+)

From this directory:

```bash
python3 evaluator.py
python3 -m unittest discover -s . -p 'test_evaluator.py' -v
```

To demonstrate the external-adapter comparison interface (only a smoke test of the interface, not an actual importer):

```bash
python3 evaluator.py --write-oracle /tmp/purple-apm-reference.jsonl
python3 evaluator.py --adapter-results /tmp/purple-apm-reference.jsonl
```

Future Codex adapter commands should take each `cases.json` `input` and emit one line per test as `{"id":"P3-01","actual":{...}}` in **JSONL**, with decisions determined by the implementation. Then invoke:

```bash
python3 evaluator.py --adapter-results /path/to/adapter-actual.jsonl
```

**Never copy `expected` directly into `actual` in a real adapter run**: that only validates wiring, not policy behavior. Maintain a separate evidence source and attach run metadata. Use frozen synthetic data in CI and keep actual tenant exports in the private state directory only.

## What this proves and does not prove

It proves the reference evaluator produces the frozen expected outcomes and that a mismatching adapter output is detected. It does not show that real raw EntraOps OpenGraph exports, Maester 2.3 JSON or Maester 3.0-preview JSON can yet be imported. Those interfaces must be implemented and tested against shape-accurate examples at pinned revisions by Codex, with explicit labels identifying any manually constructed fixtures. The `maester_shapes` vector only tests the compatibility *policy*, not full upstream schema compliance.

No test can establish an LLM agent's robustness merely by feeding hostile strings into this no-execution oracle. The injection vector protects this reference's fixed tool list; a future integrated test must actually exercise the model, gateway and tool-call receipts.

The reference suite deliberately never asserts that a graph path is effective privileged access or that a passing Maester test closes an attack path. Historical graph snapshots and current observations remain distinct.

## Upstream schema constraints verified during design

- [EntraOps BloodHound exporter](https://github.com/Cloud-Architekt/EntraOps/blob/main/Integrations/BloodHound/README.md) emits an OpenGraph overlay using per-RBAC-system EAM source exports. The extension schema defines domain-specific EntraOps relationship types; their existence alone must not establish a traversable attack path.
- [Maester result schema](https://maester.dev/docs/result-schema): 3.0-preview adds fields over the 2.x shape (including `SchemaVersion = "2.1"`). A stable 2.3 export need not have those preview-only fields.
- [Maester affected objects](https://maester.dev/docs/export-results/): `UniqueId` is a **derived** value, and user redaction is pseudonymization—not a verified native Entra object ID mapping.

## Proposed Codex implementation acceptance

1. Pin and inspect real producer revisions before mapping exporter JSON. Capture publicly shareable minimized schema examples, with **all private/identity data replaced by synthetic placeholders**.
2. Build independently tested **offline** EntraOps/Maester fixture readers and normalized provenance. Avoid changing `path_runs` or source membership graph semantics.
3. Map each P3-xx vector into its real importer policy; run it as a second implementation independently of this oracle. Create additional raw-format compatibility tests for stable 2.x and preview variants.
4. Produce the adapter JSONL result file and compare against `cases.json`; preserve error explanations, collection run IDs, digests and timestamps privately.
5. Require clean runs on replay/conflict, cross-dataset joins, PIM eligible vs active, derived Maester UniqueIds, incomplete collection and false-remediation guards. Make model-related tests separately report the actual model route and denial receipts.
6. Open a reviewable **new branch/PR** stacked on this conformance work or the approved integration base; no merge or production connection without operator approval.

## Review boundary

This pack is public-safe and contains only constructed synthetic examples. Source provenance and executed command output should be recorded in the PR handback. No data collector, service, database, dashboard, MCP client, credential, live tenant, or model is modified by running the reference tests.
