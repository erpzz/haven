# secpatch forge: a security model that keeps teaching itself

The forge turns the secpatch dataset (real, license-checked Python security fixes from OSV) into a loop that
improves a local security-review model without a person, Claude, Codex or paid credits in the loop. It runs on
Slink under a systemd user timer and uses free compute: Kaggle's weekly 2x T4 quota and Slink's own GPU.

## Where it started (Codex's Kaggle run, 2026-10-30)

`haven-r02-secpatch-cuda-reference` trained Qwen3-0.6B with LoRA r16 for 60 optimizer steps (0.34 of an epoch)
and evaluated 12 held-out fixes (72 rows):

| | score | detect recall | FPR on fixed code | paired detect | root cause |
|---|---|---|---|---|---|
| base 0.6B | 0.458 | 0.83 | 1.00 | 0.00 | 0/12 |
| + adapter | 0.486 | 0.08 | 0.17 | 0.08 | 0/12 |

The +2.8 points are one or two items inside overlapping Wilson intervals. The adapter mostly learned to answer
"not vulnerable": recall fell from 0.83 to 0.08. The run was sound infrastructure, with pinned inputs, receipts
and real CUDA evidence, but it was not a model. The targets were also weak. Detection "issues" were truncated
advisory text, root-cause "fixes" were commit subjects, and nothing taught the model *why* a line is vulnerable.

## What the forge changes

1. **Reasoning, verified against ground truth.** GLM-4.7-Flash (MIT, open weights) sees each training row with
   its recorded answer and the real patch diff. It writes the short, code-grounded analysis an engineer would
   reach from the code alone. A trace is kept only if every check holds (`teach.py`):
   - the teacher's verdict, support decision or CWE matches the record;
   - every cited line number is in the code shown;
   - it names an identifier the patch actually changed and that the student can see;
   - it never mentions the reference, the advisory, or (for vulnerable code) a later patch;
   - every backticked identifier exists in the prompt.

   Verdicts, CWEs and evidence lines in the target always come from ground truth.
2. **More data, cleaner splits** (`mix.py`). The dev split, which was previously unused, is divided by
   repository. Half joins training (339 fixes, 2,287 rows, vs 257). The other half becomes a 115-fix,
   804-row promotion gate. A gate repository's older fixes leave training too, so no repository is both
   trained on and judged. The 37-fix held-out set stays untouched.
3. **A bigger student, shipped as it is served.** Qwen3.5-4B (Haven's default local model) is trained with
   QLoRA on both T4s. It is merged into the original checkpoint layout, converted to GGUF Q4_K_M, and graded
   through llama-server: the same file Haven would run. The base and the current champion go through the
   identical convert/serve path in the same session.
4. **Self-teaching.** After each training run, the student answers every training row 4 times at temperature
   0.8. Answers that the recorded ground truth accepts become SFT rows for the next cycle, and correct/incorrect
   pairs are saved for preference training (`evalrun.py selfplay`). This costs no credits and needs no teacher.
5. **Promotion only on evidence** (`loop.py` gate). The student must beat the champion (or the base, at
   cycle 0) on gate + held-out together, under a cluster bootstrap over fixes with p < 0.1. The detection
   false-positive rate may not rise by more than 2 points, and the held-out score may not drop by more than
   2 points.
6. **Fresh data every week.** The OSV export is re-fetched and new fix commits are harvested (resumable).
   The dataset is rebuilt with the unchanged secpatch pipeline. New advisories land in dev/held-out
   repositories by the existing rules, so the test sets keep moving forward in time and stay uncontaminated.

## Running it

Everything lives on Slink:

| path | what |
|---|---|
| `~/.local/state/haven-forge/code/` | deployed copy of `forge/` and the secpatch scripts |
| `~/.local/state/haven-forge/state.json` | loop state (cycle, step, champion, gate history) |
| `~/.local/state/haven-forge/logs/loop.jsonl` | one line per event |
| `~/.local/state/haven-forge/cycles/cNNN/` | data, teacher traces, kernel outputs, `gate.json` |
| `~/.local/state/haven-forge/config.override.json` | optional overrides merged over `config.json` |

```bash
systemctl --user list-timers haven-forge.timer      # ticks every 20 min
python3 ~/.local/state/haven-forge/code/forge/loop.py status
tail -f ~/.local/state/haven-forge/logs/loop.jsonl
systemctl --user status forge-teacher-server forge-teach-slink   # Slink teacher lane
```

Secrets: Kaggle `~/.kaggle/access_token`; Hugging Face `~/.config/haven/hf_token` (used only to upload
promoted adapters and GGUFs to the private `hf_repo`). The HF account currently has no Inference Providers or
Jobs credits, so neither is used. With credits, the HF router (e.g. GLM-5.3) can serve as a stronger
`teach.py --base-url`, and an A100 job can replace the T4 trainer; nothing else changes.

The Slink lanes run at CPUWeight 1 and Nice 19 next to the interactive chat model. The teacher keeps its
experts on the CPU and uses about 2.4 GB of the 2070 Super's spare VRAM. The live chat model is never
switched automatically. Promoted models are copied into the Model Lab models directory for the owner to
select.

## Limits

* Free Kaggle quota is about 30 GPU-hours a week. A cycle uses roughly 4–6 h of teaching and 8–11 h of
  training plus evaluation, so expect about one cycle a week.
* Graders are deterministic, but remediation is scored as "plausible": it parses, keeps its signature,
  changes the code and clears the Bandit rule. That is not proof the patch fixes the issue
  (`repo_eval.py` needs an isolated runner).
* GLM-4.7-Flash is a modest teacher. Verification removes wrong traces but cannot add insight the teacher
  lacks. A stronger teacher is the first upgrade when credits exist.
