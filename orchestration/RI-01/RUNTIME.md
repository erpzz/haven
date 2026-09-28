# Native runtime preflight — no custom agent daemon required

RI-01 uses the user's installed Codex harness. The project includes ten role files under `.codex/agents/` and a small `.codex/config.toml` enabling agents, requesting live public search and limiting open children to three. No provider endpoint, model, credential, unsafe permission override, webhook or scheduled launcher is installed.

## Documentation basis checked 2026-09-28
OpenAI's official Subagents documentation describes project-local agent TOML files, required name/description/developer_instructions, role-specific settings, native delegation and lifecycle management. Its Configuration Reference documents agents.enabled, agents.max_concurrent_threads_per_session and project trust. Image Inputs documents image attachment/inspection; it does not establish arbitrary direct audio/video support in every Codex client. Sources:
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://learn.chatgpt.com/docs/config-file/config-reference
- https://learn.chatgpt.com/docs/image-inputs

Documentation support is not a successful run on this user's installed client. Formats and capabilities can change. Check the installed runtime and its effective configuration before dispatch. Project trust and parent permission overrides can affect which settings apply.

## Launch preflight
1. Confirm actual repository checkout, Git origin, current base, host class and available workspace-write/public-research permissions. Select a clean new branch; never modify the active M0 or NIGHT-01 directories.
2. Record installed client/version when exposed. Inspect the loaded agent names and actual native creation/message/wait/close tools. Use the current tool schemas, not invented CLI switches or JSON.
3. Spawn a tiny read-only intake child to report one known file's identity and return. Record the real ID and result, then close it. This proves delegation, not completion of a research task. Default native role plus exact custom instructions is an honest fallback when profiles cannot load; no actual delegation means BLOCKED_RUNTIME_MULTI_AGENT.
4. Verify available web, image, PDF and media tools. Native image recognition is a required development capability; run a benign small visual check. Audio/video gaps are recorded per modality. Do not install new tools or use a paid provider just to make a green matrix.
5. Record effective child permissions. Read-only settings do not constrain all remote connectors; writing roles' allowed-path rules are coordination instructions, not a hardened multi-tenant boundary. Do not use full-access/approval-bypass flags to satisfy this campaign.
6. Start the task graph and maintain actual receipts. A provisional vision read may run while intake is working, but VISION-0 is not accepted until it consumes the intake artifact; hard-input gates control completion.

## Model and cost policy
Profiles intentionally omit model/reasoning pins so they do not assume account availability or force the purchase of another service. Record inherited or explicitly selected settings. The user may select a qualified cheaper model for narrow intake/source checks and a stronger one for integration or difficult science, but availability and modality support must be verified. Do not silently claim cheaper routing while every child inherited a costly parent. Multi-agent research consumes the session's allowance even when no extra API is enabled.

Three children are a concurrency ceiling, not a three-agent team. The supervisor schedules the ten roles and individual research reviewers across waves. Idle integration/review agents should checkpoint and close so research can proceed. There is no Discord bot, inter-chat subscription or API service to maintain.

## What this run does not prove
Preparing or parsing role files does not establish that they were loaded, that native agents ran, that a video was understood, or that Haven has a working multimodal runtime. Use PREPARED, CONFIG_PARSED, CHILD_SPAWN_VERIFIED, IMAGE_INPUT_VERIFIED, RESEARCH_COMPLETE and MODALITY_BLOCKED as separate claims with evidence. Current M0/R1, model and physical qualification remain independent.

## Permissions or limits interrupting work
Respect the host's limits. A read-only or disconnected session may require the user to open this repository in an appropriate Codex workspace once; do not fabricate a PC connection. If available tools need a new approval, record the blocked operation and continue independent work. At the finite ceiling or unavailable native delegation, save exact remaining tasks and a single actionable resume note. No future execution occurs without a resumed user session.
