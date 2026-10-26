# Verified-teacher tool SFT

Can a small local student learn Haven's tool contract from a large local
teacher, and keep that skill on tasks it never saw? This lab answers that with a
frozen, machine-checked measurement rather than a handful of hand-written
probes.

## Design

- **World** (`world.py`): every episode carries its own synthetic notes and
  devices, four read-only or inert tools (`haven_read_note`,
  `haven_list_resources`, `haven_device_state`, `haven_propose_action`), a
  prompt, a deterministic success contract and a scripted oracle plan. The
  runtime binds the authenticated principal; denied and missing results never
  reveal whether a private record exists.
- **Verifier**: required calls (optionally ordered), forbidden calls with a
  reason (`authority`, `substituted_proposal`, `unrequested_proposal`,
  `unneeded_tool`), a call budget, required evidence (value, `evidence_id`, the
  *returned* `proposal_id`), and forbidden answer content (`leak`, `exec_claim`,
  `invented_cause`, `stale`). The oracle passes all 550 frozen episodes and a
  silent model passes none (`tests/test_tool_sft.py`).
- **Splits** (`frozen/`, hashes in `PREREGISTRATION.json`):
  - train: 400 episodes from 10 families;
  - dev: 40 fresh instances, for debugging only;
  - held-out paraphrase: 60 episodes from the same 10 families, with disjoint
    principals, topics, devices, values and wording;
  - held-out composition: 50 episodes from 5 families never trained
    (`note_then_propose`, `discover_then_state`, `injected_note`,
    `compare_with_other`, `conditional_proposal`);
  - legacy: the original hand-written 8-task bakeoff, with its own three-tool
    interface and scorer.
- **One loop** (`agent.py`) serves the teacher (loopback OpenAI-compatible
  Strata or llama.cpp), the student (local HF generation with its own chat
  template) and the oracle. It reuses the existing bakeoff system prompt
  verbatim.
- **Training** (`train.py`): one example per assistant turn. The prefix is
  rendered with `add_generation_prompt=True`, exactly as the student sees it at
  inference, and only the target turn is labeled. A CPU check confirmed that the
  split falls precisely at the generation prompt.
- **Control**: the oracle arm trains with identical settings and step count on
  scripted trajectories for exactly the episodes the teacher solved. Any gap
  between the two arms is therefore the teacher's contribution beyond templates.

## Reproduce

Run the following on the GPU host, writing to a private directory outside Git.
Only one GPU owner at a time.

```sh
python3 run.py eval --backend openai --base-url http://127.0.0.1:PORT/v1 --model haven-local \
  --api-key-file ~/.local/share/haven-model-lab/engine-key.txt --label ref-4b \
  --sets heldout,legacy --out "$R/eval-ref4b.jsonl"            # while the 4B is loaded
python3 ~/projects/haven/ops/haven-core/labctl.py unload
$VENV/bin/python run.py eval --backend hf --model Qwen/Qwen3-0.6B --revision c1899de2... \
  --label base --sets dev,heldout,legacy --out "$R/eval-base.jsonl"
python3 teacher_session.py --out "$R" --execute               # ~15 min cold start, then collect + ceiling, then stop
./run_arms.sh "$R"                                            # build, train both arms, evaluate, restore the 4B
python3 run.py compare --before "$R/eval-base.summary.json" --after "$R/eval-teacher-sft.summary.json"
```

`rescore` re-verifies saved records after a disclosed contract amendment;
it never reruns inference.
