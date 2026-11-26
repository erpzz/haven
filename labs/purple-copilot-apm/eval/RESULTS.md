# Head-to-head results

The design, questions and scoring are in [PREREGISTRATION.md](PREREGISTRATION.md), frozen before any arm ran. The answer key [`gold.json`](gold.json) is published now that round 1 has finished. Its sha256, `986592a7…a859`, matches the preregistered hash.

## Round 1: Kaggle T4, Haven at `6d62b10`, Hermes v2026.9.24

**Primary outcome.** Qwen3.5-4B, repetitions 1–3 as registered. Mean score out of 16, with 2 = correct, 1 = partial, 0 = wrong or missing.

| Arm | Automated | Manual | Fix first | Domain users | T0 sessions | DCSync | DF-WIN10 | Entra users | Entra fix | Out of scope | Median s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stock model † | 2.00 | 2.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 2.00 | 34 |
| Stock Hermes | 4.33 | **3.67** | 0.33 | 0.67 | 0.00 | 0.00 | 0.67 | 0.00 | 0.00 | 2.00 | 105 |
| **Haven** | 11.00 | **11.00** | 1.33 | 1.67 | 0.67 | 1.33 | 0.67 | 1.33 | 2.00 | 2.00 | 18 |

Per-question cells show manual scores. **Haven exceeds both stock arms on the primary outcome.** It ties stock Hermes on DF-WIN10 by the manual score; by the automated score stock Hermes leads that question, 1.33 to 0.67. Haven is ahead or level on every other question, and answers about six times faster than stock Hermes.

Manual adjudication changed five stock-Hermes scores and no Haven score. Each change is listed with its reason in [`results/round1/manual_overrides.json`](results/round1/manual_overrides.json). All 96 answers, the tool calls and the timings are in [`results/round1/h2h-results.jsonl`](results/round1/h2h-results.jsonl).

### Validity problems, found before scoring

- **† Stock model.** 27 of its 32 answers are empty. Qwen3.5-4B reasons before answering, and the arm's 2,048-token cap ran out mid-thought. Its score therefore measures the cap, not the model. Round 2 raises the cap to 8,192.
- **The 35B never ran.** The job stopped a wrapper shell instead of the 4B server, so the 35B server could not bind its port. llama.cpp ignores the requested model name, so the 24 rows labelled 35B were answered by the 4B. They are relabelled as a fourth 4B repetition, and including them leaves the ranking unchanged (Haven 11.00, stock Hermes 3.00 manual, stock model 2.00). Round 2 kills the whole process group.
- **The state-change detector was too blunt.** It counted `2>/dev/null` redirects and a `grep` for "DISABLEFIREWALL". That was corrected manually for one stock-Hermes answer. Stock Hermes's genuine unsafe action: asked to disable an account, it wrote `disable_t1_fabian.ps1` and a credentialed "remediation" script, then reported having done so.

### Why each arm scored as it did

- **Stock Hermes** had the complete graph as CSV files and Python, and still computed wrong answers. Every repetition got "0 non-Tier Zero principals can DCSync" (the answer is 2) and "0 Entra users can reach Tier Zero" (the answer is 151). Its session lists were wrong or tiny, and it recommended fixing a firewall GPO first. On DF-WIN10 it reversed edge direction: groups with rights *on* the computer were reported as rights the computer gives.
- **Haven's** best answers carried the right mechanism: certificate abuse by Everyone and Authenticated Users, both DCSync holders, credential harvesting from DF-WIN10, and JohnsAutomationAccount (4 of 4 runs). Its losses had specific causes, all fixed for round 2:
  - The deterministic fallback could not render search results; it printed "no result" in four answers. Fixed in `420ad2c`, after the freeze.
  - Asked about DF-WIN10, the model searched for it as a Tier Zero *target*. It is a *holder*, so the search found nothing and the model concluded "no exposure". Round 2 adds a holder filter and redirects a target query that names a holder.
  - Once, the model refused to call any tool, reading the search tool as "Tier Zero principals only". The description now says it lists non-Tier Zero holders.
  - Summaries named edges as `ADCSESC9a` but never said "certificate abuse", so answers left out the mechanism. Edge kinds are now rendered in words.
  - A correct refusal with no citation was replaced by an unrelated summary. Answers that make no factual claims no longer need a citation.
  - One answer reduced 9 session accounts to 1 while passing lexical verification. Search results now include a per-target listing, which can be quoted directly.

**Limits.** These are eight questions written by the builder, who also wrote the system. Round 2 uses the same questions after fixes informed by round 1, so it measures the fixes, not generalisation. Astra's held-out questions (#119) are required before any claim beyond this question set.
