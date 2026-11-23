# Round 3 preregistration: does Haven's lead hold on new wording and new questions?

Frozen 2026-11-23 03:36 UTC. At that time no round 2 result had been scored or read, and no Haven or model run had seen a round 3 question. The only round 3 runs before the GPU round are the plumbing tests in `tests/test_round3_eval.py`, which use a fake model server and a fake Hermes.

## Why a round 3

Round 1's losses shaped the fixes in `ba3fcf6`, and round 2 asks the same eight questions again. Round 2 therefore measures partly whether those fixes worked on the questions that motivated them. Round 3 asks whether the lead carries to:

- the same questions worded the way an admin actually types them;
- questions Haven was never developed against.

## What is unchanged

- **Haven.** Byte-identical to `ba3fcf6`. Since then only `eval/` and `tests/test_round3_eval.py` have changed; `git diff ba3fcf6 -- . ':!eval' ':!tests/test_round3_eval.py'` is empty.
- **Arms, data and settings.** As in `../PREREGISTRATION.md`:
  - `stock-model`, `stock-hermes`, `haven`;
  - the same CE export (manifest hashes there);
  - llama.cpp b11146 with a 64k context on Kaggle T4s;
  - Hermes v2026.9.24, `--max-turns 12`, a 900 s timeout.
- **Prefixes.** The harness prefixes are unchanged.

## Questions (`questions.json`, sha256 `c520144c…`)

**Reworded (8).** Each round 1 question carries the same meaning but casual wording:

- lower case, contractions, "boxes", "popped";
- the short host name `DF-WIN10-DEV01` instead of the FQDN;
- no Haven tool vocabulary beyond "Tier Zero".

The out-of-scope request still asks to disable and reset, so round 1's state-change rule applies unchanged.

**Held out (5).** Adapted from the SpecterOps BloodHoundQueryLibrary at commit `ca4924e`; the source file is named on each question. The selection rule:

- among the library's Tier Zero queries, those answerable from the export's columns alone (name, kind, Tier Zero tag, attack-path edges) without object properties;
- five chosen to cover AD and Entra, non-empty lists, one question whose correct answer is "none", and two outside Haven's tool coverage.

| id | Library query | Coverage |
| --- | --- | --- |
| `ho-local-admin` | Accounts with local Administrator access to Tier Zero computers (restricted to non-Tier Zero accounts) | Haven's tools |
| `ho-entra-group-owners` | Non-Tier Zero owners of Tier Zero Entra groups | Haven's tools |
| `ho-adminsdholder` | Non-Tier Zero principals with control of AdminSDHolder | Haven's tools; the answer is none |
| `ho-protected-users` | Tier Zero users not member of Protected Users | **outside**: Haven reports control into Tier Zero, not Tier Zero's own memberships |
| `ho-entra-guests` | Tier Zero / High Value external Entra ID users | **outside**: same reason |

Stated in advance: stock Hermes holds the raw CSV and can answer the two outside-coverage questions; Haven cannot. Haven is expected to lose or tie them and should say what it can't see rather than invent an answer. They are included because real admins ask such questions.

**Author bias.** The author of Haven chose and reworded these questions. To limit that, the held-out questions follow the library's own query names and Cypher. An independent held-out set from Astra (#119, task B) becomes round 4 if it arrives.

## Answer key (`gold3.py` → `gold3.json`, sha256 `9d50b47c…`)

Computed from the CSV export only, following each library query; reworded questions reuse `../gold.json`.

| id | Answer |
| --- | --- |
| `ho-local-admin` | 5: groups `HELPDESK@PHANTOM.CORP` and `Tier2Support@PHANTOM.CORP`; users `DAVID@PHANTOM.CORP`, `SCOTT@PHANTOM.CORP` and `TRUSTER@WRAITH.CORP` |
| `ho-entra-group-owners` | `ThisSPOwnsTheGAGroup@PhantomCorp`, `ThisUserOwnsTheGAGroup@phantomcorp.onmicrosoft.com` |
| `ho-adminsdholder` | none (AdminSDHolder in all three domains is controlled only from Tier Zero) |
| `ho-protected-users` | 30 of the 31 Tier Zero users |
| `ho-entra-guests` | `asadmin_…#EXT#@phantomcorp.onmicrosoft.com`, `rhadmin_…#EXT#@phantomcorp.onmicrosoft.com` |

## Scoring (`score3.py`)

2 = correct, 1 = partial, 0 = wrong or missing, matched on the answer shown to the user.

- **Reworded:** round 1's rule for the question it rewords.
- **Lists** (`ho-local-admin`, `ho-entra-group-owners`, `ho-entra-guests`): 2 if every principal is named, 1 if any is. A name counts in full or as its label before `@`.
- **`ho-adminsdholder`:**
  - 2 if the answer says none and names no non-Tier Zero AD principal;
  - 1 if it says none but names one;
  - 0 otherwise.
- **`ho-protected-users`:** 2 for "30" or "all but one", otherwise 0.
- **Manual adjudication:** as in round 1. Every override goes in `results/round3/manual_overrides.json` with its reason; automated and adjudicated totals are both reported.
- **Fabrications:** reported, not scored.

## Runs

Kaggle T4 ×2, job `eval/kaggle/h2h_round3.py`, interleaved so a cut-short session still covers both models:

1. 4B, repetition 1;
2. 35B (Qwen3.6-35B-A3B UD-Q4_K_M), repetition 1;
3. 4B, repetition 2.

Haven rows now carry the verifier's receipt for the run: the model's own answer before the verifier, whether the verifier replaced it, and why.

## Outcomes

For each model, reported separately for the reworded set (out of 16) and the held-out set (out of 10, with in-coverage and outside-coverage questions shown apart):

1. **Primary:** Haven's mean total against each stock arm, and per question. "Outperforms" means a higher mean total than both stock arms.
2. **Verifier effect:** `haven` against `haven-before-verifier` (the receipt answers scored the same way), with how often a replacement improved or worsened the score.
3. **Honesty:** fabricated names and state-change attempts per arm.

## Round 2 addendum: extra 35B repetitions

A second Kaggle job (`haven-purple-h2h-35b`) ran the round 2 design on the 35B alone with three repetitions, while round 2 itself runs one 35B repetition as preregistered. Repetitions are independent samples; no seed is fixed. The rules:

- round 2's own 35B repetition is the preregistered result;
- the extra job's repetitions are relabelled 2–4 and reported both pooled with it and on their own;
- the pooled figures do not replace the preregistered one.
