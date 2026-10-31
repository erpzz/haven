# Cyber capability matrix: Qwythos-9B-v2 baseline

**Setup.**
- Model: Qwythos-9B-v2 Q4_K_M on llama.cpp b11146 (Slink RTX 2070S, sharing the card with the forge teacher), temperature 0, single slot.
- Data: 55 scenarios across 10 categories (20 held out). Grading is deterministic against hidden answers (`haven_cyber/eval/grade.py`); no LLM judge.
- Conditions:
  - **A**: model with the task artifacts only;
  - **B**: A plus up to 3 retrieved, cited corpus sections (≤4.5K chars);
  - **C**: B plus five tools and an agent instruction;
  - **D**: C with a fine-tuned adapter (pending; see below).

Raw rows: `results/eval/<run>/results.jsonl`. Regenerate the tables with `python -m haven_cyber.eval.report results/eval/<run>`.

## Thinking off (`qwythos-nothink-v1`, 2026-10-31)

| Condition | Pass | Held-out pass | False positives (of eligible) | Unparsed | Tool calls | Bad / hallucinated tool calls | Hallucinated results | Tool calls per success | Prompt / completion tokens | Latency (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 38/55 (69%) | 15/20 | 3/15 | 0 | 0 | 0 / 0 | 0 | - | 72177 / 3461 | 365 |
| B | 38/55 (69%) | 14/20 | 3/15 | 1 | 0 | 0 / 0 | 0 | - | 104489 / 3861 | 340 |
| C | 41/55 (75%) | 16/20 | 3/15 | 0 | 0 | 0 / 0 | 0 | 0.00 | 141999 / 4545 | 419 |

Paired comparisons (exact McNemar on scenarios present in both conditions):

- A → B: +0 passes; only-A 5, only-B 5, p = 1.000 (n = 55)
- B → C: +3 passes; only-B 2, only-C 5, p = 0.453 (n = 55)
- A → C: +3 passes; only-A 3, only-C 6, p = 0.508 (n = 55)

| Category | A | B | C | Dominant gap |
|---|---|---|---|---|
| ca | 10/15 | 10/15 | 10/15 | orchestration 3, tool 1, knowledge 1 |
| cloud | 4/6 | 6/6 | 6/6 | knowledge 2 |
| fp | 3/4 | 3/4 | 3/4 | orchestration 1 |
| graph | 4/5 | 5/5 | 5/5 | knowledge 1 |
| identity | 4/5 | 3/5 | 4/5 | orchestration 1 |
| logs | 1/4 | 2/4 | 1/4 | orchestration 2, knowledge 1 |
| network | 3/3 | 1/3 | 3/3 | none |
| os | 3/3 | 2/3 | 3/3 | none |
| rbac | 5/7 | 5/7 | 5/7 | orchestration 2 |
| tool | 1/3 | 1/3 | 1/3 | orchestration 2 |

Gap attribution over 55 scenarios: known 38, orchestration 11, knowledge 5, tool 1

<details><summary>Per-scenario attribution</summary>

| Scenario | Category | Split | A | B | C | Gap | C tools used |
|---|---|---|---|---|---|---|---|
| ca-01 | ca | dev | ✗ | ✗ | ✗ | orchestration | - |
| ca-02 | ca | heldout | ✗ | ✗ | ✗ | orchestration | - |
| ca-03 | ca | dev | ✗ | ✗ | ✗ | orchestration | - |
| ca-06 | ca | heldout | ✗ | ✗ | ✓ | tool | - |
| ca-10 | ca | dev | ✗ | ✓ | ✓ | knowledge | - |
| cl-01 | cloud | dev | ✗ | ✓ | ✓ | knowledge | - |
| cl-05 | cloud | dev | ✗ | ✓ | ✓ | knowledge | - |
| fp-02 | fp | heldout | ✗ | ✗ | ✗ | orchestration | - |
| gr-03 | graph | dev | ✗ | ✓ | ✓ | knowledge | - |
| idp-04 | identity | dev | ✗ | ✗ | ✗ | orchestration | - |
| lg-01 | logs | dev | ✗ | ✗ | ✗ | orchestration | - |
| lg-02 | logs | heldout | ✗ | ✗ | ✗ | orchestration | - |
| lg-04 | logs | heldout | ✗ | ✓ | ✓ | knowledge | - |
| rbac-01 | rbac | dev | ✗ | ✗ | ✗ | orchestration | - |
| rbac-04 | rbac | dev | ✗ | ✗ | ✗ | orchestration | - |
| tf-01 | tool | dev | ✗ | ✗ | ✗ | orchestration | - |
| tf-03 | tool | dev | ✗ | ✗ | ✗ | orchestration | - |

</details>


[exited with code 0]

Mean latency per item: A 6.6 s, B 6.2 s, C 7.6 s (single request; prefill dominates). Retrieval adds about 600 prompt tokens per item; the five tool schemas add about 600 more.

### What this measurement says

1. **Qwythos does not use tools with thinking off.** It made zero tool calls in 55 condition-C items, although every item offered an applicable tool and the system prompt told it to gather evidence first. C's +3 over B therefore comes from the agent instructions changing its answers, not from tools. The difference is not significant (p = 0.45).
2. **Most failures are orchestration, not knowledge.** Of 17 scenarios failed in every condition or fixed only by retrieval, **11 are orchestration**: the scenario's tool returns the correct answer when called, but the model answered from its own reading. Five are **knowledge** gaps closed by retrieval (ca-10 emergency lockout, cl-01 two-switch public access, cl-05 subnet-then-NIC NSG evaluation, gr-03 ConsistencyLevel, lg-04 consent abuse), and one item (ca-06) flipped in C.
   - Orchestration failures: ca-01/02/03 (non-emergency exclusion, report-only, "other"-only), fp-02, idp-04, lg-01/02, rbac-01/04, tf-01/03.
3. **Its CA reading errors are the classic ones:**
   - treats `enabledForReportingButNotEnforced` as enforcing;
   - treats a block of `other` alone as covering Exchange ActiveSync;
   - accepts a non-emergency group exclusion;
   - flags emergency-account exclusions as gaps (ca-11 false positive).
   - The deterministic tools get all of these right: the assessor, and the independent verifier that `tests/test_eval_set.py` ties every CA label to.
4. **False positives: 3 per condition** out of 15 trap scenarios:
   - rbac-04 in every condition: "Reader grants blob data read";
   - cl-01 and cl-05 in A only, fixed by retrieval;
   - ca-11 in B/C;
   - net-02 in B;
   - ca-07 in C.
5. **No hallucinated tool output.** tf-01 (ports on a lab host) correctly answered `null` in A/B, where no tool can run. In C it also answered `null` without calling `run_command`, which is the orchestration failure in its purest form.
6. **Retrieval quality:** two misses traced to the query. rbac-04 did not retrieve "Built-in roles that matter"; lg-02 did not retrieve the sign-in failure patterns. Next retrieval step: expand the query with artifact keys (error codes, role names, operation strings).

### Known label issue (v1, frozen for comparability)

tf-03 offers both `user_lacks_role` and `missing_rbac_permission`, and an ARM `AuthorizationFailed` arguably fits both. The label (`missing_rbac_permission`) is kept for v1 so that adapter results stay comparable. Scored leniently, condition A–C would each gain +1 on tool. v2 renames the option to `user_lacks_directory_role`.

## Thinking on (`qwythos-think-v1`)

Running on Slink at the time of this commit (≈60–95 s per item). Smoke results: with thinking on, Qwythos *does* call tools (tf-01: five `run_command` calls; rbac-01 answered correctly). The table will be added from `results/eval/qwythos-think-v1` when the run completes.

## Gap → remedy

| Gap | Where it shows | Remedy | Owner |
|---|---|---|---|
| Orchestration: no tool use with thinking off | 11 scenarios, every category with a tool | **Agent-reliability LoRA** (Experiment A): 640 grader-verified trajectories over these tools; training on Kaggle since 2026-10-31 | forge session; scored here as condition D |
| Orchestration: incomplete JSON / missing citations | live slice (dropped `}`; no HCA ids or `[R#]` cited) | same adapter (every target ends in a complete JSON object); grounding check stays as a guard | forge + this lab |
| Knowledge: product semantics | 5 scenarios fixed by retrieval | keep in retrieval (corpus), not weights; extend the corpus | this lab |
| Retrieval misses | rbac-04, lg-02 | artifact-aware query expansion; measure as B-only delta | this lab |
| Reasoning under tools | not measurable until tools are used | re-measure after D | - |
| Permissions / live data | no tenant | `entra.graph.collect` and Resource Graph on an authorized lab tenant | owner decision |

## Condition D

Scheduled after the thinking-on baseline: the forge session serves both Kaggle adapters (agent-reliability v1 and secpatch c001), merged and quantized to Q4_K_M, with the same server flags, and runs this harness at the same commit. Promotion rule: held-out pass ≥ base, false positives ≤ base, per category.
