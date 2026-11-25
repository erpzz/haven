# Small-model augmentation — model admission and runtime observation

Workstream: [#126](https://github.com/erpzz/haven/issues/126). Base: `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; Claude retains integration/merge ownership.

## Inventory and integration summary

Do not create parallel stacks. Existing work includes Cyber evidence and registry (#105, `69f7ae3`), Forge (#106, `2dd9c4b`), Hermes operator (#107, `a643257`), HARE (#115, `7f5af0d`), deterministic queries (#118), Purple integration (#122, `f701cd7`), and weight experiments (#123–125). The targeted source review included #122's `labs/purple-copilot-apm/ops/review.sh`, HERMES_RUNBOOK.md and apm/review.py. The launcher currently accepts an already-running server from a health response; health alone is not model identity. The runbook specifies a 64,000-token Hermes minimum. No active integration files are changed here.

The runtime observer is written against the exact llama.cpp revision used by #122, `b11146`: its server documentation says `GET /v1/models` returns the loaded model and honors `--alias`, and `GET /props` exposes `default_generation_settings.n_ctx`. Source: https://raw.githubusercontent.com/ggml-org/llama.cpp/b11146/tools/server/README.md (sections GET /props and GET /v1/models).

## Admission contract

`preflight.py` accepts a JSON document via stdin, provided by a trusted launcher, with exactly four keys: expected_model (operator selection), requested_model (effective request configuration), observed_model_ids (inventory from the actual selected single-model server), observed_context_tokens (effective observed context, not the advertised training maximum). Exact case-sensitive match is required; singleton inventory only; missing or malformed observations block. CLI exits 0 on pass or 2 on block, returning fixed diagnostic codes without echoing input. The minimum is pinned to the documented Hermes version. This is deliberately restricted to single-model server configurations; a router/multi-model backend needs a different reviewed contract.

`observe_llama.py` supplies runtime observations without an LLM:
- only an explicit `http://127.0.0.1:PORT` root is accepted; localhost names, alternate numeric loopback forms, credentials, paths, query strings, fragments, TLS and non-loopback addresses are rejected;
- environment proxies are disabled and redirects are never followed;
- `/v1/models`, `/props`, then `/v1/models` are read with a 2-second timeout and a 64 KiB response cap;
- JSON uses strict duplicate-key rejection; model ids and `n_ctx` are schema-checked;
- a changed model inventory during the check blocks;
- the observed values are passed to the offline preflight. A pass sets `live_endpoint_verified=true`; this means the targeted local endpoints responded consistently and passed the contract, not that model weights were authenticated.

Example against a dedicated synthetic/local server:
```sh
python3 observe_llama.py \
  --expected-model fixture-model-9b \
  --requested-model fixture-model-9b \
  --base-url http://127.0.0.1:8091
```

## Second-pass test receipt

Linux CPU sandbox, Python standard library, no model inference/GPU. Exact committed executable/test bytes were reconstructed and hash-checked, then:
```sh
python3 -m py_compile *.py
HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9 \
  python3 -m unittest -v
```
Observed: **27/27 test methods pass in 10.418 s**.

Git blob IDs of tested bytes:
- `preflight.py`: `c979fcf49a281c87ac18023a71a6842aad142670`
- `test_preflight.py`: `eb9baf988486af23f3a48431ac941e72b33df099`
- `test_preflight_review.py`: `16c131bba10e3db71338dc0a1d33d89c051b4e81`
- `observe_llama.py`: `bcaa1577a0df14713570eb01be2ec7a8c82f0288`
- `test_observe_llama.py`: `acb32d97c3f2716464797ea16c13947ed7534598`

Coverage includes the 4,224-case offline decision matrix plus scripted HTTP tests for valid admission; wrong model; insufficient context; requested-model mismatch; non-loopback and URL tricks; redirect refusal; proxy-environment independence; bounded responses with and without Content-Length; duplicate/malformed JSON; schema failures; server change during check; dead port; duplicate/multiple model ids; context boundary; CLI exit behavior and redaction. These are producer tests, not independent qualification.

## Remaining blockers / next gate

This code still does **not** establish cryptographic weight identity, authenticate a pre-existing local server, bind a check permanently to later requests, prevent a server/process swap after validation, or modify #122's launcher. A same-user local process can claim the expected alias. The intended product gate therefore remains incomplete until the integration owner wires the observer into the launcher, preserves the existing hash-checked model-file launch path, fails closed for an unexpected pre-existing server, and tests the resulting Hermes invocation on the named Mac. Tool/MCP visibility is a separate next work package.

No private transcripts, credentials, real host paths, reserve cases or training data are published. No deployment, M4 qualification or self-merge is claimed.
