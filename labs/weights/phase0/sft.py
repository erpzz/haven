"""Per-turn SFT rows from harness records, shared by every arm (O, A, B, C).

Format: tool_sft/run.py's rows ({episode, family, source, turn, messages}; the last message
is the assistant target), so PR #95/#45 trainers read them unchanged. Two differences, both
needed because the training records come from the *full* harness:

* A verifier-rejected first answer is never a target. In a corrected episode the rejected
  answer stays in the prefix of later turns (that is what the model saw), but no row trains
  on it.
* Each row records `teacher`, `arm`, `outcome` and `corrected`, so arms can be filtered and
  the "B without Astra" arm can drop one teacher's rows exactly.
* Weighting (Amendment 1, section 3, frozen): each episode contributes a total weight of 1.0,
  split equally across its kept traces. Every row of a trace carries that trace's weight in
  `trace_weight`; the trainer scales each row's loss by it. Agreement between teachers decides
  which traces are kept, never an episode's total weight.
"""
from __future__ import annotations

import collections


def rows_from_record(record: dict, *, source: str, arm: str, teacher: str | None = None,
                     episode_id: str | None = None, trace_id: str | None = None) -> list[dict]:
    messages = record["messages"]
    episode_id = episode_id or record["episode"]
    trace_id = trace_id or f"{episode_id}|{teacher}|{record.get('attempt', 0)}"
    rejected_index = None
    if record.get("corrections_used"):
        # the first final answer, i.e. the assistant turn right before the correction message
        for i, m in enumerate(messages):
            if m["role"] == "user" and m["content"].startswith("[runtime verifier]"):
                rejected_index = i - 1
                break
    rows, corrected = [], False
    for i, m in enumerate(messages):
        if m["role"] == "user" and i > 1:
            corrected = True
        if m["role"] != "assistant" or i == rejected_index:
            continue
        rows.append({"episode": episode_id, "family": record["family"], "source": source, "arm": arm,
                     "teacher": teacher, "trace": trace_id, "turn": i, "outcome": record.get("outcome"),
                     "corrected": corrected, "messages": messages[:i + 1]})
    return rows


def apply_episode_weights(rows: list[dict]) -> list[dict]:
    """trace_weight = 1 / (kept traces of that episode). Returns the same rows, annotated."""
    traces = collections.defaultdict(set)
    for r in rows:
        traces[r["episode"]].add(r["trace"])
    for r in rows:
        r["trace_weight"] = 1.0 / len(traces[r["episode"]])
    return rows


def episode_weight_totals(rows: list[dict]) -> dict:
    """Sum of trace weights per episode (each trace counted once); must be 1.0 for every episode."""
    seen, tot = set(), collections.defaultdict(float)
    for r in rows:
        if (r["episode"], r["trace"]) not in seen:
            seen.add((r["episode"], r["trace"]))
            tot[r["episode"]] += r["trace_weight"]
    return dict(tot)


def query_row(q: dict, system: str, reply: str, *, source: str, arm: str, teacher: str | None = None) -> dict:
    return {"episode": q["id"], "family": q["family"], "source": source, "arm": arm, "teacher": teacher,
            "trace": f"{q['id']}|{teacher}|0", "trace_weight": 1.0, "turn": 2, "outcome": None, "corrected": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": q["question"]},
                         {"role": "assistant", "content": reply}]}
