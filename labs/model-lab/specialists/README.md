# Specialist acceptance workflows

Small, bounded checks that a specialist model does useful Haven work. They are not a
benchmark campaign, and they never touch routing, engines or the GPU.

## d1-2B routing acceptance (`systemone_acceptance.py`)

Can LiquidAI d1-2B, zero-shot, route the 36 real Haven pull-request titles in
`labs/engineer/router_lab/data/` as well as that lab's keyword rules, and does its
confidence flag its own mistakes?

The question wording was frozen in commit `15b8dfc` before any inference
(`question-hash` prints `753ee257…3500`). The dataset hash is enforced.

### Result (2026-10-30, off Slink)

Run on a cloud CPU container (2 vCPU, 8 GB) with llama.cpp b11946 (`8ca4060`, CPU build) and
`d1-2B-Q8_0.gguf` (sha256 `073313d9…6738c`, revision `63be75e6`). **Not Slink.**

| | d1-2B zero-shot | keyword rules | #83 trained head |
|---|---|---|---|
| all 36 | 28 | 29 | — |
| chronological test (8) | 7 | 7 | 6 |
| wrong answers committed at confidence ≥ 0.55 | 4 (4 abstained, all errors) | 7 (cannot abstain) | — |

- Discordant pairs: 0 vs 1, sign test p = 1.0. **No difference in accuracy is shown.** The
  observation worth trialing is that confidence separated errors. Both methods fail on the
  same ambiguous orchestration-versus-inference titles.
- The rule keywords were written with this dataset in view, so the rules are not an unseen
  baseline. d1 saw none of it.
- 5,769 input tokens and 0 output tokens over 36 calls. Median 4.4 s per call on 2 CPU
  threads, 1.9 GB resident. GPU latency was not measured.

Receipt: `results/d1-2b-route-acceptance-20261030.json`.

### Reproduce

    llama-server -m d1-2B-Q8_0.gguf --host 127.0.0.1 --port 18961 \
        --api-key-file KEYFILE -b 8192 -ub 8192 -c 16384        # llama.cpp b11945 or newer
    python3 labs/model-lab/specialists/systemone_acceptance.py run \
        --base-url http://127.0.0.1:18961 --api-key-file KEYFILE \
        --data labs/engineer/router_lab/data/haven_pr_routes_20261027.jsonl \
        --out results.json --environment "where this ran"

## LFM3-1.7B tool-call smoke (`results/lfm3-1.7b-toolcall-smoke-20261030.json`)

One prompt checked that LFM3-1.7B loads on b11946 and that llama.cpp parses its XML tool
call into an OpenAI `tool_calls` entry. It called `get_device_state(garage-heater)` rather
than the approval-gated setter, at 11 tok/s decode on 2 CPU threads. This is runtime
compatibility only, not a quality result.

## Not done

- **Coding workflow:** skipped. d1 cannot generate text. LFM3-1.7B's own card advises
  against agentic coding, and a 2-core container is no place to judge a coding agent.
- **Slink:** nothing ran on Slink. Its pinned b11146 cannot load either model, and no
  model-ownership window was granted.
