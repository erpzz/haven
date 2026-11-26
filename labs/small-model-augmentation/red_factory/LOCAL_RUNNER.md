# Loopback local-model runner

This stacked package makes the Local Red Factory runnable against the actual local 4B model endpoint without granting it execution authority.

## Execution contract

The runner accepts only a loopback OpenAI-compatible base URL:

- scheme must be `http`;
- host must be `127.0.0.1`, `localhost`, or `::1`;
- an explicit port is required;
- path must be exactly `/v1`;
- credentials, query strings, fragments, and non-loopback hosts are rejected.

It sends a normal `/v1/chat/completions` request with thinking disabled and asks the model for one exact JSON transcript:

- `schema`
- `case_id`
- `decision`
- `claim_ids`
- `tool_calls`

The model-facing case packet contains the synthetic prompt, trusted/untrusted evidence, visible tool names, and call budgets. It does **not** contain the expected decision, expected claim set, hidden target fingerprints, or grader result.

## No tool execution

`tool_calls` in this adapter are proposals only.

The runner never dispatches them, never opens a shell, and never calls Haven/Haven Cyber. HRF scores the proposed tool name, target arguments, budgets, duplicates, and canary attempts deterministically.

This makes the lane safe for development probing of a raw local model. Real Hermes tool-dispatch behavior remains a later integration layer under the existing #127/#129/#130/#131 controls.

## Privacy / receipts

By default the returned result stores:

- case/family;
- model alias and loopback endpoint;
- request SHA-256;
- output SHA-256;
- latency;
- bounded error string;
- deterministic HRF score;
- result SHA-256.

Raw model text and parsed transcript are omitted unless `retain_raw=True` is explicitly selected. An optional local API key is sent only in the Authorization header and is never copied into the result object.

Suite runs bind the suite hash, model/endpoint/settings, per-case result hashes, and deterministic HRF summary.

## Limits

- Loopback does not prove the process behind the port is the intended model. Product-quality use must compose #127 model/context/process admission rather than relying on URL locality.
- This direct runner tests model planning under adversarial evidence, not actual Hermes MCP execution.
- A later Hermes adapter should capture the actual first model-visible tool surface and real attempted/blocked calls, then translate them into the same HRF transcript schema.
- No network target discovery, live host scanning, exploit execution, credentials, persistence, lateral movement, destructive action, reserve data, training, promotion, or deployment is introduced.

## Qualification

CI uses a scripted loopback OpenAI-compatible server and proves:

- non-loopback endpoint refusal;
- expected-answer fields are absent from the request;
- valid structured responses score correctly;
- `<think>` blocks may be discarded but trailing prose is rejected;
- canary and wrong-target proposals score as failures and are not executed;
- duplicate-read requires one exact synthetic read proposal;
- malformed output becomes a failed bound receipt;
- API keys are not persisted;
- complete suite runs produce bound summaries.
