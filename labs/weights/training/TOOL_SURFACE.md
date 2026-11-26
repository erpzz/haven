# Training tool-surface binding contract

Haven collection and inference can pass tool definitions to the model **out-of-band** from the chat message list. The current HARE loop does exactly that: the backend receives the messages plus the fixed tool catalogue separately, while the stored record's messages contain the conversation only.

Training those records with tools omitted would render a different prompt from the one used during collection.

This package makes the model-visible tool surface part of the training data contract without changing the already-approved #152 Phase-1 collection notebook.

## Binding receipt

tool_surface.py creates a hash-bound receipt over:

- the exact ordered OpenAI-style function tool array;
- the exact tool names;
- the tool-surface SHA-256;
- a collector/source SHA-256;
- the full catalogue SHA-256;
- fixed vs routed mode;
- for routed mode, the route-receipt SHA-256.

Tool order is intentionally significant because chat templates may render tools in order.

An exact empty tool array is valid and distinct from tools being omitted or unknown.

### Fixed mode

The surface itself is the catalogue. No route receipt is allowed.

This is the appropriate representation for the currently preregistered HARE W1 collector, whose exact tool definitions come from the pinned tool_sft/world.py.

The CPU suite verifies that the repository's current world.py byte hash is exactly the SHA-256 pinned by #152's deps.json and that its four-tool TOOL_SCHEMAS array produces a valid fixed binding.

### Routed mode

A routed surface may be a strict subset of a larger catalogue. The binding requires:

- the full catalogue SHA-256;
- the selected surface SHA-256;
- a route-receipt SHA-256;
- the collector/source SHA-256.

Rows inside one training arm may use different routed subsets, but they may not mix:

- routed and fixed modes;
- different full catalogues;
- different collector/source identities.

One trace may not change surface partway through the trace.

This is the representation required if #131-style routing is adopted for a future collection arm. It does not retroactively claim that the current #152 W1 collector used routing.

## Bound rows

bind_rows() copies the exact tool array and compact binding metadata onto each training row.

It refuses to overwrite pre-existing tool/surface fields. validate_bound_rows() recomputes every hash and rejects:

- modified schemas or descriptions;
- reordered tools without a matching receipt;
- mixed fixed/routed modes;
- mixed catalogues or collectors;
- surface changes inside one trace;
- malformed or duplicate tool definitions.

For the currently approved fixed HARE collector, post-collection training preparation can bind the kept rows to the exact pinned world.TOOL_SCHEMAS surface before tokenization. If collection changes to routed surfaces in the future, the route receipt must be generated during that collection path rather than reconstructed after the fact.

## Tokenization contract

row_encoding.py refuses to tokenize an unbound row.

It passes the exact bound tools array to **every** apply_chat_template call with:

- tokenize=False;
- enable_thinking=False.

The rendering path mirrors the reviewed Qwen/Haven SFT prefix logic, including the Qwythos generation-prefix compatibility fallback.

A true empty surface is passed as tools=[], never tools=None.

If a bound row exceeds max_length, encoding fails closed. It is not silently dropped, because dropping one turn from a multi-turn trace would change the trace objective and could invalidate the episode-weighting contract.

The encoded output carries:

- the exact surface SHA-256;
- the exact surface-receipt SHA-256;
- target-token count.

Those encoded rows are then suitable input to the episode-normalized loss contract in #195.

## Relationship to #152 and #195

#152 remains the approved **collection** candidate and is not modified by this contract.

The intended pre-training sequence is:

1. collect under the approved/frozen harness;
2. seal/audit kept rows as already specified by #123/#152;
3. bind each kept row to the exact tool surface the model saw;
4. validate the whole arm's binding/provenance;
5. tokenize only through row_encoding.py;
6. group encoded rows into episodes and apply #195's episode-normalized loss;
7. only then construct a Phase-3 trainer.

For the current W1 fixed HARE path, the exact pinned world.py tool source is sufficient to reconstruct the fixed catalogue because the collector verifies that pinned dependency before running.

If #131 routing becomes part of an arm before collection, #123 must be amended/frozen as already required and the collection path must emit the route receipts used here.

## Scope

This package performs no inference, training, GPU work, hosted calls, live actions, or M4/reserve access.

A green CPU suite proves the prompt/tool-surface binding and tokenizer contract only. It does not authorize training by itself.
