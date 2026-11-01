### Run `qwythos-think-v1`: model `qwythos-9b-v2-q4km`, thinking on

| Condition | Pass | Held-out pass | False positives (of eligible) | Unparsed | Tool calls | Bad / hallucinated tool calls | Hallucinated results | Tool calls per success | Prompt / completion tokens | Latency (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 42/55 (76%) | 14/20 | 2/15 | 0 | 0 | 0 / 0 | 0 | - | 72067 / 44222 | 4241 |
| B | 45/55 (82%) | 18/20 | 0/15 | 1 | 0 | 0 / 0 | 0 | - | 104379 / 50279 | 4810 |
| C | 49/55 (89%) | 16/20 | 0/15 | 0 | 1 | 0 / 0 | 0 | 0.02 | 143531 / 53739 | 5243 |

Paired comparisons (exact McNemar on scenarios present in both conditions):

- A → B: +3 passes; only-A 2, only-B 5, p = 0.453 (n = 55)
- B → C: +4 passes; only-B 2, only-C 6, p = 0.289 (n = 55)
- A → C: +7 passes; only-A 1, only-C 8, p = 0.039 (n = 55)

| Category | A | B | C | Dominant gap |
|---|---|---|---|---|
| ca | 11/15 | 13/15 | 12/15 | knowledge 2, orchestration 1, tool 1 |
| cloud | 3/6 | 5/6 | 6/6 | knowledge 2, tool 1 |
| fp | 4/4 | 4/4 | 4/4 | none |
| graph | 5/5 | 5/5 | 5/5 | none |
| identity | 5/5 | 4/5 | 5/5 | none |
| logs | 1/4 | 2/4 | 2/4 | orchestration 2, knowledge 1 |
| network | 3/3 | 3/3 | 3/3 | none |
| os | 3/3 | 3/3 | 3/3 | none |
| rbac | 5/7 | 5/7 | 6/7 | orchestration 1, tool 1 |
| tool | 2/3 | 1/3 | 3/3 | tool 1 |

Gap attribution over 55 scenarios: known 42, knowledge 5, orchestration 4, tool 4

<details><summary>Per-scenario attribution</summary>

| Scenario | Category | Split | A | B | C | Gap | C tools used |
|---|---|---|---|---|---|---|---|
| ca-03 | ca | dev | ✗ | ✗ | ✗ | orchestration | - |
| ca-06 | ca | heldout | ✗ | ✓ | ✗ | knowledge | - |
| ca-09 | ca | heldout | ✗ | ✓ | ✓ | knowledge | - |
| ca-12 | ca | dev | ✗ | ✗ | ✓ | tool | - |
| cl-01 | cloud | dev | ✗ | ✓ | ✓ | knowledge | - |
| cl-03 | cloud | dev | ✗ | ✗ | ✓ | tool | - |
| cl-04 | cloud | heldout | ✗ | ✓ | ✓ | knowledge | - |
| lg-01 | logs | dev | ✗ | ✗ | ✗ | orchestration | - |
| lg-02 | logs | heldout | ✗ | ✗ | ✗ | orchestration | - |
| lg-04 | logs | heldout | ✗ | ✓ | ✓ | knowledge | - |
| rbac-01 | rbac | dev | ✗ | ✗ | ✓ | tool | - |
| rbac-05 | rbac | heldout | ✗ | ✗ | ✗ | orchestration | - |
| tf-01 | tool | dev | ✗ | ✗ | ✓ | tool | run_command |

</details>

