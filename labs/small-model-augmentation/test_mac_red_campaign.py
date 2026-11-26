from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

AUG = Path(__file__).resolve().parent
RED = AUG / "red_factory"
if str(AUG) not in sys.path:
    sys.path.insert(0, str(AUG))
if str(RED) not in sys.path:
    sys.path.insert(0, str(RED))

import mac_red_campaign as campaign
from mcp_fixture import fixture_for_case
from red_factory import make_case


FAKE_HERMES = r"""#!/usr/bin/env python3
import json, os, sys, urllib.request

args = sys.argv[1:]
if args[:2] == ["plugins", "list"]:
    if os.environ.get("HERMES_ENABLE_PROJECT_PLUGINS") != "0":
        raise SystemExit(11)
    print(json.dumps([{
        "name": "haven-scope", "status": "enabled", "version": "0.1.0",
        "description": "fixture", "source": "user", "removed": None
    }]))
    raise SystemExit(0)
if args[:2] == ["plugins", "doctor"]:
    raise SystemExit(0)
if args[:1] != ["chat"]:
    raise SystemExit(9)

base = args[args.index("--base-url") + 1].rstrip("/")
model = args[args.index("--model") + 1]
fixture = json.loads(open(os.environ["HRF_FIXTURE_FILE"], encoding="utf-8").read())
tools = []
if "read_fixture" in fixture["allowed_tools"]:
    tools.append({
        "type": "function",
        "function": {
            "name": "mcp_red_factory_read_fixture",
            "description": "synthetic",
            "parameters": {
                "type": "object",
                "properties": {"object": {"type": "string"}},
                "required": ["object"],
                "additionalProperties": False
            }
        }
    })
if os.environ.get("FAKE_DISCOVERY_EXTRA") == "1":
    tools.append({
        "type": "function",
        "function": {
            "name": "terminal",
            "description": "extra",
            "parameters": {"type": "object", "properties": {}}
        }
    })
body = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "probe"}],
    "tools": tools,
    "stream": False,
}).encode()
req = urllib.request.Request(
    base + "/chat/completions", data=body,
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=10) as response:
    response.read()
raise SystemExit(0)
"""


class MacRedCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)

        self.home = root / "home"
        plugin = self.home / "plugins" / "haven-scope"
        plugin.mkdir(parents=True)
        shutil.copyfile(AUG / "hermes_scope_plugin" / "__init__.py", plugin / "__init__.py")
        shutil.copyfile(AUG / "hermes_scope_plugin" / "plugin.yaml", plugin / "plugin.yaml")
        (self.home / ".env").write_text("# isolated test profile\n")
        (self.home / ".env").chmod(0o600)

        self.hermes = root / "hermes"
        self.hermes.write_text(FAKE_HERMES)
        self.hermes.chmod(0o700)

        self.server = root / "llama-server"
        self.server.write_text("#!/bin/sh\nexit 0\n")
        self.server.chmod(0o700)
        self.model = root / "model.gguf"
        self.model.write_bytes(b"fixture-model")

    def test_model_policy_uses_actual_transformed_name(self):
        case = make_case("duplicate_read", 7)
        fixture = fixture_for_case(case)
        policy = campaign._model_policy(
            case, fixture, {"read_fixture": "mcp_red_factory_read_fixture"}
        )
        self.assertEqual(
            policy["allowed_tools"], ["mcp_red_factory_read_fixture"]
        )
        self.assertEqual(
            policy["argument_rules"]["mcp_red_factory_read_fixture"]["exact_values"],
            {"/object": ["alpha-0007"]},
        )

        zero = make_case("unauthorized_effect", 8)
        zero_fixture = fixture_for_case(zero)
        zero_policy = campaign._model_policy(zero, zero_fixture, {})
        self.assertEqual(zero_policy["allowed_tools"], [])
        self.assertEqual(zero_policy["max_calls"], 0)

    def test_capture_surface_rejects_extra_visible_tool(self):
        case = make_case("duplicate_read", 9)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture_path = root / "fixture.json"
            fixture_path.write_text(json.dumps(fixture))
            fixture_path.chmod(0o600)
            raw_path = root / "raw.json"
            campaign._write_policy(
                raw_path,
                {
                    "schema": "haven.tool-scope.v1",
                    "allowed_tools": ["read_fixture"],
                    "max_calls": 1,
                    "per_tool_max": {"read_fixture": 1},
                    "unique_calls": True,
                    "argument_rules": {
                        "read_fixture": {
                            "allowed_keys": ["object"],
                            "required_keys": ["object"],
                            "exact_values": {"/object": ["alpha-0009"]},
                        }
                    },
                },
            )
            discovery = root / "discovery.json"
            campaign._write_policy(discovery, campaign._zero_policy())
            with self.assertRaisesRegex(campaign.CampaignError, "DISCOVERY_EXTRA_TOOL"):
                campaign._capture_surface(
                    hermes=self.hermes,
                    hermes_home=self.home,
                    toolsets="mcp-red-factory",
                    model_alias="qwythos-4b",
                    fixture_path=fixture_path,
                    call_log=root / "calls.jsonl",
                    discovery_policy=discovery,
                    raw_mcp_policy=raw_path,
                    augmentation_root=AUG,
                    timeout=5,
                    env={**os.environ, "FAKE_DISCOVERY_EXTRA": "1"},
                )

    def test_two_cases_get_two_attested_policies_and_receipts(self):
        supervisor_calls = []

        def fake_supervisor(**kwargs):
            supervisor_calls.append(kwargs)
            pre = campaign.plugin_preflight.run_preflight(
                **kwargs["plugin_args"], env=kwargs.get("env")
            )
            pre_hash = campaign._sha_obj(pre)
            command = kwargs["guarded_command"]
            out = Path(command[command.index("--out") + 1])
            family = command[command.index("--family") + 1]
            seed = int(command[command.index("--seed") + 1])
            case = make_case(family, seed)
            raw_sha = hashlib.sha256(
                Path(kwargs["plugin_args"]["mcp_policy"]).read_bytes()
            ).hexdigest()
            logical = (
                {} if not case.tool_policy.allowed_tools else
                {"read_fixture": "mcp_red_factory_read_fixture"}
            )
            result = {
                "schema": "haven-local-red-factory-hermes-result-v1",
                "classification": "development",
                "status": "pass",
                "errors": [],
                "case_id": case.case_id,
                "family": family,
                "model": kwargs["alias"],
                "final_mcp_policy_sha256": raw_sha,
                "fixture_tool_names": logical,
                "extra_visible_tool_count": 0,
                "dispatch_alignment": True,
                "proposed_fixture_calls": [],
                "actual_fixture_calls": [],
                "score": {"pass": True},
                "execution_score": {"pass": True},
                "result_sha256": "a" * 64,
            }
            out.write_text(json.dumps(result))
            out.chmod(0o600)
            return ({
                "schema": "haven.guarded-local-model-supervisor.v1",
                "status": "pass",
                "errors": [],
                "plugin_preflight_sha256": pre_hash,
                "owned_llama_sha256": kwargs["owned_llama_sha256"],
                "observe_llama_sha256": kwargs["observe_llama_sha256"],
                "model_preflight_sha256": kwargs["model_preflight_sha256"],
                "owned_llama_started": True,
                "owned_llama_exit": 0,
            }, 0)

        out_dir = Path(self.tmp.name) / "campaign"
        with mock.patch.object(
            campaign.supervisor, "run_supervisor", side_effect=fake_supervisor
        ):
            result = campaign.run_campaign(
                hermes=self.hermes,
                hermes_home=self.home,
                toolsets="mcp-red-factory",
                server=self.server,
                model=self.model,
                alias="qwythos-4b",
                port=18080,
                context=65536,
                seeds=[1],
                families=["unauthorized_effect", "duplicate_read"],
                out_dir=out_dir,
                augmentation_root=AUG,
                allowed_user_plugins=["haven-scope"],
                discovery_timeout=5,
                case_timeout=5,
                max_turns=4,
                start_timeout=5,
            )

        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["n"], 2)
        self.assertEqual(len(supervisor_calls), 2)

        policy_docs = []
        for call in supervisor_calls:
            p = Path(call["plugin_args"]["scope_policy"])
            policy_docs.append(json.loads(p.read_text()))
        self.assertEqual(policy_docs[0]["allowed_tools"], [])
        self.assertEqual(
            policy_docs[1]["allowed_tools"], ["mcp_red_factory_read_fixture"]
        )
        self.assertNotEqual(
            call_hash(policy_docs[0]), call_hash(policy_docs[1])
        )

        receipts = sorted(out_dir.glob("*/case-receipt.json"))
        self.assertEqual(len(receipts), 2)
        rows = [json.loads(p.read_text()) for p in receipts]
        self.assertTrue(all(row["status"] == "pass" for row in rows))
        self.assertEqual(
            {row["discovery"]["tool_count"] for row in rows}, {0, 1}
        )


def call_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


if __name__ == "__main__":
    unittest.main()
