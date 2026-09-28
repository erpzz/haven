# RI-01 operational clarifications and delivery checklist

Coordination issue: https://github.com/erpzz/haven/issues/17

1. The user asked for autonomous execution in the launched Codex session, not a stack of manually dispatched chats. Follow MASTER_PROMPT.md and advance ready tasks automatically.
2. Every new author handback gets a distinct independent review assignment before it satisfies a hard dependency. These review/rework assignments count toward the 64-assignment ceiling. The 28-node file is a seed graph, not a claim that only 28 tool calls or agents are needed.
3. A provisional vision read may start alongside intake, but VISION-0 earns completion only after it consumes the actual intake record. Hard dependencies govern acceptance; soft edges do not create scheduler waits.
4. Available existing research can satisfy a queue task only after exact-version review and equivalence mapping. A missing main-branch file may exist in an incoming PR. R02's publication edition is not a new research result.
5. Native subagent IDs and real responses are mandatory. A fallback from named profiles to native default roles is acceptable only when it still creates separate actual children. Single-agent roleplay is not an autonomous team.
6. Root owns shared state and Git. Authors write disjoint assigned report directories; reviewers return findings. A read-only fallback is reported honestly. Configuration is not a claim of strong cross-agent data isolation.
7. Full multimodality is required in the system design. The development workflow records actual modality access: images/figures, audio, sampled versus continuous video, spatial/sensor records and outputs. Unavailable modalities remain explicit gaps; they do not silently become text-only passes.
8. A more capable general model does not replace specialized CV/DSP/geometry or authorize physical action. Preserve low-cost task-specific options and original source evidence.
9. Consultations are actual scoped messages and source-linked answers. Two rounds maximum before recorded dissent or an operator decision. Only consequential unresolved choices should interrupt the user; independent work continues.
10. Final synthesis consumes current reviewed inputs and receives separate vision, code and R13/evidence reviews. Changed inputs trigger affected rechecks. Source fidelity, scientific support, runtime qualification and operator permission are separate states.
11. Final output is committed to the campaign branch, pushed and read back, with a consolidated PR and exact outstanding decisions. Do not auto-merge the campaign, implement the product or invoke the old source-import workflow.
12. At the cap, stop owned children, checkpoint unfinished work and provide one resumable report. No automatic follow-on session, detached background process or invented completion time.

## Setup verification boundary
SETUP_CHECKS.json records static parsing/graph checks only. Native role loading, delegation and media inspection must be tested in the user's actual Codex runtime on launch. No existing research/source PR was accepted or merged by preparing this campaign.
