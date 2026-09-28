# Two-person privacy, identity and action authority

**Design proposal.** Eric and Kennedy are independent users. Shared equipment does not imply shared private data. This project brief is not Kennedy's consent. A health sample, glasses feed, private note or personal calendar belongs to its subject/account owner under explicitly defined rules.

## Principals and scopes

Use person principals, device principals, narrowly scoped service principals and short-lived job identities. Bind devices to the enrolled person; handle borrowed glasses, replaced phones, a lost Watch and ambiguous household audio without guessing who is speaking. A public emergency-portal guest is a separate low-privilege principal.

Separate `personal:user_a`, `personal:user_b`, `household:shared`, `research:synthetic`, `incident:<id>`, `device:<id>` and `control:<domain>`. Do not infer access through familial relationships. A shared conversation may cite a private record only if its current sharing grant permits the audience and output channel.

## Consent is several decisions

Reading for the subject, retaining history, making derived summaries, sharing with a partner, announcing aloud, submitting to a specified provider and including in a reviewed emergency report are separate purposes. Grants include data types, resource bounds, actor, recipient, expiry, revocation epoch and policy version. A generic “Haven may help me” is insufficient for all future integrations.

Check grants when assembling context, before external transmission and before publishing a result. Revocation while a model job is running must block delivery of now-disallowed content. Caches key by person, scope, grant revision, evidence version and model/prompt. Forgetting a memory must remove or invalidate derived copies according to an explicit retention plan; it cannot be solved solely by hiding one UI row.

Audit retention and deletion can conflict. Minimize content in long-lived audit records, retain opaque references/reasons where justified, document backup expiry and disclose what cannot be immediately erased. Do not promise immutable full records and immediate complete deletion of the same data.

## Threat model

| Threat | Required boundary/test |
|---|---|
| Malicious email, webpage, image sign or spoken instruction | Untrusted content stays data; cannot add tools or alter grants |
| Household user asks for partner's records | Subject and recipient checks precede retrieval |
| Compromised research agent | Synthetic/read-only scope, no runtime secrets or execution socket |
| Cloud provider receives private material by fallback | Privacy denies route before cost/availability selection |
| Stolen phone/session | Revoke device/session and refresh rights; stale cached grants fail closed |
| Shared speaker leaks private health details | Audience-aware output selection; private phone response instead |
| Forged tool success | Domain receipt plus observed result where available, never model prose |
| Admin on shared host reads plaintext | Explicit residual risk; application roles do not defeat host administrator |
| Public emergency gateway traffic reaches control network | Network and application isolation; separate secrets and routing |
| Restored old DB resurrects authority | New run/epoch, revoked/expired grants unusable; review-only restoration |

Per-user encryption at rest can reduce casual disclosure, but a server performing plaintext inference still handles decrypted data. Discuss trusted-device processing, separate processes/accounts, locked key access and usability tradeoffs honestly. Do not market a shared-admin prototype as cryptographically private from that administrator.

## Action authorization model

The coordinator produces typed proposals. Deterministic policy checks user/service identity, exact resource, action, consent, configuration, evidence freshness, budget and domain qualification. Human approval or a separately reviewed standing policy then authorizes a bounded effect. Recheck material conditions before dispatch. The executor validates the approved identity/version/expiry/one-use execution reference independently where feasible.

Separate namespaces: `daily.read`, `daily.draft`, `daily.send`, `daily.schedule`, `evidence.read`, `observe.propose`, `flight.execute`, `robot.execute`, `fabricate.execute`, `emergency.prepare`, and eventual qualified communication. General model access to one does not imply any other. No runtime model receives arbitrary policy editing, raw radio/flight packets, an administrator shell or the ability to install unreviewed tools.

## Standing autonomy

Useful autonomy can come from a reviewed policy rather than requiring a click for every repetition. Define the qualifying facts, scope, maximum actions, time/energy budget, allowed hardware, evidence requirements, review date and revocation mechanism. Standing policies for daily reminders, bench experiments and incapacitation scenarios are different records with different assurance requirements.

Do not interpret an arbitrary unanswered message as incapacitation. Preserve the planned S2 synthetic standing-policy path and independent help workflow. User authority cannot waive physical capability limitations or establish legal deployment permission by itself.

## Human agency and recovery

Every person can pause personal collection and ordinary proactivity. Show what is active, why, and how to stop it. Keep independent hardware/manual recovery available. Cancelling speech must not cancel a medical-call interface, and cutting all electrical power is not a universal safe robot/drone stop.

A compromised component should lose its own capability, not automatically every independent alarm. Favor bounded degraded operation over an all-or-nothing “lockdown” that accidentally removes the last communications path.
