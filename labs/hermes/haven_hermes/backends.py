"""How the server reaches Haven: Slink over ssh with fixed argv lists, never a shell string from the model.

Slink commands follow ops/haven-core/slink-lab.py: `ssh -o BatchMode=yes haven python3 <repo>/...`, so the
Model Lab bearer token stays on Slink. Every argument is shell-quoted for the remote shell and has already
been validated against a strict pattern by the tool's schema. A timeout kills the local ssh process and is
reported as `timeout` (the receipt then says `unknown`).
"""
from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from .registry import ToolError, scrub

PROBE = Path(__file__).with_name("slink_probe.py")
SSH = ("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=10")


class Slink:
    def __init__(self, host: str = "haven", repo: str = "projects/haven", runner=subprocess.run):
        self.host, self.repo, self.runner = host, repo, runner

    def run(self, argv: list[str], *, timeout: float = 30, stdin: str | None = None) -> subprocess.CompletedProcess:
        cmd = [*SSH, self.host, shlex.join(argv)]
        try:
            r = self.runner(cmd, input=stdin, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise ToolError("timeout", f"Slink did not answer within {timeout:.0f} s") from None
        if r.returncode == 255:
            raise ToolError("unreachable", "ssh to Slink failed: " + scrub(r.stderr.strip()[-300:]), refused=True)
        return r

    def probe(self, command: str, *, timeout: float = 40) -> dict:
        r = self.run(["python3", "-", command], timeout=timeout, stdin=PROBE.read_text())
        return _json(r, "probe")

    def labctl(self, *args: str, timeout: float = 40) -> dict:
        r = self.run(["python3", f"{self.repo}/ops/haven-core/labctl.py", *args], timeout=timeout)
        try:
            out = _json(r, "labctl")
        except ToolError:
            if r.returncode:  # labctl exits with a plain message when the Lab itself is down
                raise ToolError("lab_unavailable", scrub((r.stderr or r.stdout).strip()[-300:]), refused=True)
            raise
        if isinstance(out, dict) and out.get("http_status"):
            # The Lab answered and refused (GPU lease, busy engine, unknown model): nothing was started.
            msg = out.get("error") or out.get("message") or json.dumps(out)[:300]
            raise ToolError("lab_refused", f"Model Lab refused (HTTP {out['http_status']}): {msg}", refused=True)
        return out


def _json(r, what):
    text = (r.stdout or "").strip()
    try:
        return json.loads(text) if text.startswith(("{", "[")) else json.loads(text.splitlines()[-1])
    except (ValueError, IndexError):
        raise ToolError(f"{what}_failed", f"{what} returned no JSON (exit {r.returncode}): "
                        + scrub((r.stderr or text).strip()[-300:])) from None
