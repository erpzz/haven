"""Per-turn SFT rows from harness records, shared by every arm (O, A, B, C).

Format: tool_sft/run.py's rows ({episode, family, source, turn, messages}; the last message
is the assistant target), so PR #95/#45 trainers read them unchanged. Two differences, both
needed because the training records come from the *full* harness:

* A verifier-rejected first answer is never a target. In a corrected episode the rejected
  answer stays in the prefix of later turns (that is what the model saw), but no row trains
  on it.
* Each row records `teacher`, `arm`, `outcome` and `corrected`, so arms can be filtered and
  the "B without Astra" arm can drop one teacher's rows exactly.
"""
from __future__ import annotations


def rows_from_record(record: dict, *, source: str, arm: str, teacher: str | None = None,
                     episode_id: str | None = None) -> list[dict]:
    messages = record["messages"]
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
        rows.append({"episode": episode_id or record["episode"], "family": record["family"], "source": source,
                     "arm": arm, "teacher": teacher, "turn": i, "outcome": record.get("outcome"),
                     "corrected": corrected, "messages": messages[:i + 1]})
    return rows


def query_row(q: dict, system: str, reply: str, *, source: str, arm: str, teacher: str | None = None) -> dict:
    return {"episode": q["id"], "family": q["family"], "source": source, "arm": arm, "teacher": teacher,
            "turn": 2, "outcome": None, "corrected": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": q["question"]},
                         {"role": "assistant", "content": reply}]}
