# Haven NIGHT-01 laboratory

**TEST DOUBLE / NOT LIVE AI. All records are synthetic.** This CLI demonstrates scoped retrieval, grounded quotation, inert draft proposals and durable outcome bookkeeping. It does not interpret questions with a model. Explicit topic metadata selects fixtures; the deterministic backend quotes them. Selecting TEST_USER_A/B injects a test identity, not real authentication or consent.

Use Ubuntu 24.04 and Python 3.12. No dependency installation, server, certificates, accounts or network are needed. From this `lab/` directory:

```sh
python3.12 -B -m unittest discover -s tests -p 'test_n1.py' -v
python3.12 -B -m haven_lab init
```

Copy the printed new run path into the next command. Each init creates a separate directory inside `lab/runtime/` and never overwrites a run.

```sh
python3.12 -B -m haven_lab ask --run '<printed-run-path>' --test-principal TEST_USER_A
python3.12 -B -m haven_lab read --run '<printed-run-path>' --request-id '<printed-request-UUID>'
python3.12 -B -m haven_lab export --run '<printed-run-path>' --request-id '<printed-request-UUID>' --format html > transcript.html
python3.12 -B -m haven_lab ask --run '<printed-run-path>' --kind DRAFT_NOTE
python3.12 -B -m haven_lab revoke --run '<printed-run-path>' --test-principal TEST_USER_B --evidence-id SHARED_DECISION --recipient TEST_USER_A
```

`read` and `export` are read-only. Successful matching request reuse returns the saved outcome without another model attempt; changed reuse conflicts. Interrupted RUNNING jobs remain OUTCOME_UNKNOWN without automatic replay. A timeout/backend exception becomes UNAVAILABLE, never success. At most two backend attempts; invalid output is not retried. Exit 0 means an answer/inert proposal (or init/revoke command) completed; exit 3 means a stored unavailable/rejected/withheld outcome; exit 2 means input/storage/access error.

The SQLite schema is version 1, with an application identifier, explicit transactions, DELETE/FULL/foreign_keys and bounded busy timeout on each writer. Reads use mode=ro and query_only. Request creation commits before model execution, each attempt is recorded, and a terminal result commits before delivery. A process stop during work leaves a durable incomplete record: reading reports unknown. Unsupported schema versions and DB failures fail closed; missing databases are not created by reads. This is prototype process/restart persistence, not qualified whole-PC power-loss durability.

Grants are purpose-specific, explicit and versioned. Selection, pre-call, pre-delivery and cached reads recheck them. Revocation withholds derived content; it does not erase retained synthetic audit history. Context classes and original times remain visible. Source instructions remain quoted data. Exact quote validation is deliberately narrow grounding, not a general truth/semantic validator. The HTML transcript escapes all source data.

ModelBackend is a replaceable code boundary. Only deterministic-fixture-quotes v1 is selectable through the CLI. Trusted test code injects malicious/failing fixtures; there is no dynamic plugin/provider option. No external network, real account, device, printer or physical executor exists. Application tests and Python audit hooks do NOT establish OS-level egress containment or privacy from the host administrator. No live AI quality, cost, latency or device qualification is claimed.

Original draft schemas remain immutable in ../haven-astra-starter. See CONTRACT_MAPPING.json for the local mapping and limits. Runtime databases and raw attempt records stay local under runtime/ and are excluded from review bundles. A transcript is a snapshot; an already exported file cannot be retroactively recalled after grant revocation. It contains only synthetic data here.

## N2 synthetic engineering notebook

N1 must pass before N2. The shipped `outputs/N1_GATE.json` records the executed N1 log and source hashes. `python3.12 -B -m haven_lab.notebook` verifies those hashes before creating a new `outputs/n2-<UUID>/` with original inputs, inert dimension revisions, all scores/checks and a report. Changes to qualified N1 source require rerunning N1 and explicitly recording a new reviewed gate; no automatic pass is inferred from changed files.

```sh
python3.12 -B run_checks.py n1
python3.12 -B run_checks.py n2
python3.12 -B -m haven_lab.notebook
```

The fixed synthetic objective and a separately coded arithmetic checker run on no more than five candidates. Both source identities are retained. Candidate rejection does not disappear because its score is low. The chosen result is PROPOSE_NEXT_FOR_REVIEW, never physical ACCEPTED. Missing, rejected or mismatched evaluation cannot promote a candidate, and even a passing synthetic evaluation cannot enable fabrication. This is no CAD engine, structural simulation, sensor measurement, fabrication, AI discovery or autonomous engineering qualification.
