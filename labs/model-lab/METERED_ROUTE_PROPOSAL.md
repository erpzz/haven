# Proposal: a metered-API route class for free-tier hosted inference

Status: **proposal, not an accepted decision.** Per `PRECEDENCE.md` gate 3 this
remains a recommendation until operator approval is recorded in
`coordination/DECISIONS.md`. Base commit read: `eaa76f8`. Relates to issue #73
(fit-aware routing) and issue #72 (per-provider context validation).

## Why this is a proposal and not a patch

The assignment was to integrate free-tier cloud inference (Groq, Cloudflare
Workers AI, Kaggle, Modal) into Haven's existing provider policies and routing.
Reading `labs/model-lab/providers.py` at `eaa76f8`, that cannot be done as an
extension. It collides with four invariants that the current code states
deliberately and, in one case, enforces by test.

**1. Metered API classes are excluded by design.**
`ROUTE_CLASSES` admits exactly `CLAUDE_CODE_PLAN` and `CHATGPT_PLAN`, with the
comment that these are plan allowance only and that a metered API class would be
a separate, explicit addition. `tests/test_cloud_lane.py` asserts that a lane
declaring `route_class: 'ANTHROPIC_API'` is **refused**. Groq and Cloudflare
Workers AI are metered API services — free tier or not, they are keyed and
metered, not subscription-allowance. Admitting them means changing a test that
exists to keep them out. That is an owner decision.

**2. Transport is private Unix SSH sockets, not outbound HTTPS.**
`PrivateWorkerConnection` requires an owner-owned socket inside the enrollment
directory, and `Registry.reload` rejects any `socket_path` that is not
`<enrollment_dir>/<id>.sock`. Even a `cloud` lane goes through that socket — the
existing cloud lanes are local CLI processes reached over a loopback tunnel
(`ops/haven-core/cloud-worker.py`), not direct API calls. An adapter dialling
`api.groq.com` from the Lab would bypass the transport contract entirely.

**3. Hosted egress is never automatic.**
The module docstring says explicit selection only, never Automatic. `choose()`
filters `kind != 'cloud'` when `requested == 'auto'`, and its final error states
that no paid fallback was attempted. The assignment's §7 — permit unattended
dispatch where ownership, documented use, quota and a $0 boundary are verified —
is a direct reversal of this invariant. It may well be the right reversal for
genuinely non-chargeable providers, but it is a reversal, and it is the one thing
in the assignment that the existing code most clearly forbids.

**4. A model cannot enroll a provider.**
The docstring states that registration files are private administrator input,
not model output, and that a model cannot enroll workers, choose URLs or rotate
credentials. Any registry of providers that I author is model-authored
enrollment. This also means the broker artifact carried over from the previous
session (a JSON provider registry with an eligibility field) duplicates
`Registry` and should not land.

## What is being proposed

A fifth gate, narrower than the assignment asked for:

### A `METERED_API` lane kind, distinct from `cloud`

| | `cloud` (existing) | `METERED_API` (proposed) |
|---|---|---|
| Egress | `HOSTED_SUBSCRIPTION` | `METERED_FREE_ALLOWANCE` |
| Transport | private SSH socket to local CLI | **unchanged** — SSH socket to a local relay process |
| Automatic selection | never | never, **unless** non-chargeable is proven |
| Billing risk | none (plan) | none *only* while the allowance holds |

The transport row is the important one: rather than opening outbound HTTPS from
the Lab, a metered lane should be reached the same way the Claude Code and Codex
lanes already are — a small owner-run relay beside `cloud-worker.py` that holds
the key and exposes `/v1/models` and `/v1/chat/completions` over its private
socket. The Lab keeps its no-outbound-egress property; the key never enters the
Lab process; `providers.py` needs no new transport.

### Two new enrollment fields, owner-supplied

- `cost_boundary`: one of `NOT_CHARGEABLE`, `PROVIDER_HARD_LIMIT`,
  `PROVIDER_SOFT_ALERT`, `CLIENT_SIDE_ONLY`.
- `eligibility_evidence`: the provider document URL, the clause relied on, and
  the date it was read.

`choose()` then admits a metered lane into Automatic **only** when
`cost_boundary` is `NOT_CHARGEABLE` or `PROVIDER_HARD_LIMIT`. Soft alerts and
client-side accounting stay explicit-selection-only, because neither can stop a
charge. This keeps the existing invariant intact for everything that can bill and
relaxes it only where the provider itself refuses to bill.

### Why the boundary distinction carries the weight

The one genuinely reusable idea from the previous session's artifact is that a
ceiling this process believes in is not a ceiling. Only a provider-imposed stop
counts. Applied to the researched providers (evidence in
`PROVIDER_EVIDENCE_20261028.md`):

- **Cloudflare Workers AI on Workers Free** — no overage path exists; operations
  fail past the allocation. `NOT_CHARGEABLE`. Strongest first candidate.
- **Groq on Free** — rate-limited, no card, 429 at exhaustion. `NOT_CHARGEABLE`
  while the account stays on Free. Limits must be read from response headers,
  never a hardcoded table, since the published table is a sample.
- **Modal** — chargeable, *but* Modal's own budgets documentation describes a
  workspace spend limit that stops workloads which would incur out-of-pocket
  charges. Set to $0 and read back, that is `PROVIDER_HARD_LIMIT`. The default is
  not $0, so it must be verified, not assumed.
- **Kaggle** — not an inference lane at all; see below.

## Kaggle does not belong in this lane

Kaggle is GPU training, and two things block it independently of the above:

1. `labs/engineer/scheduler.py` refuses GPU work outright — `validate()` raises
   when `spec.get("gpu")`, because the GPU belongs to whoever holds the Model Lab
   lease. A Kaggle training adapter therefore cannot be a fleet-scheduler job.
   It needs to be driven by the lease holder, which is an R02 question, not a
   routing question.
2. Kaggle's public API reportedly cannot cancel a running kernel, and exposes
   logs only after completion. Haven's gateway treats cancellation as
   first-class (PR #85 records a cancelled stream's terminal state in its
   receipt). An adapter that cannot cancel must say so rather than report a
   cancel it did not perform.

Recommendation: keep Kaggle out of this proposal and handle it as a separate R02
remote-training assignment, after the inference lane is proven.

## Status of each decision

**Decision 1 — a `metered` lane kind via an owner-run relay: implemented on this
branch.** It needed no invariant reversal, so it did not need to wait. A metered
lane is explicit-selection-only, exactly like the existing plan lanes, and
`choose()` excludes it from Automatic alongside `cloud`. Delivered:

- `ops/haven-core/metered-relay.py` — the relay. Holds the provider key, talks to
  Cloudflare Workers AI or Groq, serves `/v1/models` and `/v1/chat/completions`
  over the enrollment socket. The Lab makes no outbound request and never sees the
  key. A 429 or allowance refusal is reported upward, never retried, because
  retrying an exhausted allowance is how a free tier becomes an invoice.
- `labs/model-lab/providers.py` — `METERED_CLASSES`, `COST_BOUNDARIES`,
  `eligibility_evidence()`, the `metered` enrollment contract, and a
  `route_reason` naming the vendor, the allowance, the boundary and whether that
  boundary is enforceable.
- `labs/model-lab/labcore.py` — `egress_ack` now names which egress is being
  acknowledged. A `HOSTED_SUBSCRIPTION` ack does **not** authorise a metered lane,
  and the reverse also fails.
- `labs/model-lab/tests/test_metered_lane.py` — 10 tests, 9 subtests, no network
  and no key.

**Decision 2 — relaxing "hosted egress is never automatic" for provably
non-chargeable lanes: NOT taken.** This is the one genuine reversal and it is an
operator gate; a model should not record its own approval for it. `cost_boundary`
and `boundary_enforceable` are computed and surfaced today but are advisory —
nothing consumes them to widen Automatic. If you approve it, the change is one
predicate in `choose()`: admit `kind == 'metered'` when `cost_boundary` is in
`ENFORCEABLE_BOUNDARIES`. A test asserting that `CLIENT_SIDE_ONLY` and
`PROVIDER_SOFT_ALERT` stay refused should land in the same commit.

**Decision 3 — enrolling the first lane: yours.** Enrollment is administrator
input. `metered-relay.py configure` records a lane for the relay but deliberately
does not write the Lab enrollment file, and says so in its output.

No provider was contacted and no credential exists in this session, so there is no
authenticated receipt. The first real one needs a Cloudflare token and account id
placed in the relay's private key directory.
