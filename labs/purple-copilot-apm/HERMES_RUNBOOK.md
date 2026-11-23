# Purple Copilot in Hermes Agent

Haven uses [Hermes Agent](https://github.com/NousResearch/hermes-agent) as its agent runtime. This lab adds to Hermes rather than maintaining its own loop. A project plugin in `.hermes/plugins/purple-copilot` adds three read-only Tier Zero review tools. The plugin also moves the HARE assurance layers onto Hermes's own hooks:

| Layer | Hermes hook | Behaviour |
| --- | --- | --- |
| Turn context | `pre_llm_call` | Starts a fresh evidence record for the turn. In strict mode, it adds the citation rules to the user message. |
| Gateway | `pre_tool_call` | Returns `{"action": "block"}` with a reason the model sees. It blocks: any non-Purple tool in strict mode; wrong or extra arguments; an unknown platform; a principal that holds no recorded Tier Zero edge; a repeated read; more than six reads in a turn. |
| Evidence | `post_tool_call` | Records each Purple tool result for the turn. |
| Verifier | `transform_llm_output` | A final answer must cite at least one returned `[T0-…]`, `[P-…]` or `[F-…]` token, and every citation-shaped token must be real. It may use only integers the tools returned as values, including counts written as words, and only principal names they contained. In a sentence that names a principal, each number must come from that principal's own evidence. Quoted timestamps are exempt. Otherwise Hermes shows a deterministic summary of the retrieved evidence instead. That summary names the failure categories but never repeats the rejected values. |

Every reviewed turn appends a private receipt to `$APM_STATE/agent-reviews.jsonl`. A receipt records the question, reads, blocked calls, verifier findings and whether the answer was replaced.

Hermes's `pre_verify` hook fires only after file edits, so a read-only review relies on the deterministic fallback rather than a correction turn.

## Tools

| Tool | Returns |
| --- | --- |
| `purple_tier_zero_overview(platform)` | Headline exposure and the ten highest-priority non-Tier Zero principals for `ad` or `entra`. |
| `purple_tier_zero_principal(platform, principal)` | Every control edge one principal holds, its state and the identities able to gain it. |
| `purple_tier_zero_changes(platform)` | New, changed and missing edges at the latest snapshot. A missing edge keeps its last observed labels. |

The tools read the local history written by `python3 -m apm.tier_zero` ([TIER_ZERO.md](TIER_ZERO.md)). They never contact CE, the directory or the network.

## Run it

Use Hermes v2026.9.24, the release Haven already pins. Install it separately. Then point a Hermes home at a local OpenAI-compatible model server, for example llama.cpp started with `--jinja`, and enable the plugin. Hermes hides plugin tools behind its Tool Search bridge by default. Turn that off so the review tools are offered to the model directly.

```yaml
# $HERMES_HOME/config.yaml
model:
  provider: custom
  base_url: http://127.0.0.1:8080/v1
  default: local-model
plugins:
  enabled:
    - purple-copilot
tools:
  tool_search:
    enabled: "off"
```

Run from this directory so Hermes discovers the project plugin and loads `HERMES.md`, the short review brief it adds to the system prompt as project context. Keep human documentation out of that file; Hermes sends all of it to the model.

```sh
export HERMES_ENABLE_PROJECT_PLUGINS=1 APM_STATE="$HOME/.local/state/purple-copilot-apm"
hermes chat --toolsets purple-copilot --provider custom --model local-model \
  -q "Which non-Tier Zero principals can take over Tier Zero in AD, and what should I fix first?"
```

Hermes requires a model context of at least 64,000 tokens. On a 7 GB CPU host, the 4B at that context needs about 6 GB with an 8-bit KV cache (`-c 65536 -np 1 -ctk q8_0 -ctv q8_0`). The review tools read only the local history, so stop CE (`./ops/ce.sh down`) during model runs on a small host.

Strict mode is the default. Set `PURPLE_REVIEW_STRICT=0` to let Hermes use its other tools alongside the review tools; the gateway then checks only the Purple tools. To validate a copied install, set `PURPLE_COPILOT_LAB` to this directory and run `hermes plugins doctor "$PWD/.hermes/plugins/purple-copilot" --ci`.

## Executed evidence, 2026-11-22 UTC

**Plugin doctor.** `hermes plugins doctor` on Hermes v2026.9.24 (`f97608f1`) reports successful discovery, manifest parsing, import and registration, with 3 tools and 4 hooks.

**Integration.** `tests/hermes_review.py` drives the real `hermes chat --oneshot` loop against a scripted OpenAI-compatible model, so each property is exercised deterministically. The snapshot is the live history from the sample lab. All five scenarios passed in 23 model requests:

| Scenario | Scripted model behaviour | Observed |
| --- | --- | --- |
| Grounded | Reads the AD overview and answers with its citations and counts | Answer shown unchanged |
| Fabricated | Claims 412 principals, an invented principal and an invented finding citation | All three detected. Answer replaced by the evidence summary, which contains none of the fabricated values |
| Terminal | Tries `terminal` to create a canary file, then reads the overview | Call blocked, canary absent, grounded answer shown |
| Duplicate | Reads the overview twice | Second read blocked |
| Unknown principal | Asks for a principal absent from the findings | Read blocked before execution |

**Unit tests.** `tests/test_review.py` covers the tools, gateway, verifier and fallback, including the property that the fallback passes its own verifier. The suite has 43 tests in total.

**Real model.** Six analyst questions were asked of Qwen3.5-4B on CPU, before and after these refinements. The details are in [evidence/hermes-live](evidence/hermes-live/README.md).
- Tool selection was reliable.
- Edge-direction errors stopped once each edge carried a deterministic `meaning` sentence.
- The verifier replaced 3 of 6 answers in each arm.
- In each arm, 2 of 6 answers still showed wrong content: misread counts or edge semantics.
- That led to the stricter checks now in place:
  - numbers in a sentence must belong to the principal it names;
  - spelled-out counts are checked;
  - change totals are stated in a rendered sentence;
  - quoted timestamps are exempt from number checks.
- Re-applied to the same answers, the final verifier replaces all of those wrong answers except one, whose errors are semantic rather than lexical.

## Limits

The scripted model proves the enforcement path, and the six-question real-model run is descriptive, not a qualification. Verification is lexical: it confirms that citations, integers and principal names came from this turn's evidence. It cannot confirm that a sentence uses them correctly, so analyst review remains part of the workflow. Findings describe exposure on synthetic samples, not compromise.
