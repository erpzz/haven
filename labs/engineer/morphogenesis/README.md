# Haven Morphogenesis — capability as verified, portable executables

## Hypothesis

A system can accumulate useful ability without changing any model's weights, by keeping
**executable skills** that were (a) produced in response to an *observed* limitation, (b) admitted
only on held-out evidence by a harness the author cannot influence, and (c) inherited by agents
and machines that had no part in producing them. If this works, the unit of improvement is a
content-addressed program with provenance, not a parameter update, and a strong model's
contribution outlives its own inference.

## Mechanism: verified executable inheritance (VEI)

```
observe ──▶ brief ──▶ author ──▶ admit ──▶ inherit ──▶ measure ──▶ keep / retire
(ledgers)   (limit +   (any agent,   (held-out cases   (skill_* tool in   (preregistered
             contract)   isolated lab) in sandbox-denied  any executor, any   arms incl. a
                                       state; signed,     enrolled node, no   prose control)
                                       hash-addressed)    model required)
```

1. **Observe.** The executor ledgers are mined for repeated waste. First instance: in 3 of 3 local
   runs Qwen spent its first three commands discovering how to run tests.
2. **Brief.** The limitation, an interface contract and environment facts go to an author in an
   isolated workspace. The brief never contains held-out cases.
3. **Author.** Any agent; here Claude Code (Opus) through Haven's own executor, so the authoring
   itself has receipts (`skill-lab` task, 31 actions).
4. **Admit.** `skills.py` runs the candidate in the OS sandbox on cases stored in Haven's private
   state directory, which the sandbox denies to every agent. The harness, not the author, judges.
   Admission records are HMAC-signed and the skill is addressed by SHA-256 of its files; any change
   un-admits it everywhere.
5. **Inherit.** Admitted skills become tools (`skill_run_tests`) under the same policy, sandbox and
   receipts as any command, or ship to an enrolled node (`run-remote`) where they run with no model.
6. **Measure.** Preregistered comparison against two baselines: tools only, and the *same
   procedure as prose* (`recipe.md`) in the prompt. The prose arm is the key control: if prose does
   as well, executability is not what helps.
7. **Keep or retire.** Rejections are kept with reasons (`skills/rejected/`). A skill that loses on
   a later held-out set is retired, not patched in place.

## Relation to existing work (and what is different)

Skill libraries of code are not new: Voyager (2023) keeps JavaScript skills verified by the game
environment; DreamCoder/LILO/Stitch learn libraries by compression; LATM and CREATOR have a strong
model write tools for a weaker one; Agent Workflow Memory and ExpeL store reusable trajectories or
insights as text. VEI's differences are narrow and testable:

- **Admission is adversarially separated from authorship**: held-out cases are physically
  unreadable by the author's sandbox, and judgement uses the harness's comparison, not the author's.
- **Provenance is receipt-bound**: the authoring session's actions are in a signed ledger.
- **The prose control is built in**: every skill ships with an equivalent recipe, so each
  inheritance claim is also a test of "code vs. instructions".
- **Transfer is across architecture and machine**, and the receiving side may have no model.

## Experiments

| | Question | Status |
|---|---|---|
| E1 | Does an inherited executable skill help small local models on unseen tasks more than the same knowledge in prose? | preregistered (`PREREGISTRATION.json`), running |
| E1b | Does the admitted skill run on another enrolled machine with no model? | observed: Slink, Landlock sandbox, same content hash, correct structured result on an unseen pytest-style repo in 0.22 s; node:test case reports "node is not on PATH" honestly |
| E2 | Recursive or alternative controller vs. conventional agent on unseen tasks at matched compute | planned: a deterministic test-driven repair controller (run tests → localize from structured failures → ask the model only for a patch → re-run) vs. the free-form loop, same model and step budget |
| E3 | Specialized workers vs. one agent | pilot n=1 (two-module bug task): Qwen solo did not finish (2 of 3 failures fixed, 20-min limit, ~700 s of it waiting on approvals caused by a classifier bug); Opus supervising a Qwen child finished in 82 s; the child solved its leased sub-task. Confounded by supervisor strength; needs a same-model supervisor arm |
| E4 | Does placement/caching raise *task* throughput on Slink? | planned; peers measured token throughput (round 1). Blocked on a free GPU lease: the live Model Lab backend owns the GPU |

## Rejection criteria for VEI itself

VEI is rejected for a skill family if, on preregistered unseen tasks, the skill arm does not beat
the tools-only arm, or the prose arm matches the skill arm (executability adds nothing), or gains
disappear when the step budget is raised for the other arms (the skill only saves steps that a
larger budget buys back). Costs to report: authoring cost (hosted turns and wall time), admission
time, per-call runtime, and context added by the tool schema or recipe.

## Costs observed so far

Authoring: one Claude Code session on the owner's plan (31 executor actions; wall time in the task
record). Admission: 5 held-out cases in a few seconds on the Mac. Remote run: 0.35–0.45 s round trip
to Slink, 0.10–0.22 s on the node. The skill is 2,019 lines; that size is itself a risk (review cost).
