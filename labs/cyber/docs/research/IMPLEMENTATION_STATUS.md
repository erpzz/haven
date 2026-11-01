# Implementation status (2026-10-31)

Legend: **implemented + tested** (code with passing automated tests), **verified live** (exercised against the real runtime: Qwythos, Hermes, MCP SDK), **experimental**, **planned**.

| Component | Status | Evidence |
|---|---|---|
| Environment audit | done | CYBER_ENVIRONMENT_AUDIT.md (commands on Slink and the Mac) |
| Integration matrix (Phase 1) | done | OPEN_SOURCE_INTEGRATION_MATRIX.md; upstream formats read from source |
| Knowledge corpus: Entra, Azure, Windows/AD, M365, detection, general (25 docs, 111 sections) | implemented + tested | `tests/test_kb.py`: provenance on every item, ranking probes, untrusted wrapper, FTS operator safety, eval-leakage guard |
| Deterministic retrieval (SQLite FTS5/BM25, domain routing, ≤2 sections/doc, staleness) | implemented + tested | same |
| Entra CA assessor HCA-001..010 | implemented + tested | `tests/test_entra_ca.py`; every observation pointer re-resolves |
| Azure RBAC effective-permission evaluator | implemented + tested | `tests/test_registry_and_graph.py::RBACTests`; agrees with the RBAC eval labels |
| Graph read-only collector (`entra.graph.collect`) | implemented + tested on mocks; **not run live** (no tenant) | paging, foreign-nextLink refusal, 429 Retry-After, error mapping, token never in output |
| Maester + Prowler OCSF normalizers | implemented + tested | `tests/test_evidence_and_verifier.py` |
| Evidence schema + independent verifier (completeness, hash, pointer, re-derivation, criterion level) | implemented + tested | same; refutes a wrong FAIL, detects tampering and fabricated evidence |
| Tool registry (schemas, scope, timeouts, rate limits, audit, write refusal) | implemented + tested | `RegistryTests` |
| MCP server (4 tools, mcp 1.x/2.x) | verified live | `scripts/mcp_smoke.py` PASS with mcp 2.3.0; `hermes mcp test haven-cyber`: connected, 4 tools |
| Vertical slice (Phase 8) | implemented + tested; verified live with Qwythos | `tests/test_slice.py` (offline + stub-model live path + bad tool choice contained); live run `results/slice/live-qwythos-nothink-20261031.json` → `grounded_incomplete` (correct findings, no fabrication, but rule ids and references not cited) |
| Evaluation set (55 scenarios, 20 held out, hidden canary-tagged answers) | implemented + tested | `tests/test_eval_set.py`: oracle answers pass; CA and RBAC labels agree with the independent tools |
| Harness A/B/C(/D), deterministic grader, gap report | verified live | thinking-off baseline: A 38/55, B 38/55, C 41/55, with **0 tool calls** in C; 11 of 17 failures are orchestration (see CYBER_CAPABILITY_MATRIX.md) |
| Thinking-on evaluation | verified live, complete | A 42/55, B 45/55, C 49/55 with 0 false positives in B/C, but only 1 tool call in 55 and ~12.5× latency (results/eval/qwythos-think-v1) |
| LoRA research (Phase 6) | investigated; **no pilot run by this session** | LORA_RESEARCH_PLAN.md: 9B QLoRA blocked on the 8 GB card (measured); Kaggle lane in use by the forge Qwythos run; dataset generator agreed with the forge session |
| Agent-reliability training data | planned (forge session) | handoff sent with rules: grader-verified, fresh identity space, canary filter |
| ATT&CK v20.0 technique table + SigmaHQ cloud rule index (metadata only) + finding→technique→rule mapping (`detection.map`) | implemented + tested | `tests/test_attack.py`: every technique id in the corpus, eval and mappings is current in v20.0; Sigma index carries no detection logic; HCA-004 surfaces a real detection gap (no SigmaHQ cloud rule for AiTM session theft) |
| Retrieval evaluation (hand-labelled relevant docs, recall@3) + opt-in artifact query expansion | implemented + tested; **off by default** | plain 48/55, expanded 50/55 (dev signal: labels written after seeing scenarios); frozen v1 harness unchanged |
| Maester 3.0 results (schema 2.1 typed fields) | implemented + tested | found while checking upstream docs; 2.x still accepted |
| Live tenant (Graph, Resource Graph, Azure MCP Server) | planned; needs an authorized lab tenant | |
| Upstream contributions | checked against existing issues/PRs; none filed (posting needs owner approval) | Maester schema already documented upstream; Hermes `mcp add --yes` already has PRs #31979 / #147106 |
| Three-way adapter comparison (base vs agent adapter vs secpatch adapter) | pre-registered and tooled; waiting for the thinking-on baseline and both GGUFs | ADAPTER_SELECTION_PREREGISTRATION.md, `results/compare/2026-10-31/` |

## Reproduce

```bash
cd labs/cyber
python3 -m unittest discover -s tests                                   # 46 tests, ~1.5 s, stdlib only
python3 -m haven_cyber.slice --offline                                  # outcome=ok
PYTHONPATH=. <venv-with-mcp>/bin/python scripts/mcp_smoke.py             # MCP SMOKE PASS
# Model runs (Slink): llama-server -m Qwythos-9B-v2-MTP-Q4_K_M.gguf --port 8095 --jinja -c 24576 -np 1 -b 2048 -ub 2048
scripts/run_eval_slink.sh                                               # A/B/C thinking off, then on
python3 -m haven_cyber.eval.report runs/eval/qwythos-nothink-v1 runs/eval/qwythos-think-v1
```

## Preserved services

No existing Haven service was stopped or modified. Two transient user units were added on Slink: `haven-cyber-qwythos` (llama-server :8095) and `haven-cyber-eval`. Both are stoppable, and the eval resumes where it stopped. On the Mac, Hermes gained one MCP server entry (`haven-cyber`); no inference ran there.
