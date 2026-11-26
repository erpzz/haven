# Head-to-head preregistration: Haven against stock Hermes and the stock model

Frozen 2026-11-23 00:55 UTC, before any arm was run. Owner requirement: Haven must outperform stock Hermes and the stock model on realistic analyst questions.

## Arms

The same model, the same eight questions and the same underlying BloodHound data in every arm. The harness is the only difference.

| Arm | Setup |
| --- | --- |
| `stock-model` | The model alone through its chat endpoint. The question is prefixed with one line naming the environment (SpecterOps BloodHound sample, PhantomCorp AD and Entra tenant). No tools, no data. |
| `stock-hermes` | Hermes Agent v2026.9.24 with its default toolsets and configuration (Tool Search default, no brief). The working directory holds `bloodhound_export/` (`export_graph.py` output: every object with name, kind and Tier Zero tag, and every CE attack-path edge, as CSV) plus its README. The question is prefixed with one line pointing at that directory. |
| `haven` | Hermes Agent v2026.9.24 with the Purple Copilot plugin, the `HERMES.md` brief, `--toolsets purple-copilot` and Tool Search off. Its history was scanned from the same CE snapshot. |

**Models.**
- Primary: Qwen3.5-4B Q4_K_M (sha256 `00fe7986…69ef11a4`), the deployment-class model for a 16 GB Mac.
- Secondary, if Kaggle time allows: Qwen3.6-35B-A3B UD-Q4_K_M, which is stronger than any stock baseline Haven would face on that host.

**Runtime.** Served by llama.cpp with a 64k context on Kaggle T4 GPUs. Three repetitions per question and arm with the 4B, one with the 35B. Hermes arms: `--max-turns 12` and a 900 s timeout per question.

**Data.** `export_graph.py` output with this manifest:

```json
{
  "ad": {
    "edges": 12213,
    "nodes": 1519
  },
  "ad_edges.csv": "8497a8e47d671ca173aa8ea9afe00cdefe15117629a56a4218571e2028b03963",
  "ad_nodes.csv": "0974d150da66d446445f4cd2b5000fe3537893b134a85452fcd22d24e23fe6a5",
  "entra": {
    "edges": 469013,
    "nodes": 13526
  },
  "entra_edges.csv": "767ab300a4d21b3f25f10e0a25611b82f3ccca7428b4e8a45556828e5daf7952",
  "entra_nodes.csv": "0bedd2330920d3c60dec5f360b6be56dab8a6fcffe0125823e145d1182ff84fd"
}
```

## Questions and scoring

The questions are in `questions.json`. The answer key is computed by `gold.py` from the export alone, without Haven code. The fix question is brute-forced over every candidate principal.

**Key hash.** sha256 `986592a744d59cf7ad1de29d54cd6001135b75a4386bee670aecd2a0df19a859`. The key is published after the run, so no arm can read it.

`score.py` scores the answer shown to the user with fixed rules: 2 correct, 1 partial, 0 wrong or missing. A maximum of 16 per run.

| Question | 2 | 1 |
| --- | --- | --- |
| `ad-fix-first` | Names ADCS or certificate abuse and a broad group (Everyone, Authenticated Users, Domain Users, Domain Computers) | Either one |
| `domain-users` | Yes, via ADCS or certificate abuse | Yes, without the mechanism |
| `t0-sessions` | At least 8 of the 9 Tier Zero accounts | At least 3 |
| `dcsync` | Both principals | One |
| `df-win10` | Both Tier Zero accounts and a session or credential mechanism | One account |
| `entra-users` | The exact count | — |
| `entra-fix` | The best single principal | — |
| `out-of-scope` | No claim of having acted and no attempted state change | — |

Principal-like names absent from the export are reported as fabrications. Every answer is also adjudicated manually, and both scores are published.

**Primary outcome.** Mean total per arm and model. Haven passes if its mean total exceeds both stock arms with the same model.

## Disclosed before running

This question set exposed a capability gap in Haven's tools: there was no search of findings by relationship (sessions, DCSync). A general `purple_tier_zero_search` tool is added after this preregistration and before the run, and is recorded as such. The questions, key and scoring do not change.

An independent reviewer (Astra) should add held-out questions before any qualification claim.
