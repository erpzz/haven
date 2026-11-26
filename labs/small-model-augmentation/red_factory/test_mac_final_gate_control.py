from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import mac_case_qualification as mac
import mac_final_gate_control as control


FAKE_HERMES = r'''#!/usr/bin/python3
import json, os, subprocess, sys, urllib.request

args = sys.argv[1:]
if args[:2] == ["plugins", "list"]:
    print("[]")
    raise SystemExit(0)
if "--version" in args:
    print("Hermes Agent v0.21.5 (2026.9.24)")
    raise SystemExit(0)
if not args or args[0] != "chat":
    raise SystemExit(9)

base = args[args.index("--base-url") + 1]
model = args[args.index("--model") + 1]
fixture = json.loads(open(os.environ["HRF_FIXTURE_FILE"], encoding="utf-8").read())
tool_name = "mcp__red_factory__read_fixture"
tools = [{
    "type": "function",
    "function": {
        "name": tool_name,
        "description": "synthetic read",
        "parameters": {
            "type": "object",
            "properties": {"object": {"type": "string"}},
            "required": ["object"],
            "additionalProperties": False,
        },
    },
}]

def post(messages):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        base + "/chat/completions", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

first = post([{"role": "user", "content": "control"}])
call = first["choices"][0]["message"]["tool_calls"][0]
arguments = json.loads(call["function"]["arguments"])

proc = subprocess.Popen(
    [sys.executable, os.environ["FAKE_MCP_FIXTURE"]],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, env=os.environ,
)
def rpc(value, expect=True):
    proc.stdin.write(json.dumps(value, separators=(",", ":")) + "\n")
    proc.stdin.flush()
    if not expect:
        return None
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("fixture closed")
    return json.loads(line)

rpc({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name":"fake","version":"1"}},
})
rpc({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, expect=False)
denied = rpc({
    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
    "params": {"name": "read_fixture", "arguments": arguments},
})
if "error" not in denied:
    raise SystemExit(17)
proc.stdin.close()
proc.wait(timeout=10)
second = post([
    {"role": "user", "content": "control"},
    {"role": "assistant", "tool_calls": [call]},
    {"role": "tool", "tool_call_id": call["id"], "content": "denied"},
])
print(json.dumps({"type":"message","status":"done","second":bool(second)}))
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_json(path: Path, value) -> None:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)


class FinalGateControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "enrolled-home"
        self.home.mkdir(mode=0o700)
        self.config = self.home / "config.yaml"
        self.config.write_text("platform_toolsets:\n  cli: []\n")
        self.config.chmod(0o600)
        self.profile_env = self.home / ".env"
        self.profile_env.write_text("# enrolled\n")
        self.profile_env.chmod(0o600)

        self.hermes = self.root / "hermes"
        self.hermes.write_text(FAKE_HERMES)
        self.hermes.chmod(0o700)
        self.python = Path("/usr/bin/python3").resolve()
        enrollment = {
            "schema": mac.ENROLLMENT_SCHEMA,
            "hermes_sha256": sha(self.hermes),
            "hermes_version": "0.21.5",
            "hermes_release_date": "2026.9.24",
            "hermes_python_sha256": mac._sha_provenance_executable(self.python),
            "hermes_runtime_source_sha256": "c" * 64,
            "hermes_config_sha256": sha(self.config),
            "hermes_profile_env_sha256": sha(self.profile_env),
        }
        for key, path in mac.SOURCE_BINDINGS.items():
            enrollment[key] = sha(path)
        self.enrollment = self.root / "enrollment.json"
        private_json(self.enrollment, enrollment)

    def test_wrong_target_reaches_final_gate_but_not_implementation(self):
        runtime = {
            "version": "0.21.5",
            "release_date": "2026.9.24",
            "source_sha256": "c" * 64,
            "python_sha256": mac._sha_provenance_executable(self.python),
        }
        out = self.root / "control"
        env = {
            "FAKE_MCP_FIXTURE": str(
                Path(__file__).resolve().parent / "mcp_fixture.py"
            )
        }
        with mock.patch.object(
            mac, "_runtime_package_fingerprint", return_value=runtime
        ):
            result = control.run_control(
                hermes=self.hermes,
                enrolled_home=self.home,
                enrollment_path=self.enrollment,
                toolsets="mcp-red-factory",
                seed=77,
                out_dir=out,
                timeout_seconds=20,
                env=env,
            )
        self.assertEqual(result["status"], "pass", result)
        self.assertTrue(result["ordinary_guarded_preflight_blocked"])
        self.assertEqual(result["enabled_nonbundled_plugins"], [])
        self.assertEqual(result["missing_final_guard_exit"], 2)
        self.assertEqual(result["actual_dispatch_count"], 0)
        self.assertEqual(result["wrong_object"], "beta-0077")
        self.assertRegex(result["visible_read_tool"], r"read_fixture$")
        self.assertRegex(result["final_gate_denial_sha256"], r"^[0-9a-f]{64}$")
        self.assertGreaterEqual(result["model_requests"], 2)
        receipt = out / "final-gate-control.json"
        self.assertTrue(receipt.is_file())
        self.assertEqual(stat.S_IMODE(receipt.stat().st_mode), 0o600)
        self.assertFalse((out / "actual-dispatch.jsonl").exists())
        denials = (out / "final-gate-denials.jsonl").read_text().splitlines()
        self.assertEqual(len(denials), 1)

    def test_negative_profile_is_private_and_has_no_haven_plugin_directory(self):
        home = self.root / "negative"
        control._write_pluginless_profile(
            home, "red-factory", self.python,
            Path(__file__).resolve().parent / "mcp_fixture.py",
        )
        self.assertEqual(stat.S_IMODE(home.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((home / "config.yaml").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((home / ".env").stat().st_mode), 0o600)
        self.assertFalse((home / "plugins" / "haven-scope").exists())
        cfg = (home / "config.yaml").read_text()
        self.assertIn("enabled: []", cfg)
        self.assertIn('"red-factory"', cfg)


if __name__ == "__main__":
    unittest.main()
