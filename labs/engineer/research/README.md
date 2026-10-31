# Haven Engineer research index

These are evidence-first research artifacts, **not** production features, deployment approval, or proof of trained-model performance.

## Architecture decision package — 2026-10-31

- [Small specialist models, adaptive routing, and memory architectures](SMALL_SPECIALISTS_ROUTING_MEMORY_ARCHITECTURE_20261031.md): current literature, audited Haven baselines, competing architectures, training curriculum, external/learned memory, and stop/go decisions.
- [Pre-registered specialist and memory experiments](SPECIALIST_MEMORY_EXPERIMENT_PROTOCOL_20261031.md): paired arms, independent outcome verification, repository/chronological data splits, ablations, latency/energy metrics, privacy controls, and acceptance/rejection criteria.

**Summary:** begin with the existing 4B model plus verified skills and evidence-grounded memory; use a deterministic cascade before training a router, and compare a single small LoRA adapter against executable skills and scripted trajectory controls before adding separate resident models. Treat Titans/Hope/Mamba-inspired neural memory and WAN MoE as subsequent research questions, not near-term deployments.

## Related earlier Haven evidence

- [E1: procedural skill inheritance](e1-inheritance.json)
- [E2: controller replication/efficiency](e2-rerun.json) and [E2 efficiency](e2-rerun-efficiency.json)
- [E4: GPU task-throughput placement, planned](e4-task-throughput-slink.json)
- [E5: exhaustion recovery and controller](e5-exhaustion-recovery.json)
- [Haven Engineer acceptance](../ACCEPTANCE_20261027.md)
- [Morphogenesis](../morphogenesis/README.md)
- [Trained routing pilot](../router_lab/README.md)
- [Specialist acceptance](../../model-lab/specialists/README.md)

Raw private task/host receipts remain out of the public repository. Experimental work needs separately scoped authorization, isolated worktrees, truthful status labels, and reviewable PRs.
