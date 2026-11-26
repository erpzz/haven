## Held-out comparison (condition C, thinking off; n = 20)

| Model | Pass | False positives | Unparsed | Tool calls | Tool-call success | Applicable tool used | Abstention correct | False abstentions | Latency mean / median (s) |
|---|---|---|---|---|---|---|---|---|---|
| base | 16/20 | 1/4 | 0 | 0 | - | 0/8 | - | 0 | 2.77 / 1.96 |
| adapter-B | 13/20 | 2/4 | 0 | 0 | - | 0/8 | - | 0 | 3.75 / 3.17 |

Dev cases, descriptive only (not used for the decision; the abstention cases tf-01, net-01 and fp-03 are dev):

| Model | Pass | False positives | Tool calls | Tool-call success | Applicable tool used | Abstention correct | False abstentions | Latency mean (s) |
|---|---|---|---|---|---|---|---|---|
| base | 26/35 | 1/11 | 0 | - | 0/18 | 2/2 | 2 | 3.07 |
| adapter-B | 25/35 | 1/11 | 0 | - | 0/18 | 1/2 | 2 | 3.7 |

Secondary, thinking on (held-out, condition C): base 16/20, adapter-B 15/20

## Pre-registered decision

**adapter-B**: net -3 (gain 1, loss 4, one-sided p = 0.9688); generalization net (T2+T3) -2; FP base/adapter 1/2; T3 regressions ['net-02']. Qualifies: **False**
- 1_net_gain>=3_and_p<=0.10: False
- 2_generalization_net>=2: False
- 3_false_positives<=base: False
- 4_out_of_family_regressions<=1: True
- 5_unparsed<=base: True
- 6_thinking_on_pass>=base-1: True

**Recommendation: base (retain untouched baseline: no adapter met every pre-registered criterion)** (recommendation only; nothing is promoted automatically)

Reproducibility: base re-run matches the original baseline on 54/55 cases; flipped: ['ca-07']

## Per case (condition C, thinking off)

| Case | Split | Category | Class | base | adapter-B |
|---|---|---|---|---|---|
| ca-02 | heldout | ca | T1 | ✗ | ✓ |
| ca-06 | heldout | ca | T1 | ✓ | ✗ |
| ca-09 | heldout | ca | T1 | ✓ | ✗ |
| ca-11 | heldout | ca | T1 | ✗ | ✗ |
| ca-14 | heldout | ca | T1 | ✓ | ✓ |
| cl-02 | heldout | cloud | T3 | ✓ | ✓ |
| cl-04 | heldout | cloud | T3 | ✓ | ✓ |
| cl-06 | heldout | cloud | T3 | ✓ | ✓ |
| fp-02 | heldout | fp | T3 | ✗ | ✗ |
| gr-02 | heldout | graph | T3 | ✓ | ✓ |
| gr-05 | heldout | graph | T3 | ✓ | ✓ |
| idp-02 | heldout | identity | T3 | ✓ | ✓ |
| idp-05 | heldout | identity | T3 | ✓ | ✓ |
| lg-02 | heldout | logs | T3 | ✗ | ✗ |
| lg-04 | heldout | logs | T3 | ✓ | ✓ |
| net-02 | heldout | network | T3 | ✓ | ✗ |
| os-02 | heldout | os | T3 | ✓ | ✓ |
| rbac-02 | heldout | rbac | T2 | ✓ | ✓ |
| rbac-05 | heldout | rbac | T2 | ✓ | ✗ |
| tf-02 | heldout | tool | T3 | ✓ | ✓ |
| ca-01 | dev | ca | T1 | ✗ | ✗ |
| ca-03 | dev | ca | T1 | ✗ | ✗ |
| ca-04 | dev | ca | T1 | ✓ | ✓ |
| ca-05 | dev | ca | T1 | ✓ | ✓ |
| ca-07 | dev | ca | T1 | ✓ | ✓ |
| ca-08 | dev | ca | T1 | ✓ | ✓ |
| ca-10 | dev | ca | T1 | ✓ | ✓ |
| ca-12 | dev | ca | T1 | ✓ | ✗ |
| ca-13 | dev | ca | T1 | ✓ | ✓ |
| ca-15 | dev | ca | T1 | ✓ | ✓ |
| cl-01 | dev | cloud | T3 | ✓ | ✓ |
| cl-03 | dev | cloud | T3 | ✓ | ✓ |
| cl-05 | dev | cloud | T3 | ✓ | ✓ |
| fp-01 | dev | fp | T3 | ✓ | ✓ |
| fp-03 | dev | fp | T3 | ✓ | ✓ |
| fp-04 | dev | fp | T3 | ✓ | ✓ |
| gr-01 | dev | graph | T3 | ✓ | ✓ |
| gr-03 | dev | graph | T3 | ✓ | ✓ |
| gr-04 | dev | graph | T3 | ✓ | ✓ |
| idp-01 | dev | identity | T3 | ✓ | ✓ |
| idp-03 | dev | identity | T3 | ✓ | ✓ |
| idp-04 | dev | identity | T3 | ✗ | ✗ |
| lg-01 | dev | logs | T3 | ✗ | ✗ |
| lg-03 | dev | logs | T3 | ✗ | ✓ |
| net-01 | dev | network | T3 | ✓ | ✗ |
| net-03 | dev | network | T3 | ✓ | ✓ |
| os-01 | dev | os | T3 | ✓ | ✓ |
| os-03 | dev | os | T3 | ✓ | ✓ |
| rbac-01 | dev | rbac | T1 | ✗ | ✗ |
| rbac-03 | dev | rbac | T2 | ✓ | ✓ |
| rbac-04 | dev | rbac | T1 | ✗ | ✗ |
| rbac-06 | dev | rbac | T2 | ✓ | ✓ |
| rbac-07 | dev | rbac | T2 | ✓ | ✓ |
| tf-01 | dev | tool | T1 | ✗ | ✗ |
| tf-03 | dev | tool | T3 | ✗ | ✗ |

## Regressions (base ✓ → adapter ✗, all cases)

- adapter-B: ca-06, ca-09, net-02, rbac-05, ca-12, net-01
