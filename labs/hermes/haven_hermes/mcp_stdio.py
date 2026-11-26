"""Minimal MCP stdio server over a Registry (standard library only).

Factored from labs/engineer/mcp_server.py (protocol 2025-06-18, newline-delimited JSON-RPC), with what an
operator surface needs on top: per-tool annotations, so the client can tell reads from changes, and
notifications/tools/list_changed when the tool set changes (a newly admitted skill).
"""
from __future__ import annotations

import json
import sys
import threading

PROTOCOL = "2025-06-18"


class RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Server:
    def __init__(self, registry, *, name: str, version: str, instructions: str, out=sys.stdout, scope_gate=None):
        self.reg, self.name, self.version, self.instructions, self.out = registry, name, version, instructions, out
        self.scope_gate = scope_gate
        self._lock = threading.Lock()
        self.initialized = False
        registry.listeners.append(self.tools_changed)

    def send(self, msg):
        with self._lock:
            self.out.write(json.dumps(msg, default=str) + "\n")
            self.out.flush()

    def tools_changed(self):
        if self.initialized:
            self.send({"jsonrpc": "2.0", "method": "notifications/tools/list_changed"})

    def handle(self, msg):
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:  # notification
            if method == "notifications/initialized":
                self.initialized = True
            return
        try:
            self.send({"jsonrpc": "2.0", "id": mid, "result": self.dispatch(method, msg.get("params") or {})})
        except RpcError as e:
            self.send({"jsonrpc": "2.0", "id": mid, "error": {"code": e.code, "message": str(e)}})

    def dispatch(self, method, params):
        if method == "initialize":
            self.initialized = True
            return {"protocolVersion": params.get("protocolVersion") or PROTOCOL,
                    "capabilities": {"tools": {"listChanged": True}},
                    "serverInfo": {"name": self.name, "version": self.version},
                    "instructions": self.instructions}
        if method == "ping":
            return {}
        if method == "tools/list":
            self.reg.refresh()
            visible = list(self.reg.visible())
            if self.scope_gate is not None:
                try:
                    allowed = set(self.scope_gate.exposed([t.name for t in visible]))
                except Exception:
                    raise RpcError(-32603, "host tool-scope policy unavailable") from None
                visible = [t for t in visible if t.name in allowed]
            return {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.schema(),
                               "annotations": t.annotations()} for t in visible]}
        if method == "tools/call":
            self.reg.refresh()
            name = params.get("name", "")
            arguments = params.get("arguments")
            if arguments is None:
                arguments = {}
            visible = list(self.reg.visible())
            if not any(t.name == name for t in visible):
                raise RpcError(-32602, f"unknown tool: {name}")
            if self.scope_gate is not None:
                try:
                    allowed = set(self.scope_gate.exposed([t.name for t in visible]))
                    if name not in allowed:
                        raise ValueError("not exposed")
                    self.scope_gate.check(name, arguments)
                except Exception:
                    raise RpcError(-32602, "tool denied by host scope") from None
            out = self.reg.invoke(name, arguments)
            # Text only: some clients show structuredContent instead of the text when both are present.
            return {"content": [{"type": "text", "text": json.dumps(out, indent=1, default=str)}],
                    "isError": not out.get("ok")}
        if method in ("resources/list", "prompts/list"):
            return {method.split("/")[0]: []}
        raise RpcError(-32601, f"method not found: {method}")

    def serve(self, stream=sys.stdin):
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                self.send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
                continue
            for m in (msg if isinstance(msg, list) else [msg]):
                self.handle(m)
