import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import tool_visibility


FAKE = r'''#!/usr/bin/env python3
import json, os, sys, urllib.request
args=sys.argv[1:]
mode=os.environ.get("FAKE_MODE", "pass")
if mode == "unknown":
    sys.stderr.write("Warning: Unknown toolsets: mcp-haven-cyber\nsecret=DO_NOT_ECHO\n")
if mode == "exit":
    sys.stderr.write("token=DO_NOT_ECHO\n"); raise SystemExit(7)
if mode == "no-request":
    raise SystemExit(0)
if mode == "sleep":
    import time; time.sleep(5); raise SystemExit(0)
base=args[args.index("--base-url")+1]
tools=[{"type":"function","function":{"name":"mcp_haven_status","description":"x","parameters":{"type":"object"}}},
       {"type":"function","function":{"name":"mcp_haven_cyber_assess","description":"x","parameters":{"type":"object"}}}]
if mode == "missing": tools=tools[:1]
if mode == "modern": tools=[{"type":"function","function":{"name":"mcp__red_factory__read_fixture","description":"x","parameters":{"type":"object"}}}]
if mode == "bridge": tools=[{"type":"function","function":{"name":"tool_search","description":"x","parameters":{"type":"object"}}}]
if mode == "cyber-only": tools=tools[1:]
if mode == "duplicate": tools=tools+tools[:1]
if mode == "bad-schema": tools=[{"type":"function","function":{}}]
payload={"model":"haven-tool-visibility-probe","messages":[{"role":"user","content":"x"}],"tools":tools,"stream":False}
if mode == "bad-request": payload["model"]="wrong-model"
req=urllib.request.Request(base+"/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req, timeout=3) as r: r.read()
raise SystemExit(0)
'''


class VisibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hermes = Path(self.tmp.name, "hermes")
        self.hermes.write_text(FAKE)
        self.hermes.chmod(self.hermes.stat().st_mode | stat.S_IXUSR)

    def tearDown(self):
        self.tmp.cleanup()

    def probe(self, mode="pass", prefixes=None, toolsets="mcp-haven,mcp-haven-cyber"):
        env = dict(os.environ, FAKE_MODE=mode)
        return tool_visibility.run_probe(str(self.hermes), self.tmp.name, toolsets,
                                         prefixes or ["mcp_haven_", "mcp_haven_cyber_"], env=env, timeout=5)

    def test_pass_exact_model_visible_prefixes(self):
        r = self.probe()
        self.assertEqual(r["schema"], "haven.hermes-tool-visibility.v2")
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["tool_count"], 2)
        self.assertEqual(
            r["tool_names"],
            ["mcp_haven_status", "mcp_haven_cyber_assess"],
        )
        self.assertRegex(r["tool_surface_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(r["required_prefix_counts"], {"mcp_haven_": 1, "mcp_haven_cyber_": 1})
        self.assertEqual(r["model_requests"], 1)

    def test_exact_name_sequence_and_surface_hash_can_be_replayed(self):
        discovered = self.probe()
        env = dict(os.environ, FAKE_MODE="pass")
        replay = tool_visibility.run_probe(
            str(self.hermes), self.tmp.name, "mcp-haven,mcp-haven-cyber",
            ["mcp_haven_", "mcp_haven_cyber_"],
            env=env, timeout=5,
            expected_names=discovered["tool_names"],
            expected_surface_sha256=discovered["tool_surface_sha256"],
        )
        self.assertEqual(replay["status"], "pass", replay)
        self.assertEqual(replay["tool_names"], discovered["tool_names"])
        self.assertEqual(
            replay["tool_surface_sha256"], discovered["tool_surface_sha256"]
        )

    def test_name_sequence_mismatch_blocks_even_when_prefixes_still_match(self):
        env = dict(os.environ, FAKE_MODE="pass")
        result = tool_visibility.run_probe(
            str(self.hermes), self.tmp.name, "mcp-haven,mcp-haven-cyber",
            ["mcp_haven_", "mcp_haven_cyber_"],
            env=env, timeout=5,
            expected_names=[
                "mcp_haven_cyber_assess",
                "mcp_haven_status",
            ],
        )
        self.assertIn("TOOL_NAME_SEQUENCE_MISMATCH", result["errors"])
        self.assertNotIn("MISSING_REQUIRED_PREFIX", result["errors"])

    def test_surface_hash_mismatch_blocks_even_when_names_match(self):
        discovered = self.probe()
        env = dict(os.environ, FAKE_MODE="pass")
        result = tool_visibility.run_probe(
            str(self.hermes), self.tmp.name, "mcp-haven,mcp-haven-cyber",
            ["mcp_haven_", "mcp_haven_cyber_"],
            env=env, timeout=5,
            expected_names=discovered["tool_names"],
            expected_surface_sha256="0" * 64,
        )
        self.assertIn("TOOL_SURFACE_HASH_MISMATCH", result["errors"])
        self.assertNotIn("TOOL_NAME_SEQUENCE_MISMATCH", result["errors"])

    def test_invalid_expected_surface_inputs_fail_before_process(self):
        bad_name = tool_visibility.run_probe(
            str(self.hermes), self.tmp.name, "mcp-haven",
            ["mcp_haven_"], expected_names=["bad name"]
        )
        bad_hash = tool_visibility.run_probe(
            str(self.hermes), self.tmp.name, "mcp-haven",
            ["mcp_haven_"], expected_surface_sha256="not-a-hash"
        )
        self.assertEqual(bad_name["errors"], ["INVALID_EXPECTED_TOOL_NAME"])
        self.assertEqual(bad_hash["errors"], ["INVALID_EXPECTED_SURFACE_HASH"])
        self.assertFalse(bad_name["actual_hermes_executed"])
        self.assertFalse(bad_hash["actual_hermes_executed"])

    def test_current_hermes_double_underscore_mcp_name_is_attested(self):
        r = self.probe(
            "modern",
            prefixes=["mcp__red_factory__"],
            toolsets="mcp-red-factory",
        )
        self.assertEqual(r["status"], "pass", r)
        self.assertEqual(r["tool_names"], ["mcp__red_factory__read_fixture"])
        self.assertRegex(r["tool_surface_sha256"], r"^[0-9a-f]{64}$")

    def test_missing_prefix_blocks(self):
        r = self.probe("missing")
        self.assertEqual(r["status"], "block")
        self.assertIn("MISSING_REQUIRED_PREFIX", r["errors"])

    def test_unknown_toolset_blocks_even_if_request_has_tools(self):
        r = self.probe("unknown")
        self.assertIn("UNKNOWN_TOOLSET", r["errors"])
        self.assertNotIn("DO_NOT_ECHO", json.dumps(r))

    def test_nonzero_and_no_request(self):
        r = self.probe("exit")
        self.assertEqual(set(r["errors"]), {"HERMES_EXIT_NONZERO", "NO_MODEL_REQUEST"})
        self.assertEqual(r["hermes_exit_code"], 7)
        self.assertNotIn("DO_NOT_ECHO", json.dumps(r))
        self.assertIn("NO_MODEL_REQUEST", self.probe("no-request")["errors"])

    def test_malformed_and_duplicate_tools_block(self):
        self.assertIn("INVALID_TOOL_SCHEMA", self.probe("bad-schema")["errors"])
        self.assertIn("INVALID_TOOL_SCHEMA", self.probe("duplicate")["errors"])

    def test_inputs_fail_before_process(self):
        cases = [
            tool_visibility.run_probe(str(self.hermes), self.tmp.name, "bad toolset", ["mcp_haven_"]),
            tool_visibility.run_probe(str(self.hermes), self.tmp.name, "mcp-haven", ["bad prefix"]),
            tool_visibility.run_probe("/does/not/exist", self.tmp.name, "mcp-haven", ["mcp_haven_"]),
            tool_visibility.run_probe(str(self.hermes), self.tmp.name, "mcp-haven", ["mcp_haven_"], cwd="/does/not/exist"),
            tool_visibility.run_probe(str(self.hermes), "/does/not/exist", "mcp-haven", ["mcp_haven_"]),
            tool_visibility.run_probe(str(self.hermes), self.tmp.name, "mcp-haven", ["mcp_haven_", "mcp_haven_"]),
        ]
        self.assertEqual([r["errors"] for r in cases], [["INVALID_TOOLSETS"], ["INVALID_REQUIRED_PREFIX"],
                                                        ["HERMES_NOT_EXECUTABLE"], ["INVALID_WORKING_DIRECTORY"],
                                                        ["INVALID_HERMES_HOME"], ["INVALID_REQUIRED_PREFIX"]])
        self.assertTrue(all(r["actual_hermes_executed"] is False for r in cases))

    def test_executed_flag_is_true_after_launch(self):
        self.assertTrue(self.probe()["actual_hermes_executed"])
        self.assertTrue(self.probe("exit")["actual_hermes_executed"])

    def test_loopback_model_probe_bypasses_environment_proxy(self):
        env = dict(os.environ, FAKE_MODE="pass", HTTP_PROXY="http://127.0.0.1:9",
                   HTTPS_PROXY="http://127.0.0.1:9", ALL_PROXY="http://127.0.0.1:9",
                   NO_PROXY="", no_proxy="")
        r = tool_visibility.run_probe(
            str(self.hermes), self.tmp.name, "mcp-haven,mcp-haven-cyber",
            ["mcp_haven_", "mcp_haven_cyber_"], env=env, timeout=5)
        self.assertEqual(r["status"], "pass", r)
        self.assertEqual(r["model_requests"], 1)

    def test_tool_search_bridge_does_not_count_as_direct_visibility(self):
        r = self.probe("bridge")
        self.assertEqual(r["tool_count"], 1)
        self.assertIn("MISSING_REQUIRED_PREFIX", r["errors"])

    def test_overlapping_prefixes_do_not_false_pass(self):
        r = self.probe("cyber-only")
        self.assertEqual(r["required_prefix_counts"], {"mcp_haven_": 0, "mcp_haven_cyber_": 1})
        self.assertIn("MISSING_REQUIRED_PREFIX", r["errors"])

    def test_timeout_is_fixed_and_marks_execution(self):
        env = dict(os.environ, FAKE_MODE="sleep")
        r = tool_visibility.run_probe(str(self.hermes), self.tmp.name, "mcp-haven", ["mcp_haven_"],
                                      env=env, timeout=1)
        self.assertEqual(r["errors"], ["HERMES_TIMEOUT"])
        self.assertTrue(r["actual_hermes_executed"])
        self.assertIsNone(r["hermes_exit_code"])

    def test_exec_failure_is_fixed_and_redacted(self):
        broken = Path(self.tmp.name, "broken-hermes")
        broken.write_text("not an executable format")
        broken.chmod(broken.stat().st_mode | stat.S_IXUSR)
        r = tool_visibility.run_probe(str(broken), self.tmp.name, "mcp-haven", ["mcp_haven_"], timeout=1)
        self.assertEqual(r["errors"], ["HERMES_EXEC_FAILED"])
        self.assertTrue(r["actual_hermes_executed"])
        self.assertNotIn(str(broken), json.dumps(r))

    def test_malformed_model_request_is_reported_without_echo(self):
        r = self.probe("bad-request")
        self.assertIn("INVALID_MODEL_REQUEST", r["errors"])
        self.assertIn("HERMES_EXIT_NONZERO", r["errors"])
        self.assertIn("NO_MODEL_REQUEST", r["errors"])
        self.assertNotIn("wrong-model", json.dumps(r))

    def test_cli_receipt_is_fixed_and_redacted(self):
        env = dict(os.environ, FAKE_MODE="unknown")
        import subprocess, sys
        cp = subprocess.run([sys.executable, str(Path(tool_visibility.__file__)), "--hermes", str(self.hermes),
                             "--hermes-home", self.tmp.name, "--toolsets", "mcp-haven,mcp-haven-cyber", "--require-prefix", "mcp_haven_",
                             "--require-prefix", "mcp_haven_cyber_"], env=env, text=True, capture_output=True)
        self.assertEqual(cp.returncode, 2)
        self.assertEqual(json.loads(cp.stdout)["status"], "block")
        self.assertNotIn("DO_NOT_ECHO", cp.stdout + cp.stderr)


if __name__ == "__main__":
    unittest.main()
