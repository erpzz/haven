"""Exercise the real Hermes plugin/dispatch/hook path in a temporary home."""
from pathlib import Path
import argparse
import json
import os
import shutil
import socket
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Hermes checkout; use an interpreter with its dependencies")
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / "model_tools.py").is_file():
        raise ValueError("Expected a Hermes source checkout")
    attempts = []

    def reject_network(*_args, **_kwargs):
        attempts.append(True)
        raise RuntimeError("Network is disabled in the Forge offline verification")

    with tempfile.TemporaryDirectory(prefix="forge-hermes-verification-") as temporary:
        home = Path(temporary)
        home.chmod(0o700)
        os.environ["HERMES_HOME"] = str(home)
        os.environ["TERMINAL_CWD"] = str(home)
        plugin = Path(__file__).parent / ".hermes/plugins/haven-forge"
        shutil.copytree(plugin, home / "plugins/haven-forge", ignore=shutil.ignore_patterns("__pycache__"))
        (home / "config.yaml").write_text(
            "plugins:\n  enabled:\n    - haven-forge\nterminal:\n  backend: local\n",
            encoding="utf-8",
        )
        sys.path.insert(0, str(source))
        socket.socket.connect = reject_network
        socket.create_connection = reject_network
        import model_tools
        from hermes_cli.plugins import discover_plugins
        discover_plugins(force=True)
        definitions = model_tools.get_tool_definitions(
            enabled_toolsets=["terminal", "haven-forge"], quiet_mode=True, skip_tool_search_assembly=True,
        )
        names = [definition["function"]["name"] for definition in definitions]
        for required in ("forge_knowledge_search", "forge_assess_entra", "terminal"):
            if required not in names:
                raise RuntimeError(f"Plugin/runtime tool was not exposed: {required}")
        outputs = []
        for name, arguments in (
            ("forge_knowledge_search", {"query": "report-only Conditional Access MFA"}),
            ("forge_assess_entra", {"question": "Do Entra policies require MFA?", "fixture": "entra-demo"}),
            ("terminal", {"command": "printf forge-synthetic-fixture", "timeout": 5}),
            ("forge_assess_entra", {"question": "Do Entra policies require MFA?", "fixture": "entra-demo",
                                    "policy_id": "synthetic-mfa-or-device"}),
        ):
            result = model_tools.handle_function_call(name, arguments, task_id="forge-offline-verification",
                                                      tool_call_id="synthetic-" + name, enabled_tools=names)
            outputs.append(json.loads(result))
        if not outputs[0].get("documents") or outputs[1].get("status") != "VERIFIED_SYNTHETIC":
            raise RuntimeError("Retrieval or assessment did not complete through Hermes dispatch")
        evidence = outputs[2].get("forge_evidence", {})
        if evidence.get("execution") != "succeeded" or evidence.get("objective_verified") is not False:
            raise RuntimeError("Real terminal result did not pass through the evidence hook")
        selected = outputs[3].get("findings", [])
        if len(selected) != 1 or selected[0].get("verdict") != "mfa_not_required_by_policy":
            raise RuntimeError("Hermes did not dispatch the selected synthetic policy assessment")
        sys.path.insert(0, str(plugin))
        from forge_runtime.router import route_synthetic
        routed = route_synthetic(
            "Does this Entra policy require MFA?", "entra-demo", "synthetic-mfa-or-device",
            lambda values: model_tools.handle_function_call("forge_assess_entra", values,
                task_id="forge-offline-verification", session_id="forge-offline-verification",
                tool_call_id="synthetic-routed-assessment", enabled_tools=names),
        )
        if routed.get("route_status") != "HANDLED":
            raise RuntimeError("Pre-model route did not verify the real Hermes tool result")
        if attempts:
            raise RuntimeError("Offline verification attempted network access")
        print(json.dumps({"passed": True, "real_hermes_tool_calls": 5, "native_hook_observed": True,
                          "pre_model_route_verified": True,
                          "model_invocations": 0, "network_attempts": 0, "live_home_modified": False}))


if __name__ == "__main__":
    main()
