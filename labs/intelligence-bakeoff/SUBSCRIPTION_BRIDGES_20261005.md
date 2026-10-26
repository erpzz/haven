# Subscription-backed frontier model bridges — 2026-10-05

This note is deliberately **not Hermes-specific**. It evaluates how Haven or another local/open-source runtime can use frontier models through an existing ChatGPT or Claude subscription without pretending that a consumer subscription is the same thing as a developer API account.

## Decision summary

### ChatGPT: native Haven integration is now realistic

OpenAI now documents an official **Sign in with ChatGPT** path for open-source and locally hosted applications. Eligible users can authorize an OSS app to use their ChatGPT plan for eligible Responses API requests without giving the app an OpenAI API key.

That makes the preferred long-term OpenAI architecture:

```
Haven local router
  -> Sign in with ChatGPT (OAuth + PKCE)
  -> public https://api.openai.com/v1/responses
  -> account-visible Sol/Astra/etc model
```

This is better than scraping Codex credentials or using undocumented `chatgpt.com/backend-api` routes.

OpenAI's open-source flow currently requires `store:false` and `stream:true`, uses a per-host stable `ext_agent_host_id`, rotates refresh tokens, and lets the client query the signed-in account's model catalog before inference. The exact model slug should therefore be selected from the live account catalog rather than hard-coded.

Primary sources checked 2026-10-05:
- https://developers.openai.com/siwc/token-sharing-open-source
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
- https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions
- https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations
- https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites

### Claude: use the official Claude Code surface, not consumer-token scraping

Claude Pro/Max includes Claude Code, and Anthropic explicitly supports Claude Code as the terminal/agent surface under those plans. The clean Haven experiment is therefore a **bounded Claude Code worker** launched locally by Haven for a finite job, with explicit working directory/tool permissions and captured output.

Anthropic also exposes the Claude Agent SDK for building custom agents, but current public guidance for programmatic applications points developers to the Claude Developer Platform/API. Do **not** assume a consumer Claude OAuth token may be embedded in arbitrary local software just because Claude Code itself can use the subscription.

Primary sources checked 2026-10-05:
- https://www.anthropic.com/news/higher-limits-spacex
- https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously
- https://www.anthropic.com/news/claude-in-xcode
- https://www.anthropic.com/research/skills

## Ranked bridge patterns

| Pattern | ChatGPT subscription | Claude subscription | Recommendation |
|---|---|---|---|
| Native OAuth from Haven/local OSS app | **Official:** Sign in with ChatGPT + public Responses API | No equivalent general consumer-plan program found | **Best OpenAI path** |
| Official CLI as a bounded worker | Codex CLI can sign in with ChatGPT | Claude Code is included with eligible Claude plans | **Strong for both** |
| Official agent/app server | Codex app-server can receive a ChatGPT-plan OAuth token | Claude Agent SDK is excellent, but subscription reuse outside allowed surfaces is not assumed | Strong OpenAI; API-first for Claude SDK |
| Hermes provider | `openai-codex` OAuth is built in | Use Anthropic/API provider unless current Hermes+Anthropic auth is explicitly plan-authorized | Good runtime experiment, not the only bridge |
| OpenCode/other third-party auth | Prefer implementations using OpenAI's public SIWC/Responses flow | Claude Pro/Max OAuth in OpenCode has been publicly described as not officially supported | OpenAI: evaluate. Claude subscription: **do not make default** |
| Direct vendor API key | Separate API billing | Separate API billing | Stable production fallback; not subscription usage |

## Four architectures worth testing in Haven

### A. Native ChatGPT-plan provider inside Haven — preferred OpenAI target

Implement OpenAI's open-source SIWC flow in a small local broker owned by Haven.

Properties:
- browser OAuth with PKCE;
- access/refresh tokens stored in OS-protected local credential storage, never the repository/browser localStorage;
- account-specific model list;
- public Responses API only;
- `store:false`, `stream:true`;
- explicit user-visible "Using ChatGPT plan";
- no silent fallback to API billing;
- per-user credential separation.

This would let the thin Haven coordinator talk to Sol directly with **no Hermes dependency**.

### B. Codex app-server bridge — easiest supported OpenAI agent bridge

Haven can start an authenticated Codex app-server child process using an SIWC access token and communicate over its supported RPC transport. This is attractive when we want Codex's agent behavior rather than just raw model inference.

Use it as a separately labeled runtime: `codex-app-server`, not as if it were the same as a raw Responses model call.

OpenAI source:
- https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server

### C. CLI worker bridge — common denominator for ChatGPT and Claude subscriptions

Haven's local model decides that a bounded task needs frontier escalation. Haven writes a minimal job packet and launches an official CLI worker:

```
local model -> Haven policy -> finite job packet
                           -> codex CLI (ChatGPT plan)
                           -> OR claude CLI (Claude plan)
                           -> structured/sanitized result
                           -> Haven evidence ledger
```

Important:
- the local LLM never receives OAuth tokens;
- the CLI runs as a child with a restricted cwd and tool policy;
- job packet contains only data explicitly eligible for the selected cloud provider;
- the worker cannot grant itself new Haven authority;
- output is evidence/proposal, not a physical command;
- cancellation kills only the owned child and fences late publication.

This is likely the fastest safe way to make **both subscriptions useful to Haven** before building native provider integrations.

### D. Reverse MCP: frontier subscription agent uses Haven tools

Instead of local -> frontier, expose a narrow, authenticated Haven MCP surface and let Codex/Claude Code call it. This is useful for coding/research sessions in which the subscription agent is the top-level worker.

It is complementary, not a replacement for Haven's own router.

## OpenAI details that change our earlier assumptions

OpenAI's 2026 SIWC open-source flow removes the old assumption that a ChatGPT subscription cannot legitimately power a third-party local OSS app.

The documented flow:
1. registers/reuses an OAuth client for the ChatGPT account/workspace;
2. binds usage to a stable opaque host id;
3. requests the separate `chatgpt.tokens.use.direct` permission;
4. issues an access token usable against the **public Responses API**;
5. lets the app list currently available models;
6. shares the user's ChatGPT-plan usage/limits rather than creating API-key billing.

It does **not** grant access to ChatGPT conversations or the user's API key.

For the bakeoff, we should therefore add a future runtime label:
- `thin-chatgpt-plan-responses`

and compare it with:
- `hermes-openai-codex`
- `codex-app-server`
- `thin-openai-api`

while keeping model/version differences visible.

## Claude details and boundary

Supported/clean:
- Claude app/Claude Code under eligible subscriptions;
- official Claude Code CLI as the subscription worker;
- approved partner integrations such as Xcode demonstrate that Anthropic can share subscription allowance with a third-party surface when explicitly supported.

Not accepted as a Haven default:
- reading `~/.claude/.credentials.json` from an unrelated client;
- copying Claude OAuth bearer tokens into OpenCode or another proxy;
- patching a removed OAuth plugin;
- exposing a locally authenticated Claude proxy on the LAN;
- claiming Claude Agent SDK consumer-subscription billing without an explicit Anthropic-supported path.

Community projects exist that do these things; their existence is not permission or support.

For a deeply embedded Claude provider in Haven, use the Anthropic API unless Anthropic introduces a general subscription-sharing OAuth program comparable to OpenAI SIWC.

## Subscription-aware routing policy

Subscription-backed calls should be a separate route class:

```
LOCAL
  no egress, measured local cost/latency

CHATGPT_PLAN
  explicit OpenAI OAuth grant, shared plan allowance

CLAUDE_CODE_PLAN
  bounded official CLI worker, shared Claude Code allowance

OPENAI_API / ANTHROPIC_API
  explicit metered billing
```

The router must never silently move from a plan allowance to API billing or vice versa. A limit/error yields a visible route failure or asks for an eligible alternative.

## Bakeoff additions

Runtime bakeoff:
1. thin + same local model
2. Hermes + same local model
3. Hermes + ChatGPT-plan Sol
4. Codex CLI/app-server + ChatGPT plan (second phase)
5. Claude Code subscription worker (second phase)
6. thin + native ChatGPT-plan Responses after SIWC adapter implementation

Model bakeoff:
- local candidate suite remains the hardware/model comparison;
- Sol/Claude are **reference ceilings**, not "local model candidates";
- compare correct-task-time and escalation frequency, not raw tokens/sec.

## What not to build

Do not build a generic "subscription proxy" that forwards arbitrary users' traffic through one person's ChatGPT or Claude plan. The goal is a private, user-authenticated local assistant using that same user's explicit account grant.

Do not use browser automation, copied cookies, private backend endpoints, credential-file scraping, or account rotation to evade plan limits.
