"""Tool creation through the engineer's skill admission (labs/engineer/skills.py), not a second registry.

Hermes may write a candidate tool and run it against its own dev cases in the OS sandbox. This server cannot
admit it: admission is the owner's `skills.py admit` command, run against held-out cases the owner writes,
and the admitted record is HMAC-signed and content-addressed. (Hermes's own file and terminal tools could
reach that directory too; they are gated by Hermes's approvals, and admission means something only when the
owner, or an independent session, writes the cases.) Once admitted, the skill appears here as `skill_<name>` (a change tool: it runs code),
is re-verified before every call, and disappears if its files change.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path

from ..registry import ToolError, ToolSpec
from . import engineer_state, obj
from .operate import _workspace

NAME = {"type": "string", "pattern": r"[a-z][a-z0-9_]{2,40}"}
RESERVED_ARG = "haven_workspace"


def candidates_dir() -> Path:
    return engineer_state() / "skill-candidates"


def heldout_dir(name) -> Path:
    return engineer_state() / "skill-heldout" / name


def _require_sandbox():
    import sandbox
    d = sandbox.describe()
    if not d.get("available"):
        raise ToolError("no_sandbox", "this host has no OS sandbox, so candidate code is not run", refused=True)
    return d


def _display(p: Path) -> str:
    return str(p).replace(str(Path.home()), "~")


def propose(ctx, name, description, parameters, code, dev_cases, recipe=""):
    import skills
    d = candidates_dir() / name
    if d.exists():
        shutil.rmtree(d)
    (d / "dev").mkdir(parents=True, mode=0o700)
    params = {"type": "object", "properties": parameters.get("properties", {}),
              "required": parameters.get("required", []), "additionalProperties": False}
    (d / "skill.json").write_text(json.dumps({"name": name, "description": description, "parameters": params}, indent=2))
    (d / "skill.py").write_text(code)
    (d / "recipe.md").write_text(recipe or f"# {name}\n\n{description}\n")
    for i, case in enumerate(dev_cases):
        c = d / "dev" / f"case{i:02d}"
        (c / "repo").mkdir(parents=True)
        (c / "expect.json").write_text(json.dumps({"args": case["args"], "result": case["result"]}))
    _require_sandbox()
    report = skills.validate(d, d / "dev")
    digest = skills.content_hash(d)
    summary = {"dev_pass": sum(c["ok"] for c in report), "dev_total": len(report)}
    (d / "dev-report.json").write_text(json.dumps({"sha256": digest, "report": report, **summary}, indent=2))
    return {"candidate": name, "sha256": digest, **summary, "dev_report": report,
            "next": "fix and propose again until every dev case passes, then haven_tool_request_admission"
                    if summary["dev_pass"] != summary["dev_total"] or not report else "haven_tool_request_admission"}


def request_admission(ctx, name):
    import skills
    d = candidates_dir() / name
    if not (d / "skill.json").exists():
        raise ToolError("not_found", f"no candidate tool {name}; propose it first", refused=True)
    rep = json.loads((d / "dev-report.json").read_text()) if (d / "dev-report.json").exists() else {}
    digest = skills.content_hash(d)
    if rep.get("sha256") != digest or not rep.get("dev_total") or rep["dev_pass"] != rep["dev_total"]:
        raise ToolError("dev_cases_failing", "every dev case must pass on the current files first", refused=True)
    held = heldout_dir(name)
    req = {"name": name, "sha256": digest, "requested_at": time.time(), "requested_by": "hermes",
           "dev": {k: rep[k] for k in ("dev_pass", "dev_total")}}
    (d / "ADMISSION_REQUEST.json").write_text(json.dumps(req, indent=2))
    engineer = Path(skills.__file__).resolve()
    return {"requested": True, "sha256": digest,
            "owner_steps": [f"write held-out cases (<case>/repo/ and <case>/expect.json with args and result) to "
                            f"{_display(held)} (write them yourself or have an independent session do it, never the tool's author)",
                            f"python3 {_display(engineer)} admit {_display(d)} --heldout {_display(held)} "
                            f"--dev {_display(d / 'dev')} --author hermes"],
            "note": "the tool appears as skill_" + name + " once admitted; until then it cannot be called"}


def tools_list(ctx):
    import skills
    changed = ctx.registry.refresh() if ctx.registry else False
    if changed:
        ctx.registry.changed()
    cands = []
    root = candidates_dir()
    for d in sorted(root.iterdir()) if root.exists() else []:
        if not (d / "skill.json").exists():
            continue
        rep = json.loads((d / "dev-report.json").read_text()) if (d / "dev-report.json").exists() else {}
        cands.append({"name": d.name, "sha256": rep.get("sha256", "")[:12],
                      "dev": f"{rep.get('dev_pass', 0)}/{rep.get('dev_total', 0)}",
                      "admission_requested": (d / "ADMISSION_REQUEST.json").exists()})
    return {"admitted": skills.list_skills()["skills"], "candidates": cands,
            "callable_now": sorted(t.name for t in ctx.registry.tools.values() if t.name.startswith("skill_"))
            if ctx.registry else []}


def _skill_fn(name):
    def run(ctx, **args):
        import skills
        v = skills.verified(name)
        if not v:
            raise ToolError("skill_invalid", f"skill {name} is no longer admitted or its files changed", refused=True)
        _require_sandbox()
        ws = args.pop(RESERVED_ARG, None)
        with tempfile.TemporaryDirectory(prefix="haven-skill-ws-") as t:
            cwd = _workspace(ws) if ws else t
            result, raw = skills.run_skill(v[0], cwd, args)
        if result is None:
            raise ToolError("skill_failed", f"skill {name} returned no JSON: {raw[-300:]}")
        return {"skill": name, "sha256": v[1]["sha256"][:12], "result": result}
    return run


def sync_skill_tools(registry) -> bool:
    """Register every admitted, intact skill as skill_<name>; drop the rest. True if the set changed."""
    import skills
    want = {}
    for tool, schema in skills.tool_schemas().items():
        params = json.loads(json.dumps(schema["parameters"]))
        params["properties"][RESERVED_ARG] = {"type": "string", "pattern": r"[A-Za-z0-9._-]{1,80}",
                                              "description": "Optional registered workspace to run in (default: "
                                                             "an empty scratch directory)."}
        want[tool] = ToolSpec(tool, schema["description"], params, _skill_fn(tool[len("skill_"):]), effect="change",
                              rate_per_min=10, summary=lambda a, t=tool: f"{t} {json.dumps(a, sort_keys=True)[:160]}")
    have = {n for n in registry.tools if n.startswith("skill_")}
    for n in have - set(want):
        registry.unregister(n)
    for n, spec in want.items():
        registry.register(spec, replace=True)
    return have != set(want)


def specs():
    case = obj({"args": {"type": "object"}, "result": {"type": "object"}}, ["args", "result"])
    return [
        ToolSpec("haven_tools", "Tools Hermes has created: admitted skills (callable as skill_<name>), candidates "
                 "with their dev-case results, and pending admission requests.", obj({}), tools_list),
        ToolSpec("haven_tool_propose", "Create or replace a candidate tool: a stdlib Python script that reads its "
                 "JSON arguments from argv[1] and prints one JSON object on its last stdout line. It runs in the OS "
                 "sandbox against your dev cases (each: args and the object the result must contain). It cannot "
                 "be called until the owner admits it on held-out cases.",
                 obj({"name": NAME, "description": {"type": "string", "minLength": 10, "maxLength": 1000},
                      "parameters": {"type": "object", "maxBytes": 8000},
                      "code": {"type": "string", "minLength": 20, "maxLength": 20000},
                      "recipe": {"type": "string", "maxLength": 4000},
                      "dev_cases": {"type": "array", "items": case, "maxItems": 12}},
                     ["name", "description", "parameters", "code", "dev_cases"]),
                 propose, effect="create", rate_per_min=6,
                 summary=lambda a: f"propose tool {a['name']} ({len(a['code'])} chars, {len(a['dev_cases'])} dev cases)"),
        ToolSpec("haven_tool_request_admission", "Ask the owner to admit a candidate tool whose dev cases all pass. "
                 "Returns the owner's steps; Hermes cannot admit its own tool.", obj({"name": NAME}, ["name"]),
                 request_admission, effect="create", idempotent=True, rate_per_min=6,
                 summary=lambda a: f"request admission of {a['name']}"),
    ]
