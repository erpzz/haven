# Query-writing evaluation: does a small model that writes the query beat a model that reasons?

**Status: development suite and harness built and self-checked. CPU smoke only, so no results yet.** This is
bet (a) in [issue #117](https://github.com/erpzz/haven/issues/117): the model translates the question,
and code does the formal reasoning.

## What it measures

Identity-security questions over synthetic Entra-style tenants (users, nested groups, service
principals, roles with `active`/`eligible` assignments and scopes, ownership). Seven families:

| Family | Question shape | Answer |
|---|---|---|
| direct_holders | who has a direct active assignment of role R | set |
| transitive_member | is user U in group G, including nesting | bool |
| effective_holders | users with role R, active and tenant-wide, by any path | set |
| eligible_only | eligible for R but not active by any path | set |
| stale_privileged | disabled users still holding a tier-0 role | set |
| owner_escalation | users who own a service principal holding a tier-0 role | set |
| transitive_count | distinct users in group G, including nesting | int |

Three arms on identical questions (the model arms use the same model, temperature 0, thinking off):
- **code**: no model. A rules-only parser (family keywords plus verbatim entity match) fills the reference
  query templates. This is the code-alone baseline from the assurance plan (issue #117, step 1). The model's
  job is to add correct answers over it.
- **cypher**: the model sees the schema and the question, writes one read-only query, and the embedded Kùzu
  engine (openCypher, `pip install kuzu`, no server) executes it. If the query fails, the model gets one retry
  with the error text; retries are counted.
- **prose**: the model sees the whole tenant as text and answers in JSON.

Gold answers come from plain Python graph traversal (`tenant.py`), not from Cypher. Hand-written reference
queries (`ORACLE_CYPHER`) must match the gold on every question, and `run.py check` and the tests enforce it
(84/84). Write and admin statements are refused before execution. Question selection keeps empty or false answers
from being a safe default (more than 60% non-trivial).

```sh
pip install kuzu
python3 run.py check
python3 -m unittest discover -s tests -v
python3 run.py eval --arm cypher --base-url http://127.0.0.1:PORT/v1 --label 4b-cypher --out R/4b-cypher.jsonl
python3 run.py eval --arm prose  --base-url http://127.0.0.1:PORT/v1 --label 4b-prose  --out R/4b-prose.jsonl
```

## Scoring rules

- **Each arm declares its own answer type** before scoring. The gold type is used only by the scorer.
  - The code arm takes its type from its parsed family.
  - The cypher arm declares it on a `TYPE:` line; if it omits one, the type is inferred from the result's shape (`type_declared` is recorded).
  - The prose arm's type is the JSON type of its answer.
  - A type mismatch is wrong. A test checks that no arm reads the gold type or the gold answer inside the timed block.
- **One end-to-end timer per question,** from request through model calls, query execution, any retry and parsing. Summaries report mean and p95.
- **Yes/no:** when an arm declares `bool` and its query returns a non-boolean row, any non-empty row means "yes" (adopted after the CPU smoke, before any real result).
- **Agreed with the assurance lane for the reserve (issue #117):**
  - A clarifying question earns full credit only when the evidence leaves a material ambiguity and the question asks for the detail that would resolve it. A generic or unnecessary clarification earns zero.
  - Either arm may abstain, but a parser miss earns zero, even when the right answer is "insufficient evidence". Earning that point requires naming the missing observation and why the source cannot settle the question.
  - The code arm's "unsupported" output is therefore a zero.

## First executed result: the development suite cannot discriminate

Code-alone scores **84/84** on the development suite in essentially zero time, because the questions are
templated and the parser was written against that wording. This is expected, and it is why the deciding test
is the assurance lane's reserve, with analyst phrasing, paraphrase variants and graph variants. A model arm
earns its place only by adding correct answers over code-alone on the reserve, under the 90% / 15 s p95 gates
agreed in #117.

## Limits (stated before any result)

- This is a development suite written by the lane that builds the system, so it can flatter the approach.
  The deciding evaluation is the independent held-out set on public BloodHound/EntraOps sample data that
  the assurance lane specifies and holds (issue #117). The reserved half must not enter this repository.
- The schema is simpler than BloodHound's real graph, and the query arm gets the schema while the prose arm
  gets the data; that difference is the point of the comparison, not a confound to remove.
- The prose arm's prompt grows with tenant size. At larger sizes the comparison shifts in the query arm's
  favour, so the size used must be reported.
