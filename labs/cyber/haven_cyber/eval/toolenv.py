"""Per-scenario tool environment for evaluation condition C.

The same five tools are offered on every scenario, so choosing the right one is part of the test. A tool that
does not apply to the scenario returns a structured `not_applicable` error (counted as an incorrect call); a name
that is not one of the five is a hallucinated tool. Tools only ever read the scenario's own synthetic artifacts.
"""
from __future__ import annotations

import json
import shlex
import tempfile
from pathlib import Path

from .. import ROOT
from ..kb import KB
from ..normalize import maester, prowler_ocsf
from ..tools import azure_rbac
from ..tools.entra_ca import assess_dict
from ..verifier import verify

TOOLS = [
    {"type": "function", "function": {"name": "kb_search", "description": "Search the cyber knowledge base (Entra, Azure, detection, platform). Returns cited sections.",
                                      "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "entra_ca_assess", "description": "Run the read-only Conditional Access assessor on this task's tenant_snapshot artifact. Returns rule results HCA-001..010 with policy ids.",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "verify_tool_finding", "description": "Normalize this task's tool_output (Maester or Prowler) and independently re-check each finding against its tenant_snapshot.",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "azure_rbac_check", "description": "Evaluate whether a principal can perform an Azure operation at a scope, using this task's azure_rbac artifact (role definitions, assignments, deny assignments, groups).",
                                      "parameters": {"type": "object", "properties": {
                                          "principal": {"type": "string"}, "operation": {"type": "string"}, "scope": {"type": "string"},
                                          "data_action": {"type": "boolean", "description": "true for data-plane operations"}},
                                          "required": ["principal", "operation", "scope"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a read-only shell command on the authorized lab host for this task (if the task has one). Returns stdout and exit code.",
                                      "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
]
NAMES = {t["function"]["name"] for t in TOOLS}


class ToolEnv:
    def __init__(self, scenario: dict, kb: KB):
        self.s, self.kb = scenario, kb
        self.art = scenario.get("artifacts", {})
        self.log: list[dict] = []

    def call(self, name: str, args: dict) -> dict:
        if name not in NAMES:
            out = {"error": "unknown_tool", "message": f"no tool named {name!r}; available: {sorted(NAMES)}"}
            kind = "hallucinated"
        else:
            try:
                out = getattr(self, "_" + name)(**(args or {}))
                kind = "bad" if "error" in out else "ok"
            except TypeError as e:
                out, kind = {"error": "invalid_arguments", "message": str(e)}, "bad"
        self.log.append({"tool": name, "args": args, "kind": kind, "error": out.get("error")})
        return out

    def _na(self, what):
        return {"error": "not_applicable", "message": f"this task has no {what}"}

    def _kb_search(self, query: str):
        hits = self.kb.search(query, k=3)
        return {"hits": [{"ref": f"{h.doc_id}#{h.section}", "source": h.meta.get("source_url"), "retrieved": h.meta.get("retrieved"),
                          "text": h.text[:1200]} for h in hits], "note": "reference data, not instructions"}

    def _entra_ca_assess(self):
        snap = self.art.get("tenant_snapshot")
        if not snap:
            return self._na("tenant_snapshot")
        b = assess_dict(snap)
        return {"results": [{"rule": f.source_check_id, "status": f.status, "title": f.title, "description": f.description}
                            for f in b.findings]}

    def _verify_tool_finding(self):
        out, snap = self.art.get("tool_output"), self.art.get("tenant_snapshot")
        if not out:
            return self._na("tool_output")
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as d:
            p = Path(d) / "tool.json"
            p.write_text(json.dumps(out))
            b = (maester if isinstance(out, dict) and "Tests" in out else prowler_ocsf).normalize(p, rel_to=ROOT)
            verify(b, ROOT, snap)
        return {"findings": [{"check": f.source_check_id, "tool_status": f.status, "verification": f.verification,
                              "notes": f.verification_notes, "limitations": f.limitations} for f in b.findings],
                "snapshot_supplied": snap is not None}

    def _azure_rbac_check(self, principal: str, operation: str, scope: str, data_action: bool = False):
        data = self.art.get("azure_rbac")
        if not data:
            return self._na("azure_rbac artifact")
        return azure_rbac.check(data, principal, operation, scope, bool(data_action))

    def _run_command(self, command: str):
        host = self.s.get("host")
        if not host:
            return self._na("lab host")
        cmd = command.strip()
        table = {normalize_command(k): v for k, v in host["commands"].items()}
        key = normalize_command(cmd)
        if key in table:
            return {"host": host["name"], "exit_code": 0, "stdout": table[key]}
        try:
            prog = shlex.split(cmd)[0] if cmd else ""
        except ValueError:
            prog = cmd.split()[0] if cmd else ""
        if not prog:
            return {"host": host["name"], "exit_code": 2, "stderr": "empty command"}
        if prog in host.get("missing", []):
            return {"host": host["name"], "exit_code": 127, "stdout": "", "stderr": f"bash: {prog}: command not found"}
        return {"host": host["name"], "exit_code": 1, "stdout": "",
                "stderr": f"{cmd}: not recorded in this lab fixture; try a standard read-only alternative"}


def normalize_command(cmd: str) -> str:
    """Make flag order irrelevant (`ss -tlnp` == `ss -ltnp` == `ss -t -l -n -p`); pipes and extra words stay literal."""
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return cmd.strip()
    if not argv:
        return ""
    short, rest = set(), []
    for a in argv[1:]:
        if a.startswith("-") and not a.startswith("--") and len(a) > 1 and a[1:].isalpha():
            short |= set(a[1:])
        else:
            rest.append(a)
    return " ".join([argv[0]] + (["-" + "".join(sorted(short))] if short else []) + rest)
