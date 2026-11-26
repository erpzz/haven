"""Trusted routing metadata adapter for the Haven Hermes operator catalog.

The model-visible definition is exactly the MCP tools/list object emitted by
mcp_stdio.Server. Routing metadata is separate, host-owned code. Free-form tool
descriptions never decide relevance.
"""
from __future__ import annotations

from typing import Mapping

from .registry import Registry, ToolSpec

BUILTIN_ROUTE_TERMS = {
    "haven_status": ["status", "haven", "health", "overview"],
    "haven_gpu": ["gpu", "vram", "compute", "graphics"],
    "haven_models": ["model", "models", "loaded", "downloaded", "admission"],
    "haven_sentinel": ["sentinel", "security", "audit", "finding", "findings"],
    "haven_brief": ["brief", "summary", "controller", "records"],
    "haven_fleet": ["fleet", "node", "nodes", "memory", "gpu"],
    "haven_jobs": ["job", "jobs", "scheduler", "progress"],
    "haven_lab_job": ["job", "progress", "model", "load", "strata"],
    "haven_tasks": ["task", "tasks", "agent", "engineer"],
    "haven_approvals": ["approval", "approvals", "pending", "owner"],
    "haven_receipts": ["receipt", "receipts", "ledger", "verify"],
    "haven_check_answer": ["answer", "claim", "claims", "receipt", "verify"],
    "haven_model_use": ["model", "load", "switch", "context"],
    "haven_model_unload": ["model", "unload", "disconnect", "gpu"],
    "haven_strata_connect": ["strata", "connect", "backend", "gpu"],
    "haven_job_submit": ["job", "submit", "command", "scheduler", "workspace"],
    "haven_job_cancel": ["job", "cancel", "scheduler", "stop"],
    "haven_task_start": ["task", "start", "agent", "workspace", "engineer", "observe"],
    "haven_task_cancel": ["task", "cancel", "stop", "agent"],
    "haven_tools": ["tool", "tools", "skill", "skills", "candidate", "admitted"],
    "haven_tool_propose": ["tool", "propose", "create", "skill", "code"],
    "haven_tool_request_admission": ["tool", "skill", "admission", "request", "owner"],
}


class RoutingMetadataError(ValueError):
    pass


def mcp_definition(spec: ToolSpec) -> dict:
    """Exact object shape emitted by mcp_stdio.Server for one visible tool."""
    return {
        "name": spec.name,
        "description": spec.description,
        "inputSchema": spec.schema(),
        "annotations": spec.annotations(),
    }


def route_cards(registry: Registry, *, dynamic_route_terms: Mapping[str, list[str]] | None = None) -> list[dict]:
    """Build cards for the *entire* current visible catalog or fail closed.

    Dynamic skill descriptions are user/model-authored content and never become
    routing authority. A visible dynamic tool requires explicit host metadata.
    """
    registry.refresh()
    dynamic_route_terms = dict(dynamic_route_terms or {})
    cards = []
    missing = []
    for spec in registry.visible():
        terms = BUILTIN_ROUTE_TERMS.get(spec.name)
        if terms is None:
            terms = dynamic_route_terms.get(spec.name)
        if terms is None:
            missing.append(spec.name)
            continue
        cards.append({
            "name": spec.name,
            "effect": spec.effect,
            "route_terms": list(terms),
            "definition": mcp_definition(spec),
        })
    if missing:
        raise RoutingMetadataError(
            "visible tools lack host-owned routing metadata: " + ", ".join(sorted(missing))
        )
    return sorted(cards, key=lambda card: card["name"])
