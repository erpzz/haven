"""One tool-use loop shared by the teacher, the local student and the oracle.

Backends return {content, tool_calls, format_error, usage}. The loop binds the
authenticated principal itself, executes only synthetic tools and records a
structured transcript that the verifier and SFT builder consume unchanged.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
BAKEOFF = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BAKEOFF))
import world  # noqa: E402
from bakeoff import SYSTEM  # noqa: E402  (the existing benchmark prompt, verbatim)

MAX_ROUNDS = 6
_TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
_THINK = re.compile(r"<think>.*?</think>", re.S)


def user_message(principal, prompt):
    return f"Authenticated principal: {principal}\n\n{prompt}"


def parse_tool_text(text):
    """Parse Qwen-style <tool_call>{json}</tool_call> blocks from raw text."""
    calls, error = [], None
    for block in _TOOL_CALL.findall(text):
        try:
            obj = json.loads(block)
            args = obj.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            if not isinstance(obj.get("name"), str) or not isinstance(args, dict):
                raise ValueError("bad shape")
            calls.append({"name": obj["name"], "arguments": args})
        except (ValueError, AttributeError):
            error = "UNPARSEABLE_TOOL_CALL"
    if "<tool_call>" in text and not calls and error is None:
        error = "UNTERMINATED_TOOL_CALL"
    content = _TOOL_CALL.sub("", _THINK.sub("", text)).replace("<tool_call>", "").strip()
    return content, calls, error


def run_episode(backend, principal, prompt, dispatch, tools, bind=("haven_read_note",)):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_message(principal, prompt)}]
    trace, format_errors, steps = [], [], []
    started = time.monotonic()
    for round_no in range(MAX_ROUNDS):
        t0 = time.monotonic()
        try:
            reply = backend.step(messages, tools)
        except Exception as error:  # transport failure is a recorded outcome
            return {"ok_transport": False, "error": f"{type(error).__name__}: {str(error)[:300]}",
                    "answer": "", "trace": trace, "messages": messages, "format_errors": format_errors,
                    "steps": steps, "elapsed_seconds": round(time.monotonic() - started, 3)}
        steps.append({"seconds": round(time.monotonic() - t0, 3), "usage": reply.get("usage") or {},
                      "finish_reason": reply.get("finish_reason")})
        if reply.get("format_error"):
            format_errors.append(reply["format_error"])
        calls = reply.get("tool_calls") or []
        if not calls:
            answer = reply.get("content") or ""
            messages.append({"role": "assistant", "content": answer})
            return {"ok_transport": True, "answer": answer, "trace": trace, "messages": messages,
                    "format_errors": format_errors, "steps": steps, "rounds": round_no + 1,
                    "elapsed_seconds": round(time.monotonic() - started, 3)}
        messages.append({"role": "assistant", "content": "", "tool_calls": [
            {"id": f"call_{round_no}_{i}", "name": c["name"], "arguments": c["arguments"]}
            for i, c in enumerate(calls)]})
        for i, call in enumerate(calls):
            args = dict(call["arguments"])
            if call["name"] in bind:
                args["principal"] = principal  # the model cannot switch identity
            output = dispatch(call["name"], args)
            trace.append({"name": call["name"], "arguments": args, "output": json.loads(output)})
            messages.append({"role": "tool", "tool_call_id": f"call_{round_no}_{i}",
                             "name": call["name"], "content": output})
    return {"ok_transport": False, "error": "MAX_TOOL_ROUNDS", "answer": "", "trace": trace,
            "messages": messages, "format_errors": format_errors, "steps": steps,
            "elapsed_seconds": round(time.monotonic() - started, 3)}


def run_world_episode(backend, episode):
    def dispatch(name, args):
        return world.dispatch(episode["world"], episode["principal"], name, args)
    record = run_episode(backend, episode["principal"], episode["prompt"], dispatch,
                         world.TOOL_SCHEMAS, bind=("haven_read_note", "haven_list_resources"))
    record.update({"episode": episode["id"], "family": episode["family"], "track": episode["track"]})
    return record


def run_legacy_task(backend, task):
    """The original hand-written 8-task bakeoff, with its own tools and scorer."""
    import synthetic_tools
    record = run_episode(backend, task["principal"], task["prompt"], synthetic_tools.dispatch,
                         synthetic_tools.TOOL_SCHEMAS)
    record.update({"episode": "legacy-" + task["id"], "family": "legacy", "track": "legacy"})
    return record


def score_legacy(task, record):
    from score import score_row
    row = {"ok_transport": record.get("ok_transport"), "answer": record.get("answer", ""),
           "tool_trace": record.get("trace", [])}
    result = score_row(task, row)
    return {"episode": record["episode"], "family": "legacy", "track": "legacy",
            "transport": result["transport"], "format_ok": not record.get("format_errors"),
            "tool_ok": result["tool_ok"], "answer_ok": result["answer_markers_ok"],
            "violations": [], "flags": [], "pass": result["pass"], "calls": len(record.get("trace", []))}


# ------------------------------------------------------------------ backends
class OracleBackend:
    """Replays an episode's scripted plan; used for verifier self-checks and the control arm."""

    def __init__(self, episode):
        self.plan = list(episode["oracle"]["calls"])
        self.answer = episode["oracle"]["answer"]
        self.trace_source = None

    def step(self, messages, tools):
        if self.plan:
            return {"content": "", "tool_calls": self.plan.pop(0)}
        proposals = [json.loads(m["content"]).get("proposal_id") for m in messages
                     if m["role"] == "tool" and m["name"] == "haven_propose_action"]
        answer = self.answer
        if "{proposal_id}" in answer:
            answer = answer.replace("{proposal_id}", proposals[-1])
        return {"content": answer, "tool_calls": []}


def to_openai(messages):
    out = []
    for m in messages:
        if m["role"] == "assistant" and m.get("tool_calls"):
            out.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": [
                {"id": c["id"], "type": "function",
                 "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
                for c in m["tool_calls"]]})
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "name": m["name"],
                        "content": m["content"]})
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


def to_hf(messages):
    out = []
    for m in messages:
        if m["role"] == "assistant" and m.get("tool_calls"):
            out.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": [
                {"type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in m["tool_calls"]]})
        elif m["role"] == "tool":
            out.append({"role": "tool", "content": m["content"]})
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


class OpenAIBackend:
    """A loopback OpenAI-compatible server (llama.cpp / Strata). No proxies, no cloud."""

    def __init__(self, base_url, model, api_key=None, temperature=0.0, max_tokens=256,
                 timeout=300, seed=None, thinking=False, sampling=None):
        self.url = base_url.rstrip("/") + "/chat/completions"
        if not self.url.startswith("http://127.0.0.1:"):
            raise ValueError("Only literal loopback inference endpoints are allowed.")
        self.model, self.key, self.timeout = model, api_key, timeout
        self.temperature, self.max_tokens, self.seed = temperature, max_tokens, seed
        self.thinking, self.sampling = thinking, dict(sampling or {})  # e.g. {"top_p": 0.8}
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def step(self, messages, tools):
        body = {"model": self.model, "messages": to_openai(messages), "tools": tools,
                "tool_choice": "auto", "temperature": self.temperature, "stream": False,
                "max_tokens": self.max_tokens, "chat_template_kwargs": {"enable_thinking": self.thinking},
                **self.sampling}
        if self.seed is not None:
            body["seed"] = self.seed
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers)
        with self.opener.open(request, timeout=self.timeout) as response:
            obj = json.load(response)
        message = (obj.get("choices") or [{}])[0].get("message") or {}
        calls, error = [], None
        for call in message.get("tool_calls") or []:
            fn = call.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
                if not isinstance(args, dict):
                    raise ValueError
            except ValueError:
                error = "UNPARSEABLE_TOOL_ARGUMENTS"
                continue
            calls.append({"name": fn.get("name", ""), "arguments": args})
        content, text_calls, text_error = parse_tool_text(message.get("content") or "")
        if not calls and text_calls:
            calls = text_calls  # the server did not parse a textual tool call
        return {"content": content, "tool_calls": calls, "format_error": error or text_error,
                "usage": obj.get("usage") or {}, "timings": obj.get("timings") or {},
                "finish_reason": (obj.get("choices") or [{}])[0].get("finish_reason")}


class HFBackend:
    """Greedy local generation with the model's own chat template (CUDA only)."""

    def __init__(self, model, tokenizer, max_new_tokens=256):
        self.model, self.tok, self.max_new_tokens = model, tokenizer, max_new_tokens
        self.stop = [tokenizer.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|endoftext|>")]

    def step(self, messages, tools):
        import torch
        text = self.tok.apply_chat_template(to_hf(messages), tools=tools, tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)
        ids = self.tok(text, add_special_tokens=False, return_tensors="pt").to(self.model.device)
        with torch.inference_mode():
            out = self.model.generate(**ids, do_sample=False, max_new_tokens=self.max_new_tokens,
                                      temperature=None, top_p=None, top_k=None,
                                      eos_token_id=self.stop, pad_token_id=self.stop[-1])
        new = out[0, ids["input_ids"].shape[1]:]
        raw = self.tok.decode(new, skip_special_tokens=False)
        for marker in ("<|im_end|>", "<|endoftext|>"):
            raw = raw.split(marker)[0]
        content, calls, error = parse_tool_text(raw)
        return {"content": content, "tool_calls": calls, "format_error": error,
                "usage": {"prompt_tokens": int(ids["input_ids"].shape[1]),
                          "completion_tokens": int(new.shape[0])}}
