"""Tokenize only training rows whose exact model-visible tool surface is bound.

The rendering logic intentionally mirrors the Qwen/Haven SFT path used by the
referenced trainers, but it never permits tools=None as an accidental fallback.
"""
from __future__ import annotations

import os
from typing import Sequence

import tool_surface


class EncodingError(ValueError):
    pass


def _render(tokenizer, messages: list[dict], tools: list[dict]) -> tuple[str, str]:
    if not isinstance(messages, list) or len(messages) < 2:
        raise EncodingError("row needs at least a prefix and assistant target")
    last = messages[-1]
    if not isinstance(last, dict) or last.get("role") != "assistant":
        raise EncodingError("last message must be the assistant training target")

    kwargs = {
        "tools": tools,
        "tokenize": False,
        "enable_thinking": False,
    }
    try:
        prefix = tokenizer.apply_chat_template(
            messages[:-1], add_generation_prompt=True, **kwargs
        )
        full = tokenizer.apply_chat_template(messages, **kwargs)
    except Exception as exc:
        raise EncodingError("chat template rendering failed") from exc

    if not isinstance(prefix, str) or not isinstance(full, str):
        raise EncodingError("chat template must return text")

    if full.startswith(prefix):
        target = full[len(prefix):]
    else:
        # Qwythos templates can omit the generation prompt's empty think block in
        # the completed assistant turn. Preserve the same compatibility rule as
        # the reviewed #95 trainer while keeping the exact bound tool array.
        try:
            base = tokenizer.apply_chat_template(messages[:-1], **kwargs)
        except Exception as exc:
            raise EncodingError("chat template base rendering failed") from exc
        if not isinstance(base, str) or not full.startswith(base) or not prefix.startswith(base):
            raise EncodingError("chat template prefix mismatch")
        turn = full[len(base):]
        generated = prefix[len(base):]
        head = os.path.commonprefix([turn, generated])
        head = head[:head.rfind("\n") + 1]
        if not head:
            raise EncodingError("chat template prefix mismatch")
        target = turn[len(head):]

    target = target.rstrip("\n")
    if not target:
        raise EncodingError("assistant target rendered empty")
    return prefix, target


def _token_ids(tokenizer, text: str) -> list[int]:
    try:
        encoded = tokenizer(text, add_special_tokens=False)
    except Exception as exc:
        raise EncodingError("tokenization failed") from exc
    if not isinstance(encoded, dict) or not isinstance(encoded.get("input_ids"), list):
        raise EncodingError("tokenizer did not return input_ids")
    ids = encoded["input_ids"]
    if not ids or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in ids):
        raise EncodingError("invalid token ids")
    return ids


def encode_bound_row(tokenizer, row: dict, *, max_length: int) -> dict:
    """Encode one row using the exact tool array committed into that row."""
    problems = tool_surface.validate_bound_rows([row])
    if problems:
        raise EncodingError("invalid tool-surface binding: " + ",".join(problems))
    if isinstance(max_length, bool) or not isinstance(max_length, int) or max_length < 2:
        raise EncodingError("invalid max_length")

    messages = row.get("messages")
    tools = row["tools"]
    prefix, target = _render(tokenizer, messages, tools)
    prefix_ids = _token_ids(tokenizer, prefix)
    target_ids = _token_ids(tokenizer, target)
    if len(prefix_ids) + len(target_ids) > max_length:
        # Do not silently skip one row from a multi-row trace: that would alter the
        # trace objective and could invalidate the episode weighting contract.
        raise EncodingError("bound row exceeds max_length")

    return {
        "input_ids": prefix_ids + target_ids,
        "attention_mask": [1] * (len(prefix_ids) + len(target_ids)),
        "labels": [-100] * len(prefix_ids) + target_ids,
        "target_tokens": len(target_ids),
        "tool_surface_sha256": row["tool_surface_sha256"],
        "tool_surface_receipt_sha256": row["tool_surface"]["receipt_sha256"],
    }


def encode_bound_rows(tokenizer, rows: Sequence[dict], *, max_length: int) -> list[dict]:
    """Validate the whole arm before encoding any row."""
    problems = tool_surface.validate_bound_rows(rows)
    if problems:
        raise EncodingError("invalid bound training rows: " + ",".join(problems))
    return [encode_bound_row(tokenizer, row, max_length=max_length) for row in rows]
