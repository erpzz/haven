# Bringing up the first metered lane (Cloudflare Workers AI)

Run this **on Slink**, where the Model Lab's enrollment directory lives. It does not
work from a cloud session or the admin Mac: the relay must serve its socket into the
Lab's own private providers directory.

Three steps here are deliberately yours and cannot be automated away:

1. **Minting the provider token.** It lives in your Cloudflare account.
2. **Placing it.** It must never transit a chat, an issue or a commit. Steps 2–3
   below read it from your shell, and the relay reads it from an owner-private file
   at dispatch. The whole reason the relay exists is that the key stays on this host.
3. **Writing the enrollment file.** `providers.py` treats enrollment as administrator
   input, not model output; nothing in this repository authors one, and `fleet.py`
   marks discovered hosts `DISCOVERED_NOT_ENROLLED` for the same reason. The JSON is
   pre-filled below so only `key` and `socket_path` are left to you.

Everything else — relay, validation, verification, receipts, tests — is already on
PR #87.

---

## 1. Mint a least-privilege Cloudflare token

Cloudflare dashboard → My Profile → API Tokens → Create Token → Custom token.

- Permission: **Account → Workers AI → Read**. Nothing else. Do not use a Global API
  Key, and do not grant Zone or DNS scopes — this lane only runs inference.
- Account Resources: the single account you want billed-at-zero.
- Note the **Account ID** from the dashboard sidebar (it is not secret, but the relay
  reads it from the same private directory to keep one source of truth).

Confirm on the live pricing page that the Workers **Free** plan still has no overage
path — that requests fail rather than bill past the daily allocation. The evidence
block below records that clause, but I read it through a documentation mirror rather
than the live page, so treat it as unconfirmed until you have looked. If Cloudflare
has since introduced metered overage on Free, the correct `cost_boundary` becomes
`PROVIDER_SOFT_ALERT` or `CLIENT_SIDE_ONLY`, not `NOT_CHARGEABLE`, and the lane should
stay explicit-only regardless.

## 2. Place the credential and account id

```sh
export HAVEN_METERED_STATE="$HOME/.haven/metered"
mkdir -p "$HAVEN_METERED_STATE/keys" && chmod 700 "$HAVEN_METERED_STATE" "$HAVEN_METERED_STATE/keys"

# Paste the token at the prompt; -s keeps it out of your shell history.
read -rs CF_TOKEN && printf '%s' "$CF_TOKEN" > "$HAVEN_METERED_STATE/keys/cf-workers-ai"
read -r  CF_ACCOUNT && printf '%s' "$CF_ACCOUNT" > "$HAVEN_METERED_STATE/keys/cf-account"
unset CF_TOKEN CF_ACCOUNT
chmod 600 "$HAVEN_METERED_STATE/keys/"*
```

The relay refuses to read any key file that is group- or world-readable.

## 3. Generate the Lab-facing bearer key

This is a *different* secret from the Cloudflare token: it is what the Lab presents to
the relay over the private socket, and it is the value that goes in the enrollment
file's `key` field.

```sh
LAB_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(36))')"
printf '%s' "$LAB_KEY" > "$HAVEN_METERED_STATE/keys/cf-workers-ai.lab"
chmod 600 "$HAVEN_METERED_STATE/keys/cf-workers-ai.lab"
echo "$LAB_KEY"   # paste into the enrollment file below, then clear your scrollback
```

## 4. Configure the lane

```sh
python3 ops/haven-core/metered-relay.py configure \
  --lane cf-workers-ai \
  --vendor cloudflare \
  --model '@cf/meta/llama-3.1-8b-instruct' \
  --key-ref cf-workers-ai \
  --account-ref cf-account \
  --cost-boundary NOT_CHARGEABLE
```

`configure` records the lane for the relay. It deliberately does **not** write the Lab
enrollment file, and says so in its output.

## 5. Verify — this produces the real authenticated receipt

```sh
python3 ops/haven-core/metered-relay.py verify --lane cf-workers-ai
```

It prompts before sending, because on Cloudflare this consumes a few Neurons of
today's allocation (on Groq the equivalent probe is a free model listing and spends
nothing). Pass `--yes` to skip the prompt in a script.

A `VERIFIED` outcome is the first genuinely authenticated Haven receipt for this lane:
it records the route class, the cost boundary, the HTTP status and any allowance
headers the provider returned, and it is written with `simulated: false`. It refuses to
write a receipt that contains the credential. A refusal is classified rather than
retried — `REFUSED_429` (rate-limited or allowance exhausted), `REFUSED_402`/`403`
(outside the allowance or not permitted on this plan), `REFUSED_401` (credential
rejected). Receipts append to `$HAVEN_METERED_STATE/requests.jsonl`.

**Do not continue past a non-`VERIFIED` outcome.** Enrolling a lane that cannot
authenticate just moves the failure into the Lab.

## 6. Write the enrollment file

Into the Lab's private providers directory (the same directory
`cloud-worker.py`'s preflight prints — typically `<lab data dir>/providers/`), as
`cf-workers-ai.json`, mode `0600`, owned by the Lab user.

Fill **only** `key` (step 3's value) and `socket_path` (step 7's socket).

```json
{
  "id": "cf-workers-ai",
  "label": "Metered · Workers AI",
  "node_id": "slink",
  "base": "http://127.0.0.1:8893/v1",
  "socket_path": "<LAB_PROVIDERS_DIR>/cf-workers-ai.sock",
  "key": "<LAB_KEY from step 3>",
  "model": "@cf/meta/llama-3.1-8b-instruct",
  "display_model": "Llama 3.1 8B · Workers AI",
  "kind": "metered",
  "compute": "hosted",
  "route_class": "CLOUDFLARE_WORKERS_AI_FREE",
  "egress": "METERED_FREE_ALLOWANCE",
  "cost_boundary": "NOT_CHARGEABLE",
  "eligibility_evidence": {
    "doc_url": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
    "clause": "free daily Neuron allocation; on Workers Free, over-limit operations fail rather than bill",
    "retrieved": "2026-10-28"
  },
  "max_context_tokens": 8192,
  "trust": "OWNER_ENROLLED_SSH",
  "allowed_roles": ["admin"],
  "enrolled_at": 0
}
```

Set `enrolled_at` to the current epoch seconds (`date +%s`). `Registry.reload` validates
every field and rejects the row outright if the egress, route class, cost boundary or
evidence is wrong — including a non-https evidence URL or a malformed date — so a typo
fails closed rather than enrolling something unintended.

If you could not confirm the Free-plan clause in step 1, change `cost_boundary` to match
what you did confirm. It is surfaced in the route reason the operator sees, and an
unenforceable boundary is stated as such: *"this is NOT an enforceable boundary; if the
allowance is exhausted this lane could bill."*

## 7. Serve

```sh
python3 ops/haven-core/metered-relay.py serve --lane cf-workers-ai \
  --socket '<LAB_PROVIDERS_DIR>/cf-workers-ai.sock'
```

Then in the Lab the lane appears with `locality: METERED_FREE_ALLOWANCE` and
`automatic: false`. Select it explicitly; a turn additionally requires
`egress_ack: "METERED_FREE_ALLOWANCE"` on every request. A `HOSTED_SUBSCRIPTION`
acknowledgment will not authorise it.

## What this does not do

The lane is **explicit-selection-only**. It is excluded from Automatic alongside the
subscription lanes, and `cost_boundary` is advisory — nothing consumes it to widen
Automatic. Admitting provably non-chargeable lanes into Automatic is a separate
operator decision; see `labs/model-lab/METERED_ROUTE_PROPOSAL.md`.

Kaggle is not part of this: `labs/engineer/scheduler.py` refuses GPU specs because the
Model Lab lease owns the GPU, and Kaggle's public API cannot cancel a running kernel.
That wants its own R02 assignment.
