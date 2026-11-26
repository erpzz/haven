import _env  # noqa: F401  (must be first)

import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from haven_hermes.backends import Slink
from haven_hermes.mcp_stdio import Server
from haven_hermes.registry import Registry, ToolError, ToolSpec, scrub, validate


class ValidationTests(unittest.TestCase):
    S = {"type": "object", "additionalProperties": False, "required": ["a"],
         "properties": {"a": {"type": "array", "maxItems": 2,
                              "items": {"type": "object", "required": ["x"], "additionalProperties": False,
                                        "properties": {"x": {"type": "integer", "minimum": 0}}}},
                        "s": {"type": ["string", "null"], "maxLength": 3, "pattern": "[a-z]+"},
                        "c": {"const": "YES"}}}

    def bad(self, value):
        with self.assertRaises(ToolError) as e:
            validate(self.S, value)
        self.assertTrue(e.exception.refused)
        return e.exception.message

    def test_nested_and_limits(self):
        validate(self.S, {"a": [{"x": 1}], "s": None, "c": "YES"})
        self.assertIn("a[0].x", self.bad({"a": [{"x": -1}]}))
        self.assertIn("a[0]", self.bad({"a": [{"x": 1, "y": 2}]}))
        self.bad({"a": [{"x": 1}] * 3})
        self.bad({"a": [], "s": "abcd"})
        self.bad({"a": [], "s": "AB"})
        self.bad({"a": [], "c": "NO"})
        self.bad({"a": [{"x": True}]})  # booleans are not integers
        self.bad({})

    def test_unsupported_type_is_a_clean_error(self):
        with self.assertRaises(ToolError) as e:
            validate({"type": "date"}, "x")
        self.assertEqual(e.exception.code, "bad_schema")

    def test_scrub(self):
        out = scrub(f"{Path.home()}/x token=abc123 /home/someone/y " + "A" * 48)
        self.assertNotIn(str(Path.home()), out)
        self.assertNotIn("abc123", out)
        self.assertNotIn("someone", out)
        self.assertNotIn("A" * 48, out)


def _reg(mode="operate", **kw):
    t = Path(tempfile.mkdtemp())
    reg = Registry(object(), mode=mode, state=t, **kw)
    reg.register(ToolSpec("t_read", "r", {"type": "object", "properties": {"p": {"type": "string"}},
                                          "additionalProperties": False}, lambda ctx, p="": {"echo": p},
                          rate_per_min=2))
    reg.register(ToolSpec("t_change", "c", {"type": "object", "properties": {}}, lambda ctx: {}, effect="change"))
    return reg, t


class RegistryTests(unittest.TestCase):
    def test_observe_mode_hides_and_refuses_changes(self):
        reg, _ = _reg("observe")
        self.assertEqual([t.name for t in reg.visible()], ["t_read"])
        self.assertEqual(reg.invoke("t_change")["error"]["code"], "mode_forbids")

    def test_annotations_follow_effect(self):
        reg, _ = _reg()
        self.assertTrue(reg.tools["t_read"].annotations()["readOnlyHint"])
        self.assertFalse(reg.tools["t_change"].annotations()["readOnlyHint"])
        self.assertIn("idempotency_key", reg.tools["t_change"].schema()["properties"])
        self.assertNotIn("idempotency_key", reg.tools["t_read"].schema()["properties"])

    def test_rate_limit_survives_restart_and_audit_has_no_raw_args(self):
        reg, state = _reg()
        self.assertTrue(reg.invoke("t_read", {"p": "secret-path"})["ok"])
        self.assertTrue(reg.invoke("t_read")["ok"])
        again = Registry(object(), mode="operate", state=state)  # a new Hermes session, same state
        again.register(reg.tools["t_read"])
        self.assertEqual(again.invoke("t_read")["error"]["code"], "rate_limited")
        audit = (state / "audit.jsonl").read_text()
        self.assertEqual(len(audit.splitlines()), 3)
        self.assertNotIn("secret-path", audit)

    def test_tool_bug_does_not_crash_or_leak(self):
        reg, _ = _reg()
        reg.register(ToolSpec("t_boom", "b", {"type": "object"}, lambda ctx: 1 / 0))
        out = reg.invoke("t_boom")
        self.assertEqual(out["error"]["code"], "tool_failed")
        self.assertNotIn("Traceback", json.dumps(out))


class McpTests(unittest.TestCase):
    def rpc(self, server, *msgs):
        out = io.StringIO()
        server.out = out
        server.serve(io.StringIO("\n".join(json.dumps(m) for m in msgs) + "\n"))
        return [json.loads(line) for line in out.getvalue().splitlines()]

    def test_list_call_and_hidden_tools(self):
        reg, _ = _reg("observe")
        srv = Server(reg, name="t", version="0", instructions="i")
        init, listed, call, hidden = self.rpc(
            srv, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "t_read", "arguments": {"p": "x"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "t_change"}})
        self.assertTrue(init["result"]["capabilities"]["tools"]["listChanged"])
        self.assertEqual([t["name"] for t in listed["result"]["tools"]], ["t_read"])
        self.assertEqual(json.loads(call["result"]["content"][0]["text"])["echo"], "x")
        self.assertEqual(hidden["error"]["code"], -32602)

    def test_list_changed_notification(self):
        reg, _ = _reg()
        srv = Server(reg, name="t", version="0", instructions="i", out=io.StringIO())
        srv.initialized = True
        reg.changed()
        self.assertIn("notifications/tools/list_changed", srv.out.getvalue())


class SlinkBackendTests(unittest.TestCase):
    def test_arguments_are_quoted_for_the_remote_shell(self):
        seen = []

        def runner(cmd, **kw):
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, '{"ok": 1}', "")
        Slink(runner=runner).labctl("load", "m; rm -rf ~")
        self.assertEqual(seen[0][-1], "python3 projects/haven/ops/haven-core/labctl.py load 'm; rm -rf ~'")
        self.assertIn("BatchMode=yes", seen[0])

    def test_unreachable_timeout_and_lab_refusal(self):
        def down(cmd, **kw):
            return subprocess.CompletedProcess(cmd, 255, "", "Connection refused")

        def slow(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 1)

        def refuses(cmd, **kw):
            return subprocess.CompletedProcess(cmd, 1, '{"http_status": 409, "error": "GPU lease held"}', "")
        with self.assertRaises(ToolError) as e:
            Slink(runner=down).probe("gpu")
        self.assertEqual((e.exception.code, e.exception.refused), ("unreachable", True))
        with self.assertRaises(ToolError) as e:
            Slink(runner=slow).labctl("unload")
        self.assertEqual((e.exception.code, e.exception.refused), ("timeout", False))
        with self.assertRaises(ToolError) as e:
            Slink(runner=refuses).labctl("load", "m")
        self.assertEqual((e.exception.code, e.exception.refused), ("lab_refused", True))
        self.assertIn("GPU lease held", e.exception.message)


if __name__ == "__main__":
    unittest.main()
