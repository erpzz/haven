"""Synthetic Hermes callback tests; not a claim that Mac Hermes loaded the hook."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from unittest import mock
import sys
import tempfile
import unittest

AUG = Path(__file__).resolve().parent
sys.path.insert(0, str(AUG))

import hermes_scope_plugin as plugin  # noqa: E402
import tool_context as routing  # noqa: E402
import tool_scope as scope  # noqa: E402

TARGET = "fixtures/allowed.json"
ARGS = {"tool_id": "entra.ca.assess", "arguments": {"snapshot_path": TARGET}}


def policy(max_calls=2, allowed=("cyber_call",)):
    if not allowed:
        return {
            "schema": scope.SCHEMA, "allowed_tools": [],
            "max_calls": 0, "per_tool_max": {},
            "unique_calls": True, "argument_rules": {},
        }
    rules = {}
    for name in allowed:
        if name == "cyber_call":
            rules[name] = {
                "allowed_keys": ["tool_id", "arguments"],
                "required_keys": ["tool_id", "arguments"],
                "exact_values": {
                    "/tool_id": ["entra.ca.assess"],
                    "/arguments": [{"snapshot_path": TARGET}],
                    "/arguments/snapshot_path": [TARGET],
                },
            }
        else:
            rules[name] = {
                "allowed_keys": ["object_id"],
                "required_keys": ["object_id"],
                "exact_values": {"/object_id": ["synthetic-A"]},
            }
    return {
        "schema": scope.SCHEMA, "allowed_tools": list(allowed),
        "max_calls": max_calls,
        "per_tool_max": {name: max_calls for name in allowed},
        "unique_calls": True, "argument_rules": rules,
    }


class FakeHermesContext:
    """Models dispatch ordering, not Hermes source code."""
    def __init__(self):
        self.callbacks = {}

    def register_hook(self, name, handler):
        self.callbacks[name] = handler

    def dispatch(self, name, args, implementation, session_id="s1"):
        gate = self.callbacks["pre_tool_call"](
            tool_name=name, args=args, session_id=session_id,
        )
        if gate and gate.get("action") == "block":
            return {"blocked": True, "message": gate["message"]}
        implementation()
        return {"blocked": False}


class HookIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "scope.json"
        self.write_policy(policy())
        self.gate = plugin.Gate(policy_path=str(self.path), augmentation_root=AUG)
        self.assertIsNone(self.gate._failed)

    def write_policy(self, p):
        self.path.write_text(json.dumps(p), encoding="utf-8")
        self.path.chmod(0o600)

    def context(self, gate=None):
        c = FakeHermesContext()
        c.register_hook("pre_tool_call", (gate or self.gate).pre_tool_call)
        return c

    def test_admit_exact_real_shape_and_block_extra_or_missing(self):
        self.assertEqual(self.gate.admit_surface(["cyber_call"])["status"], "pass")
        self.assertEqual(self.gate.admit_surface(["cyber_call", "terminal"])["status"], "block")
        self.assertEqual(self.gate.admit_surface([])["status"], "block")

    def test_canary_wrong_tool_never_executes(self):
        calls = []
        result = self.context().dispatch("write_canary", {}, lambda: calls.append("executed"))
        self.assertTrue(result["blocked"])
        self.assertEqual(calls, [])
        self.assertNotIn(TARGET, result["message"])

    def test_nested_scope_mismatch_never_executes(self):
        ctx = self.context()
        for changed in [
            {"tool_id": "another.tool", "arguments": {"snapshot_path": TARGET}},
            {"tool_id": "entra.ca.assess", "arguments": {"snapshot_path": "/etc/hosts"}},
            {"tool_id": "entra.ca.assess", "arguments": {"snapshot_path": TARGET, "extra": 1}},
            {"tool_id": "entra.ca.assess", "arguments": {}},
        ]:
            calls = []
            result = ctx.dispatch("cyber_call", changed, lambda: calls.append("executed"))
            self.assertTrue(result["blocked"], changed)
            self.assertFalse(calls)
        self.assertEqual(self.gate._states["s1"].total, 0)

    def test_approved_call_once_then_duplicate_blocks(self):
        ctx = self.context()
        calls = []
        first = ctx.dispatch("cyber_call", ARGS, lambda: calls.append("yes"))
        second = ctx.dispatch("cyber_call", ARGS, lambda: calls.append("again"))
        self.assertFalse(first["blocked"])
        self.assertTrue(second["blocked"])
        self.assertEqual(calls, ["yes"])

    def test_parallel_budget_is_atomic(self):
        # Distinct allowed calls must win at most two budget slots.
        p = policy(max_calls=2, allowed=("read_fixture",))
        p["unique_calls"] = False
        self.write_policy(p)
        gate = plugin.Gate(policy_path=str(self.path), augmentation_root=AUG)
        ctx = self.context(gate)
        count = []
        from threading import Lock
        lock = Lock()

        def implementation():
            with lock:
                count.append(1)

        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(
                lambda _: ctx.dispatch(
                    "read_fixture", {"object_id": "synthetic-A"}, implementation),
                range(24),
            ))
        self.assertEqual(sum(not r["blocked"] for r in results), 2)
        self.assertEqual(len(count), 2)

    def test_sessions_have_separate_budgets(self):
        ctx = self.context()
        calls = []
        self.assertFalse(ctx.dispatch("cyber_call", ARGS, lambda: calls.append(1), "a")["blocked"])
        self.assertFalse(ctx.dispatch("cyber_call", ARGS, lambda: calls.append(1), "b")["blocked"])
        self.assertEqual(len(calls), 2)

    def test_missing_session_id_blocks_without_effect(self):
        seen = []
        result = self.context().dispatch("cyber_call", ARGS, lambda: seen.append(1), "")
        self.assertTrue(result["blocked"])
        self.assertFalse(seen)

    def test_mutated_policy_permanently_blocks(self):
        self.assertIsNone(self.gate.pre_tool_call(tool_name="cyber_call", args=ARGS, session_id="s1"))
        self.write_policy(policy(max_calls=1))
        result = self.gate.pre_tool_call(tool_name="cyber_call", args=ARGS, session_id="s2")
        self.assertEqual(result["action"], "block")
        self.assertIn("POLICY_CHANGED", result["message"])

    def test_policy_file_permissions_fail_closed(self):
        self.path.chmod(0o644)
        self.assertEqual(
            self.gate.pre_tool_call(tool_name="cyber_call", args=ARGS, session_id="s1")["action"],
            "block",
        )
        failed = plugin.Gate(policy_path=str(self.path), augmentation_root=AUG)
        self.assertEqual(
            failed.pre_tool_call(tool_name="cyber_call", args=ARGS, session_id="s1")["action"],
            "block",
        )

    def test_policy_symlink_rejected(self):
        symlink = Path(self.dir.name) / "link"
        symlink.symlink_to(self.path)
        failed = plugin.Gate(policy_path=str(symlink), augmentation_root=AUG)
        self.assertEqual(failed.pre_tool_call(tool_name="cyber_call",
                                             args=ARGS, session_id="s1")["action"], "block")

    def test_engine_load_exception_does_not_remove_veto(self):
        with mock.patch.object(plugin, "_scope_engine", side_effect=SyntaxError("bad module")):
            failed = plugin.Gate(policy_path=str(self.path), augmentation_root=AUG)
        self.assertEqual(
            failed.pre_tool_call(tool_name="cyber_call", args=ARGS, session_id="s1")["action"],
            "block",
        )

    def test_register_valid_hook_and_enforce_dispatch(self):
        old_path = os.environ.get(plugin.POLICY_ENV)
        old_root = os.environ.get(plugin.ROOT_ENV)
        try:
            os.environ[plugin.POLICY_ENV] = str(self.path)
            os.environ[plugin.ROOT_ENV] = str(AUG)
            ctx = FakeHermesContext()
            plugin.register(ctx)
            done = []
            self.assertTrue(ctx.dispatch("terminal", {"command": "id"},
                                         lambda: done.append(1))["blocked"])
            self.assertFalse(ctx.dispatch("cyber_call", ARGS,
                                          lambda: done.append(2))["blocked"])
            self.assertEqual(done, [2])
        finally:
            for key, old in ((plugin.POLICY_ENV, old_path), (plugin.ROOT_ENV, old_root)):
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old

    def test_missing_invalid_policy_still_registers_veto(self):
        old = os.environ.get(plugin.POLICY_ENV)
        try:
            os.environ[plugin.POLICY_ENV] = str(Path(self.dir.name) / "missing")
            ctx = FakeHermesContext()
            plugin.register(ctx)
            self.assertIn("pre_tool_call", ctx.callbacks)
            result = ctx.dispatch("write_canary", {}, lambda: self.fail("canary executed"))
            self.assertTrue(result["blocked"])
        finally:
            if old is None:
                os.environ.pop(plugin.POLICY_ENV, None)
            else:
                os.environ[plugin.POLICY_ENV] = old

    def test_zero_tool_session_blocks_all_dispatch(self):
        self.write_policy(policy(allowed=()))
        gate = plugin.Gate(policy_path=str(self.path), augmentation_root=AUG)
        self.assertEqual(gate.admit_surface([])["status"], "pass")
        count = []
        result = self.context(gate).dispatch("write_canary", {}, lambda: count.append(1))
        self.assertTrue(result["blocked"])
        self.assertEqual(count, [])

    def test_routing_surface_matches_scope_and_hidden_canary_stays_denied(self):
        cards = [
            {"name": "read_fixture", "effect": "read",
             "route_terms": ["read", "fixture"],
             "definition": {"name": "read_fixture", "description": "safe", "parameters": {}}},
            {"name": "write_canary", "effect": "change",
             "route_terms": ["write", "fixture"],
             "definition": {"name": "write_canary", "description": "synthetic", "parameters": {}}},
        ]
        routed = routing.route(cards, "read fixture",
                               authorized=["read_fixture"], allowed_effects=("read",))
        self.assertEqual(routed["status"], "pass")
        self.assertEqual(routed["selected"], ["read_fixture"])
        self.write_policy(policy(allowed=("read_fixture",)))
        gate = plugin.Gate(policy_path=str(self.path), augmentation_root=AUG)
        self.assertEqual(gate.admit_surface(routed["selected"])["status"], "pass")
        ctx = self.context(gate)
        executed = []
        self.assertTrue(ctx.dispatch("write_canary", {},
                                     lambda: executed.append("canary"))["blocked"])
        self.assertFalse(ctx.dispatch("read_fixture", {"object_id": "synthetic-A"},
                                      lambda: executed.append("read"))["blocked"])
        self.assertEqual(executed, ["read"])


if __name__ == "__main__":
    unittest.main()
