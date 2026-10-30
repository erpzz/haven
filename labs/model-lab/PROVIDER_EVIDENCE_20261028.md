# Provider evidence — free-tier hosted inference candidates

Researched 2026-10-28. Base commit read: `eaa76f8`. Supports
`METERED_ROUTE_PROPOSAL.md`; relates to issues #72 and #73.

Status tags per `START_HERE.md`: every row below is **planned** — no provider was
contacted, no credential exists in this session, and no inference was performed.
This is public-documentation research, not a measured result. Nothing here is an
enrollment: enrollment remains administrator input per `providers.py`.


Confidence is recorded honestly, because the distinction decides whether an entry
is usable as `TermsEvidence`:

- **primary** — provider's own documentation
- **secondary** — provider docs seen via a mirror or docs-repo diff, not the live page
- **third-party** — aggregator or community source; *not* sufficient for AUTONOMOUS

---

## Summary

| Provider | Workload | Chargeable? | Boundary available | Recommended class | Confidence |
|---|---|---|---|---|---|
| Cloudflare Workers AI | inference | No, on Workers **Free** | Requests fail past allocation | AUTONOMOUS candidate — strongest | secondary |
| Groq | inference | No, on Free tier | 429 at rate limit; no budget to overrun | AUTONOMOUS candidate | third-party + community |
| Modal | training, inference, cpu_batch | **Yes** | Workspace **spend limit**, provider-enforced | AUTONOMOUS candidate *iff* spend limit verified | primary |
| Kaggle | training | No | Weekly accelerator quota | APPROVAL_REQUIRED — see blockers | third-party |
| Google Colab Free | — | No | — | INTERACTIVE_ONLY (excluded) | prior finding |

---

## Cloudflare Workers AI

**Free allocation:** 10,000 Neurons/day, shared across models, resetting daily at
00:00 UTC. Overage on Workers Paid is $0.011 per 1,000 Neurons.

**Why this is the strongest candidate:** the pricing table's overage column for
Workers **Free** is not a rate — it directs the user to upgrade. The docs state
that exceeding a limit causes further operations to fail with an error. On the
Free plan there is therefore no billing path at all: the $0 boundary is the
provider's own behaviour, not our accounting. That maps to
`CapEnforcement.NOT_CHARGEABLE`.

**Caveats to verify against the account:**
- A text-generation rate limit (reported ~300 req/min) applies separately from the
  Neuron allocation.
- Some newer models require a paid billing method and are therefore *not* on the
  free allocation. The eligible model list must be read from the account, not assumed.
- Neuron cost per request varies sharply by model, so "10,000/day" is not a request count.

Source: Workers AI pricing docs (`developers.cloudflare.com/workers-ai/platform/pricing`),
read via docs-repo diff and mirror — the live page was not on this session's fetch
allowlist, so confidence is **secondary**. Owner should confirm on the live page.

---

## Groq

**Shape of the free tier:** rate-limited rather than budget-capped. No credit card
required; accounts sit on Free until explicitly upgraded to Developer. Limits apply
at the **organisation** level and per model, across several dimensions (RPM, RPD,
TPM, TPD). Exhaustion returns 429.

**Why it suits unattended use:** there is no spend to overrun — the failure mode is
refusal, not a charge. Maps to `NOT_CHARGEABLE` while the account stays on Free.

**Critical caveat:** the published limits table is explicitly a *sample*. The
authoritative limits for a given organisation are on that account's own limits page
in console settings, and Groq notes exceptions exist. So the adapter must read
quota from response headers (`x-ratelimit-remaining-*`) and never from a hardcoded
table — which is how `providers/groq.py` already behaves, returning `None` before
the first response rather than assuming headroom.

**Also relevant:** one aggregator records Groq as not training on customer data,
attributing this to the Services Agreement. Confidence is third-party; the owner
should confirm from the agreement itself before routing anything sensitive.

Confidence: **third-party + community**. Primary docs (`console.groq.com/docs/rate-limits`)
need an authenticated read. Not yet sufficient for AUTONOMOUS.

---

## Modal — correction to the previous session

**I was wrong last session.** I concluded Modal could never be AUTONOMOUS because
included credit is not a ceiling. The first half is still true; the conclusion was not.

Modal's own budgets documentation describes a **Workspace spend limit**: a monthly
cap on net charges after credits are applied, distinct from the Workspace budget
(which caps usage). When that spend limit is reached, Modal stops workloads that
would incur further out-of-pocket charges; work still covered by remaining credit
may continue until the usage limit is hit. If no custom limit is set, the default is
the cycle's usage limit minus credits.

That is a **provider-enforced ceiling**, not client-side accounting. A spend limit
set to $0 means Modal itself halts anything that would cost money, leaving only
credit-covered execution. That satisfies `CapEnforcement.PROVIDER_HARD_LIMIT`, so
the existing `BudgetGuard` already handles this correctly once the cap is recorded —
no code change needed, only a verified reading.

**What must be verified before promotion:**
1. A spend limit is actually set on the workspace, at $0 or another agreed figure —
   and read back from Modal, not assumed. The *default* is credits-minus-usage-limit,
   which is **not** $0.
2. Starter-plan concurrency limits (reported ~100 containers / 10 GPU concurrency).
3. Network egress. A third-party source reports egress joining the meter from
   1 October 2026 at $0.04/GiB after an included tier. If accurate this is an
   out-of-pocket cost category the estimate must include — `CostEstimate.includes_egress`
   exists for exactly this. Needs primary confirmation.
4. Whether included credits cover every endpoint type. The original directive flagged
   that Shared Endpoint token charges may sit outside included compute. Unverified
   here; treat as excluded until confirmed.

Source: `modal.com/docs/guide/budgets` — **primary**.

---

## Kaggle

**Quota:** roughly 30 GPU-hours per week, with a per-session ceiling around 12 hours
and a weekly reset (community sources say Saturday 00:00 UTC, and that the allowance
is somewhat dynamic, 30–41h). All reports here are third-party.

**Automation surface:** the public API supports pushing a kernel — which also triggers
execution — polling status, and downloading output. That is a genuine batch-submit
interface, which is what an R02 remote-training adapter needs.

**Three real blockers, not formalities:**

1. **No programmatic cancellation.** Multiple independent sources report that the
   public API cannot cancel a running kernel session; stopping requires the web UI.
   The directive's inference-gateway requirement lists cancellation as mandatory. A
   training adapter therefore cannot honour a cancel request through the API — it can
   only stop *polling*. This must be surfaced to the operator rather than papered over.
2. **Log availability is post-hoc.** Status polling returns logs only once the kernel
   reaches complete/error; live execution logs are not exposed. A long LoRA run is
   opaque until it finishes.
3. **Free-GPU notebooks may be forced public.** One source reports notebooks on free
   GPUs are public and auto-shut-down. If that holds, no restricted dataset can go
   through this path — `DataSensitivity.RESTRICTED` must deny Kaggle outright. This
   is the single most important thing to confirm before R02 uses it.

Plus the personal/non-commercial usage condition noted in the original directive,
which the owner must affirm covers Haven's research use.

Confidence: **third-party throughout.** Not sufficient for AUTONOMOUS.

---

## What the owner needs to do per provider

| Provider | Minimal verification to promote |
|---|---|
| Cloudflare | Confirm live pricing page; list models eligible on Free for this account |
| Groq | Read the account's own limits page; confirm data-training stance from the agreement |
| Modal | Set and **read back** a spend limit; confirm egress metering and endpoint coverage |
| Kaggle | Confirm notebook-visibility rule, weekly quota, and that terms cover this use |

Once a row is confirmed, record it as `TermsEvidence` (doc_url, clause, retrieved,
scope) in `providers.json` and change `eligibility`. The loader rejects evidence
older than 180 days, so these need re-reading each cycle.
