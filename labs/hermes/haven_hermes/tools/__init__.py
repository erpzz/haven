"""Tool sets: observe (read), operate (change) and forge (create). All share one Context."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def engineer_state() -> Path:
    return Path(os.environ.get("HAVEN_ENGINEER_STATE", Path.home() / ".local/state/haven-engineer"))


def engineer_config() -> Path:
    return Path(os.environ.get("HAVEN_ENGINEER_CONFIG", Path.home() / ".config/haven-engineer"))


@dataclass
class Context:
    slink: object  # backends.Slink
    allow_strata: bool = False
    receipts: object = None  # receipts.Receipts
    registry: object = None
    settings: dict = field(default_factory=dict)

    @classmethod
    def load_settings(cls) -> dict:
        """Owner settings for this surface (private, never written by a tool): ~/.config/haven-engineer/hermes.json

        {"task_agents": ["agent-id", ...]}   engineer agents haven_task_start may use (default: none)
        """
        p = engineer_config() / "hermes.json"
        try:
            return json.loads(p.read_text()) if p.exists() else {}
        except ValueError:
            return {}


def obj(props: dict, required=(), **extra) -> dict:
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False, **extra}


ID = {"type": "string", "pattern": r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}"}
