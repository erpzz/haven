# Haven Continuous Security Factory — Research Vision

Status: research/design note. Additive only. This document does not change any frozen evaluation, reserve, promotion, training, or runtime authorization boundary.

## Thesis

Haven should not try to reproduce the hosted Daybreak service. The useful research target is to reproduce selected *architectural functions* at local scale and make them inspectable, deterministic, and composable with small local models.

The core research question is:

> **How much of the capability gap between a 4B local model and a frontier model can system architecture recover?**

The working hypothesis is that a meaningful fraction of the apparent "model intelligence" required for practical security work can be moved out of the model and into deterministic infrastructure: evidence preparation, tool routing, state, scope enforcement, decomposition, retrieval, verification, replay, recovery, and closed-loop red/blue evaluation.

This does not imply that architecture can eliminate model-capability limits. The research goal is to measure which deficits are recoverable, which are not, and at what cost.

## Design principle

Treat the model as an untrusted reasoning component embedded inside a deterministic evidence-and-authority machine.

The model may reason and propose. The host owns:

- identity and admission;
- evidence provenance;
- visible tool surface;
- effect and target authorization;
- execution;
- state transitions;
- verification;
- receipts;
- closure;
- promotion and training decisions.

This separation should remain true even if the model becomes much stronger.

## Relationship to Daybreak

This project is not a reimplementation of OpenAI Daybreak, Defense Factory, or Red Team and does not claim parity with those systems.

The useful ideas to reproduce at local scale are the workflow functions:

1. canonical security findings;
2. reproducible execution environments;
3. a shared evidence fabric;
4. bounded workflow skills rather than giant prompts;
5. red -> blue -> red validation loops;
6. persistent state and receipts;
7. continuous evaluation and remediation.

The hosted infrastructure scale, multi-tenant control plane, specialized proprietary cyber models, and large agent fleets are explicitly out of scope.

## Existing Haven foundations

### Local Defense Factory (HDF)

HDF is the blue/remediation kernel.

Current conceptual flow:

```text
scanner / deterministic analyzer
            |
            v
     structured finding
            |
            v
    evidence normalization
   file SHA + line evidence
            |
            v
    host-owned fix packet
 finding + exact allowlist
            |
            v
         local model
      patch proposal only
            |
            v
     deterministic patch gate
            |
            v
  disposable Git worktree
            |
            v
     host-owned recipes
    test / scan / regression
            |
            v
     cryptographic receipt
            |
            v
      workflow controller
            |
            v
      verified candidate
            |
            v
    landed-commit verifier
            |
            v
           closed
```

A passing disposable-worktree repair proves only a verified candidate. Closure requires evidence that the exact intended repair landed in an authoritative commit and still passes the prescribed integrated retest.

### Local Red Factory (HRF)

HRF is the adversarial-behavior/evaluation kernel.

Current conceptual flow:

```text
             host case generator
                     |
          deterministic synthetic case
                     |
          +----------+----------+
          |                     |
   trusted evidence      adversarial evidence
          |                     |
          +----------+----------+
                     v
              local model / Hermes
                     |
          +----------+----------+
          |                     |
    model intent           actual dispatch
    capture proxy           MCP trace
          |                     |
          +----------+----------+
                     v
           deterministic grader
                     |
                bound receipt
```

The critical distinction is **intent vs execution**. A model may propose an unauthorized action while the runtime successfully prevents the dispatch. Those are two different failures/successes and should be measured separately.

### Shared guarded runtime

HDF and HRF should reuse one common execution and evidence substrate rather than invent separate runtimes.

Conceptual flow:

```text
local model
   |
exact model/server admission
   |
Hermes
   |
context + tool routing
   |
exact model-visible tool surface
   |
pre-dispatch scope gate
   |
raw MCP/final-dispatch gate
   |
tool implementation
```

Cross-cutting controls include:

- model/server/GGUF identity;
- effective context;
- evidence admission and provenance;
- exact tool visibility;
- principal/effect/target scope;
- process ownership;
- hard timeout and descendant termination;
- crash recovery;
- private receipts;
- controlled evaluation;
- negative controls;
- target-machine qualification.

## Target architecture: Haven Continuous Security Factory

```text
                         HAVEN FACTORY
                              |
                  +-----------+-----------+
                  |                       |
            FACTORY CONTROL          FACTORY STATE
                  |                       |
          scheduler / policy       assets / findings
          approval / routing       evidence / owners
          model admission          runs / receipts
                  |                       |
                  +-----------+-----------+
                              |
                     EXECUTION PLANE
                              |
        +---------------------+---------------------+
        |                     |                     |
   WORKTREES              CONTAINERS             LABS
   code repair          app reproduction       AD / Azure /
                                              network labs
        |                     |                     |
        +---------------------+---------------------+
                              |
                    GUARDED AGENT RUNTIME
                              |
                  local model(s) / Hermes
                              |
                     bounded workflow skills
                              |
                       exact tool scope
                              |
                   host-owned dispatch
                              |
                     evidence receipts
```

Over the execution/control substrate:

```text
            +-------------------------------+
            |                               |
       BLUE FACTORY                    RED FACTORY
            |                               |
 inventory / triage                  challenge / validate
 remediation                        adversarial evaluation
 verification                       stress runtime guards
            |                               |
            +---------------+---------------+
                            |
                     CANONICAL FINDINGS
                            |
                     EVIDENCE GRAPH
                            |
                  evaluation / training
```

Training remains outside the authority loop. Qualified traces may become training candidates only after the evaluation, evidence, privacy, and reserve gates permit it.

## Canonical objects

The first integration layer should normalize the factories around a small durable object model.

### Asset

Identifies the thing under study:

- repository / commit;
- service / application;
- host / lab;
- identity / tenant;
- model / runtime;
- synthetic fixture.

### Finding

A durable security or behavior claim with lifecycle state.

Suggested fields:

- finding_id;
- source;
- asset_id;
- class / family;
- severity;
- status;
- creation provenance;
- current representative evidence;
- duplicate/canonical relationship;
- current owner;
- current verification state.

### Evidence

Evidence should be first-class, not prose pasted into a prompt.

Suggested fields:

- evidence_id;
- source type;
- source identity/version;
- target/asset;
- authenticated principal where relevant;
- timestamp;
- content/artifact hash;
- admissibility status;
- authority/freshness metadata;
- privacy classification;
- parent evidence / derivation;
- raw artifact reference.

### Run

Represents one bounded execution:

- exact workflow/skill;
- exact model/runtime identity;
- exact visible tools;
- exact authorization policy;
- exact input/evidence hashes;
- environment identity;
- timestamps;
- result artifacts;
- exit/timeout/recovery state;
- receipt hash.

### Fix

Binds a proposed remediation to:

- finding;
- base state/commit;
- exact patch;
- touched objects/files;
- allowed scope;
- proposer/model identity;
- validation receipt.

### Verification

Binds the claim that a result passed to independent host evidence:

- verification policy;
- environment;
- checks;
- adversarial retest;
- expected/actual state;
- integration identity;
- receipt.

## Workflow skills

Avoid giant "do security" prompts. Use bounded skills with explicit contracts.

Candidate skills:

- inventory_asset;
- triage_finding;
- gather_evidence;
- validate_finding;
- reproduce_finding;
- identify_owner;
- prepare_fix;
- verify_fix;
- adversarial_retest;
- close_finding.

Each skill should declare:

- input schema;
- required evidence;
- visible tools;
- effect/target scope;
- output schema;
- timeout;
- retry/recovery policy;
- approval requirements;
- verifier.

The orchestrator may select skills; selection must not widen permissions.

## Red -> Blue -> Red loop

A core integration target is a closed remediation loop:

```text
RED
 |
discover/reproduce failure
 |
 v
canonical finding
 |
 v
BLUE
 |
propose remediation
 |
 v
deterministic verification
 |
 v
RED
 |
repeat original adversarial case
 |
 +----------+
 |          |
FAIL       PASS
 |          |
reopen    verified candidate
            |
            v
       landed-state check
            |
            v
          closed
```

The original red evidence and the remediation verification should remain independently inspectable. The model under test must not certify its own success.

## Reproducible execution plane

Factory jobs should execute in the smallest environment sufficient for the task.

Initial backends:

- GitWorktreeEnvironment;
- ContainerEnvironment;
- SyntheticToolEnvironment.

Possible later backends:

- VMEnvironment;
- LocalADLabEnvironment;
- CloudTenantLabEnvironment.

Common interface:

```text
create()
bind_inputs()
run()
collect_receipts()
destroy()
```

Every environment should bind exact source/version, policy, model, tools, and artifacts. Cleanup is part of the receipt, not an assumption.

## What not to reproduce

Do not optimize for parity with the hosted Daybreak service.

Initially avoid:

- large multi-agent fleets;
- Kubernetes for its own sake;
- multi-tenant infrastructure;
- generalized cloud credential brokerage;
- arbitrary autonomous offensive operations;
- massive scanner breadth;
- a new shell runtime;
- model-authored verification;
- proprietary-model imitation.

The intended local scale is modest:

- one Mac operator;
- one Haven server / workstation;
- one to a few local model workers;
- GitHub;
- SQLite/Postgres if persistence needs it;
- worktrees/containers/labs;
- strong receipts.

## Build order

### Factory 0 — unify state

Create canonical Asset, Finding, Evidence, Run, Fix, and Verification records.

Map HDF and HRF into the same lifecycle without changing their existing semantics.

### Factory 1 — environment abstraction

Generalize disposable execution into a small environment interface. Start with worktrees, containers, and synthetic tool environments.

### Factory 2 — bounded workflow skills

Express triage, validation, remediation, verification, and retest as typed skills with explicit authority.

### Factory 3 — controller

Provide a host-owned workflow engine, conceptually:

```text
haven factory run finding <id>
```

The controller moves artifacts between skills and verifies contracts; it does not silently grant the model broader tools.

### Factory 4 — continuous mode

Only after the deterministic core is stable:

- GitHub event ingestion;
- scheduled scans;
- new-finding triggers;
- commit-change triggers;
- recurring red retests.

## Primary research program

The factory should become an instrument for answering:

> **How much of the capability gap can system architecture recover for a 4B local model?**

Candidate comparison arms:

- raw 4B;
- 4B + structured prompt;
- 4B + retrieval/evidence preparation;
- 4B + Hermes;
- 4B + exact tool routing/scope;
- 4B + decomposition/controller;
- 4B + deterministic verifier/retry;
- 4B + full Haven architecture;
- trained 4B + Haven architecture;
- larger local model(s);
- frontier reference model(s), where permitted.

Measure more than final task accuracy:

- answer/finding correctness;
- evidence precision and provenance violations;
- tool selection;
- wrong-target calls;
- unauthorized intent;
- unauthorized execution;
- redundant calls;
- recovery from tool errors;
- fix correctness;
- regression rate;
- red-retest survival;
- verifier intervention rate;
- human intervention rate;
- wall time;
- tokens;
- memory/context use;
- compute/energy/device time;
- architecture overhead.

The goal is a capability-recovery curve, not a single benchmark score.

## Working hypotheses

1. **Evidence preparation and deterministic retrieval will recover a large fraction of factual/security-analysis performance.**
2. **Exact tool routing and host-owned state will recover more reliable tool use than prompt-only instruction.**
3. **Task decomposition will disproportionately help small models by reducing simultaneous state and planning burden.**
4. **External verification/retry can recover execution correctness even when first-pass proposal quality remains below frontier models.**
5. **Architecture will recover less of genuinely novel long-horizon reasoning, ambiguous causal inference, and unseen exploit synthesis.**
6. **The strongest 4B system may beat a much larger raw model on bounded operational tasks while still losing badly on open-ended reasoning.**
7. **The right metric is not "4B equals frontier model." It is "what percentage of useful system-level performance can be recovered per unit of compute, latency, and human supervision?"**

## Research discipline

For every claimed gain distinguish:

- model improvement;
- prompt/context improvement;
- retrieval improvement;
- tool/runtime improvement;
- verification improvement;
- retry/search improvement;
- training improvement.

Do not credit architecture for hidden model changes or credit the model for host-provided answers.

Maintain independent evaluation and reserve boundaries. Development factories may generate training candidates, but promotion requires the existing qualification process.

## Success criterion

A successful Haven Factory does not need to make a 4B model universally frontier-class.

It succeeds if it can show, reproducibly, that for a meaningful class of real operational security tasks:

1. a small local model plus well-designed architecture reaches materially higher end-to-end reliability than the raw model;
2. the remaining failure modes are measurable and bounded;
3. unauthorized behavior is prevented independently of model compliance;
4. remediation is independently verified;
5. the resulting system is cheaper, more private, or easier to operate locally than using a large model for every step.

That would be a substantive systems result even if substantial capability gaps remain.
