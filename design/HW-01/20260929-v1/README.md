# HW-01 — Haven local coding worker and modular minimum hardware

2026-09-29 • PROPOSED_DESIGN • NOT_IMPLEMENTED • NOT_INDEPENDENTLY_REVIEWED

The operator requested a dedicated local coding agent with a broad toolset, structured feedback into Haven, a minimum viable hardware/parts list, future compute options, and visual teaching material. They explicitly added interest in Raspberry Pi, Jetson and other modules to augment future agents. This additive design answers both requests. It does not install software, buy equipment, start a new goal, change an active campaign, or authorize a policy bypass.

## Read in order

1. [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md): the three logical zones, local-agent choice, permissions, tools and feedback contract.
2. [HARDWARE.md](HARDWARE.md): zero-purchase start, optional workbench parts, a dedicated worker versus an inference workstation, and accelerator tradeoffs.
3. [EDGE_MODULES.md](EDGE_MODULES.md): modular sensor/compute nodes, role-to-hardware mapping, part bundles and the edge-to-Haven contract. Includes the latest Raspberry Pi price observation; use its correction where earlier estimates differ.
4. [FIRST_PROOF.md](FIRST_PROOF.md): a proposed bounded implementation/evaluation sequence using the existing roles.
5. [DIAGRAMS.md](DIAGRAMS.md): GitHub-rendered architecture, feedback loop and hardware evolution diagrams. EDGE_MODULES adds the modular topology.
6. [SOURCES.md](SOURCES.md): inspected primary documentation and dated retail observations, with limitations. Edge-specific primary references are appended in EDGE_MODULES.

## Anchors and continuity

Research baseline: 6bc1c8df1218ceb0e0d8709adee65d1e44634047. Retain PRECEDENCE.md and the seven I01–I07 interfaces. IP-01's role map at 8e1304caf82c0a889eeaea7691db7b9d7b98c526 remains its own scoped operating model. SI-01 vision anchors are at cdc32eabe847a6bb5fff1a0f69d7ba5f6b7832d5, research/SI-01/20260929-v1/VISION_ANCHORS.md.

The proposed local worker label is **Forge**: a coding role inside Haven, not a replacement product name, new root supervisor, biological model, or autonomous self-modification authority. Other friendly node labels are proposed aliases, not agents that have been created. Design identifiers HW-01/FW-* are local proposal IDs, not canonical test aliases.

IP-01 Issue #20 / PR #21 is a separate live-work track. Do not borrow its assignments, replace its selected model, change its deadline, or add this proposal as a prerequisite. Do not retry PR #19's denied metadata action. Existing research, source branches, main, runtime state and original application workspaces are unchanged by this publication.

## Central recommendation

Keep Haven's durable state and release authority separate from a powerful coding laboratory. Evaluate OpenCode plus a local model service as the first broad-tool worker; use Aider as a smaller coding baseline and OpenHands as a heavier alternative. Reuse existing hardware to establish capability before purchase. A 24 GB GPU or 64 GB unified-memory machine is a practical next evaluation tier for stronger local coding, not a mandatory starting cost or a guarantee of quality.

Add distributed modules for a specific useful observation, local interface or controlled physical subsystem. Use deterministic microcontrollers where possible, Pi-class general-purpose nodes where appropriate, and Jetson/accelerators for measured perception workloads. One agent need not equal one board or one loaded LLM. Small boards do not automatically combine their memory into a large model computer.

No current host inspection, local model benchmark, installation, deployment, purchase, native-agent dispatch, or independent reviewer run was performed for this design. Hardware class inputs are operator-reported; exact free memory, storage, power supply, case fit and thermal capacity remain unverified. Dollar allowances are not a validated shopping cart. See the source records for current documentation conflicts and pricing caveats.
