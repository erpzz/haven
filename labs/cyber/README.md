# labs/cyber: cyber intelligence for Qwythos and Hermes

Knowledge, read-only security tools, a common evidence model with an independent verifier, and an evaluation harness that measures what Qwythos-9B-v2 can do alone, with retrieval, with tools and (next) with a LoRA adapter.

Start with [docs/research/IMPLEMENTATION_STATUS.md](docs/research/IMPLEMENTATION_STATUS.md).

## Requirements

- Python ≥ 3.11, standard library only, for everything except the MCP server.
- The MCP server needs the `mcp` SDK (1.x or 2.x) in any venv.
- Model runs need an OpenAI-compatible endpoint, e.g. llama.cpp `llama-server --jinja`.

## Commands (run from `labs/cyber`)

```bash
python3 -m unittest discover -s tests                     # 39 tests
python3 -m haven_cyber.kb build                           # index corpus/ → runs/kb.sqlite
python3 -m haven_cyber.kb search "report-only conditional access" --domain entra
python3 -m haven_cyber.slice --offline \
  --import maester:fixtures/tool_outputs/maester-weak.json \
  --import prowler-ocsf:fixtures/tool_outputs/prowler-weak.ocsf.json      # end-to-end slice, no model
python3 -m haven_cyber.slice --endpoint http://127.0.0.1:8095/v1 --model qwythos   # same, live model
PYTHONPATH=. <venv>/bin/python scripts/mcp_smoke.py       # MCP server end to end
python3 -m haven_cyber.eval.harness --endpoint http://127.0.0.1:8095/v1 --model qwythos \
  --conditions A,B,C --out runs/eval/<name> [--think]     # capability evaluation
python3 -m haven_cyber.eval.report runs/eval/<name> > report.md
python3 fixtures/tenants/build.py && python3 fixtures/tool_outputs/build.py && python3 eval/build_scenarios.py   # regenerate data
```

Hermes: `echo Y | hermes mcp add haven-cyber --command <venv>/bin/python --env PYTHONPATH=$PWD --args -m haven_cyber.mcp_server`

## Layout

| Path | What |
|---|---|
| `corpus/` | versioned knowledge (Entra, Azure, detection, general) with provenance front matter |
| `haven_cyber/kb.py` | FTS5/BM25 index and cited, untrusted-data retrieval |
| `haven_cyber/tools/` | `entra_ca` (HCA-001..010), `azure_rbac`, `graph` (gated read-only collector), `registry` |
| `haven_cyber/normalize/` | Maester `TestResults.json`, Prowler OCSF |
| `haven_cyber/evidence.py`, `verifier.py` | evidence schema and independent verifier |
| `haven_cyber/mcp_server.py` | four-tool MCP server |
| `haven_cyber/slice.py` | the end-to-end vertical slice |
| `haven_cyber/eval/` | harness (A/B/C/D), grader, tool environment, report |
| `eval/` | scenario builder, scenarios (visible) and answers (hidden, canary-tagged) |
| `fixtures/` | synthetic tenants and tool outputs, with their generators |
| `results/` | committed evaluation summaries and reports |
| `docs/research/` | audit, matrix, architecture, designs, capability matrix, LoRA plan, provenance, upstream plan, status |

All tenant data is synthetic (`contoso.example`). Nothing here needs, or contains, credentials.
