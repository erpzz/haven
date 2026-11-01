"""Deterministic grading against hidden ground truth (eval/answers/*.json). No LLM judge."""
from __future__ import annotations

import json
import re


def strip_reasoning(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    return text.split("</think>")[-1]


def extract_json(text: str) -> dict | None:
    """Return the last top-level JSON object in the text (models often add prose or code fences)."""
    text = strip_reasoning(text)
    best = None
    depth, start, in_str, esc = 0, None, False, False
    for i, ch in enumerate(text):
        if in_str:
            esc = (ch == "\\") and not esc
            if ch == '"' and not esc:
                in_str = False
            elif ch != "\\":
                esc = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(text[start:i + 1])
                    if isinstance(obj, dict):
                        best = obj
                except json.JSONDecodeError:
                    pass
    return best


def extract_json_lenient(text: str) -> tuple[dict | None, bool]:
    """Production parsing (not used for grading): if no complete object parses, close a truncated trailing object.
    Returns (object, repaired). Qwythos sometimes stops right before the final '}'."""
    obj = extract_json(text)
    if obj is not None:
        return obj, False
    t = strip_reasoning(text)
    start = t.find("{")
    if start < 0:
        return None, False
    frag = t[start:].rstrip()
    depth_curly = frag.count("{") - frag.count("}")
    depth_square = frag.count("[") - frag.count("]")
    if frag.count('"') % 2:
        frag += '"'
    for cand in (frag + "]" * max(0, depth_square) + "}" * max(0, depth_curly),):
        try:
            o = json.loads(cand)
            return (o, True) if isinstance(o, dict) else (None, False)
        except json.JSONDecodeError:
            pass
    return None, False


def _norm(v):
    if isinstance(v, str):
        s = v.strip().lower()
        return int(s) if s.isdigit() else s
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() else v
    if isinstance(v, list):
        return sorted((_norm(x) for x in v), key=lambda x: str(x))
    return v


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [x for x in re.split(r"[\s,;]+", v) if x]
    return list(v) if isinstance(v, (list, tuple)) else [v]


def check(ans: dict, c: dict) -> bool:
    v = ans.get(c["field"])
    op, want = c["op"], c.get("value")
    if isinstance(v, list) and len(v) == 1 and not isinstance(want, list):
        v = v[0]  # ["no"] for "no": small models wrap scalars; the meaning is unambiguous
    if op == "equals":
        return _norm(v) == _norm(want)
    if op == "in":
        return _norm(v) in [_norm(x) for x in want]
    if op == "is_null":
        return v is None or v == [] or (isinstance(v, str) and v.strip().lower() in ("", "null", "none", "unknown"))
    got = {str(_norm(x)) for x in _as_list(v)}
    if op == "contains_all":
        return all(str(_norm(x)) in got for x in want)
    if op == "contains_any":
        return any(str(_norm(x)) in got for x in want)
    if op == "contains_none":
        return not any(str(_norm(x)) in got for x in want)
    raise ValueError(f"unknown op {op}")


def grade(answer_text: str, truth: dict) -> dict:
    ans = extract_json(answer_text)
    if ans is None:
        return {"parsed": False, "pass": False, "checks_passed": 0, "checks": len(truth["checks"]), "false_positive": False}
    results = [check(ans, c) for c in truth["checks"]]
    fp = bool(truth.get("false_positive_if")) and check(ans, truth["false_positive_if"])
    return {"parsed": True, "pass": all(results), "checks_passed": sum(results), "checks": len(results), "false_positive": fp,
            "answer": ans}
