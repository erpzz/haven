# Haven Intelligence Bakeoff

Status: **RUNNABLE HARNESS ADDED; REAL MODEL/HERMES RESULTS REQUIRE THE WINDOWS HOST.**

This package executes the scoped R02-P04/P05 bakeoff authorized in issue #27. It compares two independent axes:

1. **Runtime:** Haven thin tool loop vs Hermes Agent.
2. **Model:** the same Haven-style tasks across local candidate models.

The harness uses only synthetic identities/data and proposal-only tools. It must never be pointed at employer data, private household records, real devices, or physical actuators.

## Why two axes

Do not compare "Hermes + Sol" against "thin coordinator + Qwen" and call that a runtime result. Run:
- same model + same fixtures across runtimes first;
- then compare models on one frozen runtime;
- then optionally compare best-qualified configurations.

## Quick local run: thin coordinator

Point directly at an OpenAI-compatible local inference endpoint (for example the llama.cpp server owned by Model Lab):

```powershell
cd labs\intelligence-bakeoff
python bakeoff.py --base-url http://127.0.0.1:8080/v1 --model YOUR_MODEL_ID --label qwen35-4b --repetitions 3
python score.py runs\qwen35-4b.jsonl
```

No model is downloaded by this harness. Use Model Lab or your chosen engine to load the candidate first.

On Windows, `RUN-WINDOWS.ps1` wraps validation, thin-runtime runs, Hermes plugin validation, repetitions, and scoring without installing or authenticating anything automatically.

## Hermes run

Hermes is pinned for this experiment to stable release **v2026.9.24**. Install/review it separately, then explicitly enable this trusted project plugin:

```powershell
$env:HERMES_ENABLE_PROJECT_PLUGINS="true"
$env:HAVEN_BAKEOFF_TRACE="$PWD\runs\hermes-tools.jsonl"
hermes plugins doctor .\hermes-plugin --ci
python hermes_adapter.py --provider openai-codex --model ACCOUNT_VISIBLE_SOL --label hermes-sol --repetitions 3
```

For a local model, configure Hermes to the same OpenAI-compatible endpoint/model and run the adapter with that provider/model. `hermes_adapter.py` consumes Hermes' supported `--format stream-json` output; it does not scrape terminal decorations.

## ChatGPT / Claude subscription bridges

See [SUBSCRIPTION_BRIDGES_20261005.md](SUBSCRIPTION_BRIDGES_20261005.md).

Short version:
- OpenAI now has an official open-source **Sign in with ChatGPT** flow that can let eligible Plus/Pro users authorize Responses API usage from a local OSS app with OAuth rather than an API key.
- Codex CLI/app-server and Hermes' `openai-codex` provider are additional ChatGPT-plan paths.
- Claude Pro/Max officially includes Claude Code. A bounded local worker can delegate a job to the official Claude Code CLI. Treat general third-party reuse of Claude consumer OAuth tokens as unsupported unless Anthropic explicitly permits it; do not copy/scrape Claude credentials into unrelated clients.
- Direct OpenAI/Anthropic APIs remain separate metered billing paths.

## Candidate set

See `candidates.json`. Initial frozen local set:
- Qwen3.5 4B (champion)
- Ministral 3 3B Instruct
- Phi-4 Mini Instruct 3.8B
- NVIDIA Nemotron 3 Nano 4B
- IBM Granite 4 H-Tiny
- Qwen3.5 9B
- SmolLM3 3B / Gemma 3 4B / Llama 3.2 3B as architecture/legacy baselines
- one RAM-assisted coding/generalist stretch candidate only after fit review

A candidate is **not** promoted into Model Lab's checksum-pinned catalog by appearing here.

## Metrics

Each task records:
- selected/called tools;
- tool arguments and synthetic results;
- final answer;
- first-attempt completion;
- elapsed time and provider usage when exposed;
- mechanical privacy/authority/factual checks.

`score.py` reports:
- task pass rate;
- tool-selection pass rate;
- forbidden-tool violations;
- required/forbidden answer-marker checks;
- parse/transport failures.

Keep human usefulness and deeper coding quality as separate review dimensions; do not hide a safety failure inside an average score.

## Real execution gate

The repository/chat environment cannot access the operator's RTX 2070 Super. Therefore:
- fixture/unit execution here can validate the harness;
- local-model latency/VRAM/quality claims require a run on that PC;
- Hermes installation/authentication requires the operator's machine/account;
- subscription/API credentials are never committed.

Run receipts belong in `runs/` locally and are gitignored by the repository's normal local-evidence policy unless a sanitized result is deliberately published.
