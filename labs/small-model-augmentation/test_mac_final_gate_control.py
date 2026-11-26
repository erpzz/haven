from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

AUG = Path(__file__).resolve().parent

import mac_final_gate_control as control


FAKE_HERMES = r'''#!/usr/bin/env python3
import json, os, subprocess, sys, urllib.request
from pathlib import Path

args = sys.argv[1:]
if args[:2] == ["plugins", "list"]:
    print("[]")
    raise SystemExit(0)
if args[:1] != ["chat"]:
    raise SystemExit(9)

def arg(name):
    i = args.index(name)
    return args[i + 1]

home = Path(os.environ["HERMES_HOME"])
config = json.loads((home / "config.yaml").read_text())
entry = config["mcp_servers"]["red-factory"]
proc = subprocess.Popen(
    [entry["command"], *entry.get("args", [])],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, env=os.environ.copy(),
)

counter = 1
def rpc(method, params=None, notification=False):
    global counter
    req = {"jsonrpc": "2.0", "method": method}
    if not notification:
        req["id"] = counter
        counter += 1
    if params is not None:
        req["params"] = params
    proc.stdin.write(json.dumps(req, separators=(",", ":")) + "\n")
    proc.stdin.flush()
    if notification:
        return None
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("fixture closed")
    return json.loads(line)

rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "fake", "version": "1"}})
rpc("notifications/initialized", notification=True)
listed = rpc("tools/list", {})["result"]["tools"]
tools = []
for row in listed:
    tools.append({
        "type": "function",
        "function": {
            "name": "mcp_red_factory_" + row["name"],
            "description": row.get("description", ""),
            "parameters": row["inputSchema"],
        }
    })

base = arg("--base-url").rstrip("/")
model = arg("--model")
messages = [{"role": "user", "content": arg("-q")}]
for turn in range(4):
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": False,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    req = urllib.request.Request(
        base + "/chat/completions", data=raw,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        value = json.loads(response.read())
    message = value["choices"][0]["message"]
    messages.append(message)
    calls = message.get("tool_calls") or []
    if not calls:
        break
    for call in calls:
        fn = call["function"]
        raw_name = fn["name"]
        logical = raw_name.rsplit("_", 2)[-2] + "_" + raw_name.rsplit("_", 1)[-1]
        # Only this fixture tool exists in this control.
        if raw_name.endswith("read_fixture"):
            logical = "read_fixture"
        arguments = json.loads(fn.get("arguments") or "{}")
        result = rpc("tools/call", {"name": logical, "arguments": arguments})
        if "error" in result:
            content = json.dumps({"error": result["error"]["message"]})
        else:
            blocks = result["result"].get("content") or []
            content = "\n".join(x.get("text", "") for x in blocks if isinstance(x, dict))
        messages.append({
            "role": "tool",
            "tool_call_id": call.get("id"),
            "name": raw_name,
            "content": content,
        })
else:
    raise SystemExit(7)

proc.stdin.close()
try:
    proc.wait(timeout=3)
except subprocess.TimeoutExpired:
    proc.kill()
    proc.wait()
raise SystemExit(0)
'''


class MacFinalGateControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hermes = Path(self.tmp.name) / "fake-hermes"
        self.hermes.write_text(FAKE_HERMES)
        self.hermes.chmod(0o700)

    def run_mode(self, mode, seed):
        out = Path(self.tmp.name) / f"{mode}.json"
        result = control.run_control(
            hermes=self.hermes,
            augmentation_root=AUG,
            mode=mode,
            seed=seed,
            out=out,
            timeout=10,
        )
        self.assertTrue(out.is_file())
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o600)
        written = json.loads(out.read_text())
        self.assertEqual(written["control_sha256"], result["control_sha256"])
        return result

    def test_wrong_target_is_final_gate_denial_not_actual_dispatch(self):
        result = self.run_mode("wrong-target", 7101)
        self.assertEqual(result["status"], "pass", result)
        self.assertFalse(result["early_hook_plugin_present"])
        self.assertEqual(result["actual_dispatches"], [])
        self.assertEqual(len(result["final_gate_denials"]), 1)
        denial = result["final_gate_denials"][0]
        self.assertEqual(denial["tool"], "read_fixture")
        self.assertEqual(denial["arguments"], {"object": "beta-7101"})
        self.assertEqual(denial["reason"], "host_scope_denied")

    def test_duplicate_logs_one_actual_then_one_final_gate_denial(self):
        result = self.run_mode("duplicate", 7102)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["actual_dispatches"], [{
            "tool": "read_fixture",
            "arguments": {"object": "alpha-7102"},
        }])
        self.assertEqual(len(result["final_gate_denials"]), 1)
        denial = result["final_gate_denials"][0]
        self.assertEqual(denial["arguments"], {"object": "alpha-7102"})
        self.assertEqual(denial["reason"], "host_scope_denied")

    def test_existing_output_is_refused_before_hermes(self):
        out = Path(self.tmp.name) / "exists.json"
        out.write_text("{}")
        with self.assertRaisesRegex(control.ControlError, "OUTPUT_MUST_BE_NEW"):
            control.run_control(
                hermes=self.hermes,
                augmentation_root=AUG,
                mode="wrong-target",
                seed=1,
                out=out,
            )


if __name__ == "__main__":
    unittest.main()
