"""Imported first by every test module: tests run against a private temporary engineer state and config; nothing touches the real Haven."""
import json
import os
import sys
import tempfile
from pathlib import Path

_BASE = Path(tempfile.mkdtemp(prefix="haven-hermes-test-"))
STATE, CONFIG = _BASE / "state", _BASE / "config"
# Engineer modules resolve their state directory at import time, so this must run before any of them load.
os.environ["HAVEN_ENGINEER_STATE"] = str(STATE)
os.environ["HAVEN_ENGINEER_CONFIG"] = str(CONFIG)
CONFIG.mkdir(parents=True, exist_ok=True)
WORKSPACE = _BASE / "ws-demo"
WORKSPACE.mkdir()
(CONFIG / "workspaces.json").write_text(json.dumps([{"name": "demo", "path": str(WORKSPACE), "kind": "disposable"}]))
(CONFIG / "fleet.json").write_text(json.dumps({"nodes": [{"name": "local", "kind": "local", "roles": ["tools"]},
                                                         {"name": "slink", "kind": "ssh", "ssh": "haven",
                                                          "roles": ["tools"]}]}))
(CONFIG / "scope.json").write_text(json.dumps({"network": False}))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
