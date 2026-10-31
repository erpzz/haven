"""Deterministic decoder-only transformer for HIVE's *correctness* pilot.

Random initialized weights: this is REAL neural computation, NOT a language-capable
checkpoint. No pretrained model, inference quality or GPU speed is implied.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import torch
from torch import nn


@dataclass(frozen=True)
class Spec:
    layers: int = 4
    dim: int = 64
    heads: int = 4
    context: int = 64
    seed: int = 20261031

    def validate(self) -> None:
        if not (1 <= self.layers <= 24 and 8 <= self.dim <= 512 and
                1 <= self.heads <= 32 and self.dim % self.heads == 0 and
                2 <= self.context <= 512 and 0 <= self.seed <= 2**31 - 1):
            raise ValueError('Invalid bounded HIVE model specification.')

    @property
    def identity(self) -> str:
        return hashlib.sha256(('hive-random-transformer-v1:' + json.dumps(
            asdict(self), sort_keys=True, separators=(',', ':'))).encode()).hexdigest()


class Block(nn.Module):
    def __init__(self, dim: int, heads: int):
        super().__init__()
        self.dim, self.heads = dim, heads
        self.norm1 = nn.LayerNorm(dim)
        self.attn = nn.Linear(dim, 3 * dim, bias=False)
        self.proj = nn.Linear(dim, dim, bias=False)
        self.norm2 = nn.LayerNorm(dim)
        self.ff1 = nn.Linear(dim, 4 * dim)
        self.ff2 = nn.Linear(4 * dim, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        t, d = x.shape
        h = self.norm1(x)
        q, k, v = self.attn(h).chunk(3, dim=-1)
        q = q.reshape(t, self.heads, d // self.heads).transpose(0, 1)
        k = k.reshape(t, self.heads, d // self.heads).transpose(0, 1)
        v = v.reshape(t, self.heads, d // self.heads).transpose(0, 1)
        scores = (q @ k.transpose(-1, -2)) / math.sqrt(d // self.heads)
        mask = torch.ones((t, t), device=x.device, dtype=torch.bool).triu(1)
        scores = scores.masked_fill(mask, torch.finfo(scores.dtype).min)
        att = torch.softmax(scores, dim=-1)
        x = x + self.proj((att @ v).transpose(0, 1).contiguous().reshape(t, d))
        x = x + self.ff2(torch.nn.functional.gelu(self.ff1(self.norm2(x))))
        return x


def _seeded(seed: int, constructor):
    # CPU-only initialization makes parameters reproducible on heterogeneous hosts.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return constructor()


class Segment(nn.Module):
    """Owns ONLY the requested layer range, never the full-model weights."""
    def __init__(self, spec: Spec, start: int, stop: int, device: str = 'cpu'):
        super().__init__()
        spec.validate()
        if not (0 <= start < stop <= spec.layers):
            raise ValueError('Invalid layer range.')
        self.start, self.stop = start, stop
        self.layers = nn.ModuleList([
            _seeded(spec.seed + 1000 + i, lambda: Block(spec.dim, spec.heads))
            for i in range(start, stop)
        ])
        self.to(device).eval()

    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x


class Endpoints(nn.Module):
    """Coordinator-only embeddings and output head, with no transformer layers."""
    def __init__(self, spec: Spec, device: str = 'cpu'):
        super().__init__()
        spec.validate()
        self.token = _seeded(spec.seed + 11, lambda: nn.Embedding(256, spec.dim))
        self.position = _seeded(spec.seed + 12, lambda: nn.Embedding(spec.context, spec.dim))
        self.norm = _seeded(spec.seed + 13, lambda: nn.LayerNorm(spec.dim))
        self.head = _seeded(spec.seed + 14, lambda: nn.Linear(spec.dim, 256, bias=False))
        self.to(device).eval()

    def embed(self, ids: list[int]):
        dev = self.token.weight.device
        positions = torch.arange(len(ids), device=dev)
        return self.token(torch.tensor(ids, dtype=torch.long, device=dev)) + self.position(positions)

    def predict(self, x):
        return int(torch.argmax(self.head(self.norm(x[-1])), dim=-1).item())


@torch.inference_mode()
def baseline(spec: Spec, prompt: bytes, count: int) -> list[int]:
    spec.validate()
    validate_prompt(spec, prompt, count)
    ends = Endpoints(spec)
    all_layers = Segment(spec, 0, spec.layers)
    ids = list(prompt)
    new = []
    for _ in range(count):
        value = ends.predict(all_layers(ends.embed(ids)))
        ids.append(value)
        new.append(value)
    return new


def validate_prompt(spec: Spec, prompt: bytes, count: int) -> None:
    if not prompt or not (1 <= count <= 128) or len(prompt) + count > spec.context:
        raise ValueError('Prompt must be nonempty and prompt + output must fit context.')
