# Adjudicated tool-use benchmark

Until this benchmark, every Haven capability number came from one generator
(`distillation/tool_sft/world.py`) scored by a lexical verifier, and that verifier accepts some
explicitly negated correct answers. This directory is the independent, adjudicated suite that
`design/HS01/ARCHITECTURE_BREAKTHROUGH_THESIS_20261026.md` §4 asks for before any breakthrough
claim.

- **Independent generator** (`generator.py`). It has its own households, vocabulary, scenario
  structures and wording. It shares only the tool contract with tool_sft: the four tool names
  and schemas, `world.dispatch`, and the bakeoff system prompt via `agent.py`. No identifier
  overlaps tool_sft's vocabulary, and a test checks this. 15 families × 12 = **180
  episodes**, frozen in `frozen/episodes.jsonl`.
- **Adjudication, not keywords** (`adjudicator.py`, rubric in [ADJUDICATION.md](ADJUDICATION.md)).
  Each episode is scored from the structured trace: required and forbidden calls, arguments,
  authority, guessed identifiers, call budget. The answer is scored from a JSON claims block
  (value, evidence_id, status) that is checked against tool outputs and the world. Negation,
  hedging, forged evidence and execution claims are rejected. A lexical fallback is reported
  only as a secondary metric.
- **Preregistered** (`PREREGISTRATION.json`). It holds the SHA-256 of the frozen episodes, the
  code, the shared contract and the claims instruction, plus the metrics, analysis plan,
  spot-check rule and the floor baselines. It was committed before any model was evaluated.
- **Same backends as tool_sft.** `bench.py eval` calls `agent.run_episode` and
  `run.make_backend`, so any loopback OpenAI-compatible server or local HF model can be scored.

## Use

```sh
python3 bench.py check                          # hashes, oracle 180/180, floor baselines
python3 -m unittest discover -s tests -v        # stdlib only, no model

# On the GPU host, one GPU owner at a time, records outside Git:
python3 bench.py eval --backend openai --base-url http://127.0.0.1:PORT/v1 --model haven-local \
  --api-key-file ~/.local/share/haven-model-lab/engine-key.txt --label ref-4b --out "$R/adj-4b.jsonl"
python3 bench.py spotcheck --records "$R/adj-4b.jsonl" --out "$R/adj-4b.spot.jsonl"
python3 bench.py agreement --worksheet "$R/adj-4b.spot.jsonl"   # after a human fills it in
python3 bench.py rescore --records "$R/adj-4b.jsonl" --out "$R/adj-4b.rescore.json"
```

`eval` refuses to run if the frozen file or the shared contract no longer matches the
preregistration, and it never overwrites a receipt. Raw records and spot-check worksheets hold
full transcripts; keep them private. Only sanitized summaries go in `results/`.

## Floors at freeze

| backend | pass /180 | lexical /180 |
|---|---|---|
| oracle (scripted plan) | 180 | 180 |
| silent (no calls, empty answer) | 0 | 0 |
| everything `unavailable`, no calls | 0 | 0 |
| everything `refused`, no calls | 12 (all `execute_refusal`) | 12 |
