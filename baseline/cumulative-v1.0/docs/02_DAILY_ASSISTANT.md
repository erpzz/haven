# Everyday Haven: experience, tasks and digital actions

**Proposed domain design; not M0 expansion.** The daily assistant must be valuable even before a single aircraft, glasses SDK or sensor works. Give this domain equal product attention to the physical research branches.

## First useful release

Begin with authenticated text conversation, a deliberately supplied project notebook, visible memory controls, and source-linked answers. Add drafts and daily planning based on explicitly supplied information before live connector writes. Then implement one durable reminder workflow and one read-only personal connector, each with its own tests. Voice, more connectors and household coordination follow separate gates.

Keep one visible Haven personality across endpoints. Its stable persona is calm, capable, direct and warm; the model/version doing a task may change. Preferences for response length or quiet hours are user-editable. Do not use diagnoses, sensitive history, guilt or fear to make the assistant sound personal. It should not claim private continuous thinking or emotional dependence.

## Conversation contract

Resolve a turn into one of: answer, clarify, retrieve permitted evidence, draft, propose an action, schedule an already-authorized task, or explicitly decline/stop because the input is insufficient. Each turn binds a principal, conversation, relevant project/incident, permitted data scopes and an expiry for context. A pronoun such as “that one” needs an unambiguous referent before a write.

Haven must distinguish “I can prepare it,” “I have prepared it,” “the provider accepted it,” and “the intended result was observed.” A natural-language success message is constructed from actual receipts. The existing M0 teaches that pattern; ordinary tasks get their own records rather than borrowing outside-check expiry semantics.

## Memory classes

| Class | Authority and retention | Retrieval rule |
|---|---|---|
| Reviewed preferences | User reviews or explicitly requests saving; editable/deletable | Current revision only; cannot grant new physical permissions |
| Personal projects | Owned notes, decisions and approved files | Project-scoped search with source links |
| Shared household | Deliberately shared tasks/notes | Grant permits each recipient and purpose |
| Conversation context | Short-lived referents and active topic | Expire or reconfirm before sensitive use |
| Operational state | Device/controller records, not model recollection | Freshness and origin accompany every answer |
| Incident evidence | Accepted observations and corrections | Preserve source/provenance; distinguish inference |
| Research notebook | Hypotheses, methods, failed/positive tests | Never convert untested predictions into measurements |

Start retrieval with structured IDs, time ranges, tags and full-text search. A later embedding index is derived and rebuildable. Its deletion and authorization filtering must be tested independently. Do not use a conversation summary as the only record of a user's approval.

## Action lifecycle

A proposed `DailyAction` can move through DRAFT, NEEDS_CLARIFICATION, AWAITING_CONFIRMATION, AUTHORIZED, SUBMITTED, ACCEPTED, OBSERVED_COMPLETE, FAILED, CANCELLED or OUTCOME_UNKNOWN. An action may not need every state. State names are domain-specific; the semantics are not optional.

Bind confirmation to the actual recipient/resource, content revision and scope. A changed email body or different calendar requires a fresh decision if it changes what was authorized. Suitable low-risk repeated actions can have narrow reviewed standing grants; every trivial read need not require another prompt. A daily grant never becomes an aircraft/printer/medical authorization.

When a provider request times out, query its supported status/idempotency mechanism before repeating an irreversible write. Store a local idempotency key and a remote identifier when available. If the provider cannot disambiguate, show unknown and ask for reconciliation rather than sending a second email merely to be safe.

## Reminders and schedules

A reminder is durable only after a scheduler commits it. Record timezone, local intent, UTC execution candidates, recurrence semantics, daylight-saving policy, missed-run policy, destination and delivery receipts. A recurrence across a clock change must be explicitly defined; silently guessing whether “8 AM” means fixed UTC is unacceptable.

If the desktop sleeps, distinguish missed, still eligible, expired and already delivered. Legitimate future daily reminders may run after reconnect according to their policy. This does not relax M0's no-automatic-resubmission rule or later physical no-replay behavior. Cancelled tasks remain cancelled across restore. Optional AI availability must not decide whether an already scheduled deterministic reminder is due.

## Connector investigation template

For personal calendar/email/contacts/files/tasks/home controls, document the official API or supported connector route; identity and account owner; least read/write scopes; consent UI; token storage/refresh/revocation; provider changes; rate limits; idempotency/status lookup; deletion/export; offline behavior; and a synthetic/test account path. A connector in a hosted chat product is not automatically callable by a standalone Haven application.

Do not read Eric's real accounts during design. Do not import workplace identity or customer information just because he administers those systems. Browser/desktop automation is a separate sandboxed option only where official APIs cannot meet a reviewed need; it never receives the control-plane keys.

## Attention and voice

Default interaction is foreground/on-demand. Proposed proactive classes are quiet record, grouped useful update and independently configured protective alert. Let each person control quiet hours and ordinary interruptions. Notification preference changes do not silently disable native alarms or standing emergency policies.

Push-to-talk is the first voice target. Store only the necessary transcript under the user's retention choice. Separate “stop speaking,” “cancel this investigation,” “cancel that reminder,” and “request robot recovery.” An ambiguous voice command should not cut a motor or cancel a safety task.

The assistant should explain uncertainty naturally: “I found an older note, not a current measurement.” “I drafted the reply; nothing has been sent.” “Your request is stored locally; there is no internet connection to deliver it yet.” Voice and screen display should expose the same actual state.

## Everyday acceptance bar

Evaluate correct source retrieval, recipient resolution, drafts versus sends, temporal language, undo/cancel semantics, cross-user isolation, malicious document content, account revocation, cost and degraded operation. At least half of initial user-journey tests concern ordinary usefulness, not emergencies. Success means a task actually becomes easier and its outcome remains understandable, not simply that the model produces friendly prose.
