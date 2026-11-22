"""Hermes Agent project plugin: Purple Copilot Tier Zero review.

Tools read the local Purple Copilot history only. ``pre_tool_call`` runs the evidence gateway,
``post_tool_call`` records evidence for the turn, and ``transform_llm_output`` replaces any final
answer that cites, counts or names something the turn's evidence does not contain. In strict mode
(the default; ``PURPLE_REVIEW_STRICT=0`` disables it) every non-Purple tool is blocked.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import threading
import time

# In place, the lab is three levels up. A copied install (or `hermes plugins doctor`) sets PURPLE_COPILOT_LAB.
LAB = pathlib.Path(os.environ.get("PURPLE_COPILOT_LAB") or pathlib.Path(__file__).resolve().parents[3])
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from apm import review  # noqa: E402

STRICT = os.environ.get("PURPLE_REVIEW_STRICT", "1") != "0"
INSTRUCTION = ("[Purple Copilot review] Answer only from purple_tier_zero_* tool results retrieved in this turn. "
               "Cite each claim with the [citation] token from the result, for example [T0-6] or [P-6-0123456789ab]. "
               "Use only numbers and principal names that the results contain. Say what the evidence does not show. "
               "Findings are exposure, not proof of compromise; confidence is limited for archived samples.")
GATE, VERIFIER = review.Gate(strict=STRICT), review.Verifier()
_turns: dict[str, review.Turn] = {}
_lock = threading.Lock()


def _turn(session_id):
    with _lock:
        return _turns.setdefault(session_id or "", review.Turn())


def _handler(name):
    def call(params, **kwargs):
        try:
            return review.call(name, dict(params or {}))
        except (KeyError, TypeError, ValueError) as exc:
            return json.dumps({"error": str(exc)})
    return call


def _pre_llm_call(session_id=None, user_message=None, **kwargs):
    with _lock:
        _turns[session_id or ""] = review.Turn(user_message or "")
    return {"context": INSTRUCTION} if STRICT else None


def _pre_tool_call(tool_name=None, args=None, session_id=None, **kwargs):
    turn = _turn(session_id)
    message = GATE.check(turn, tool_name, args)
    if message:
        turn.blocked.append({"tool": tool_name, "args": args, "reason": message})
        return {"action": "block", "message": message}
    return None


def _post_tool_call(tool_name=None, result=None, session_id=None, **kwargs):
    if tool_name not in review.TOOLS or not isinstance(result, str):
        return
    try:
        data = json.loads(result)
    except ValueError:
        return
    if isinstance(data, dict) and "platform" in data and "error" not in data:
        _turn(session_id).results.append((tool_name, result))


def _transform_llm_output(response_text=None, session_id=None, turn_id=None, model=None, **kwargs):
    turn = _turn(session_id)
    problems = VERIFIER.problems(turn, response_text or "")
    if turn.results or turn.blocked:
        review.receipt({"at": time.time(), "session": session_id, "turn": turn_id, "model": model,
                        "question": turn.question, "calls": [c[0] for c in turn.calls],
                        "blocked": turn.blocked, "problems": problems, "replaced": bool(problems),
                        "answer": response_text})
    return review.fallback(turn, problems) if problems else None


def register(ctx):
    for name in review.TOOLS:
        ctx.register_tool(name=name, toolset="purple-copilot", schema=review.schema(name), handler=_handler(name))
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("transform_llm_output", _transform_llm_output)
