### Run `qwythos-nothink-v1`: model `qwythos-9b-v2-q4km`, thinking off

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
