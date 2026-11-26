# Security evidence schema (`haven-cyber-evidence-v1`)

Implemented in `haven_cyber/evidence.py`. `finding_json_schema()` generates the JSON Schema from the dataclass, so the code and the schema cannot drift.

## Bundle

```
EvidenceBundle { schema, artifacts[], observations[], findings[] }
```

### ArtifactRef: raw evidence, identified by content
`sha256`, `path` (re-readable location), `media_type`, `source_tool`, `collected_at`.

### Observation: what a tool saw
`id`, `artifact` (sha256), `pointer` (RFC 6901 JSON pointer into the artifact), `value` (exactly what was there), `note`.

### Finding: a conclusion
| Field | Notes |
|---|---|
| `id`, `title` | |
| `domain`, `service` | e.g. `entra` / `conditional-access` |
| `source_tool`, `source_check_id` | the tool's own id, verbatim (`MT.1005`, `entra_legacy_authentication_blocked`, `HCA-002`) |
| `resource_id`, `environment`, `observation_point` | what was assessed, where it lives (`synthetic:…`, `tenant:<id>`, `lab:…`), and how it was observed (`microsoft-graph:v1.0 snapshot`) |
| `status` | the tool's verdict: `fail`, `pass`, `manual`, `error`, `skipped`, `not_applicable` |
| `description`, `severity`, `confidence` | severity = impact if true; confidence (0–1) = strength of evidence |
| `collected_at` | |
| `observations[]`, `artifacts[]` | the evidence trail |
| `controls[]` | crosswalk ids: `maester:MT.1006`, `prowler:<CheckID>`, `CIS-4.0_M365:5.2.2.3`, ATT&CK ids |
| `remediation`, `references[]` | |
| `limitations[]`, `next_validation_step` | what this evidence cannot show, and how to confirm it |
| `verification`, `verification_notes[]` | set by the verifier, never by the tool |
| `inferred` | true for conclusions; false only for a direct restatement of an observation |

## Verification states

`reported` (a tool said so) → `corroborated` (independently re-derived from raw evidence) | `refuted` (raw evidence contradicts it) | `insufficient_evidence` (incomplete, unresolvable pointer, artifact changed) → `confirmed` (**human or controlled lab only**; the verifier flags any tool that sets it).

## Verifier (`haven_cyber/verifier.py`)

1. **Completeness**: required fields, enums, confidence range. A `fail` finding needs observations, an artifact and remediation.
2. **Consistency**:
   - the artifact is declared;
   - its bytes still hash to the recorded sha256 (tamper or staleness check);
   - each pointer resolves and equals the recorded value (catches fabricated evidence).
3. **Re-derivation**: separate predicates (not imported from the assessor) recompute each HCA rule from the raw snapshot as `(qualifying policy exists, every in-scope principal covered)`. Upstream checks map to a rule **and a criterion level**:
   - an existence-level check (Prowler `entra_legacy_authentication_blocked`, Maester MT.1006) is compared with *exists*;
   - a coverage-level check (MT.1005) is compared with *covered*.
   - When a check passes at the existence level but coverage fails, the note records a **criterion gap** instead of calling either tool wrong.

## Normalizers

| Source | Module | Mapping highlights |
|---|---|---|
| Haven CA assessor | `tools/entra_ca.py` | native; observations point into the Graph snapshot |
| Maester `TestResults.json` | `normalize/maester.py` | Result Passed/Failed/Error/Investigate/Skipped/NotRun → pass/fail/error/manual/skipped; ResultDetail severity/description; HelpUrl; Skipped carries a "not a pass" limitation |
| Prowler OCSF Detection Finding | `normalize/prowler_ocsf.py` | status_code PASS/FAIL/MANUAL/MUTED; `metadata.event_code` = CheckID; compliance → controls; remediation desc/references; any OCSF class 2004 producer |

## Measured on the fixtures (tests/test_evidence_and_verifier.py)

- **Weak tenant, Haven assessor:** 6 failing rules corroborated, 0 problems.
- **Weak tenant, Maester:** MT.1005 and MT.1007 fails corroborated. The MT.1006 pass is corroborated at existence level, with a criterion-gap note (a Global Administrator is excluded).
- **Weak tenant, Prowler:** 3 findings corroborated; the legacy-auth pass carries a criterion-gap note.
- **Hardened tenant, deliberately wrong Prowler FAIL:** refuted.
- **Tampering:** a tampered snapshot, a fabricated observation value and a failing finding stripped of evidence are each detected.
