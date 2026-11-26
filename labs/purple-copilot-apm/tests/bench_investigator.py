"""End-to-end native tool selection on three task types with the real Haven gateway."""
import asyncio
import os
import sys
import tempfile
import threading
from pathlib import Path

from apm.investigator import investigate
from apm.path_history import get_run, record_paths
from apm.paths import registry, sample_scan

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "model-lab"))
from gateway import Gateway
from labcore import Lab
from server import Server


async def bench():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        lab = Lab(data)
        os.environ["HAVEN_GATEWAY_KEY"] = Gateway.issue_key(data, "path-review", "member")
        lab.connect("http://127.0.0.1:8135/v1", kind="llama")
        with Server(("127.0.0.1", 8877), lab) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                run = record_paths(sample_scan(registry()["phantom-admins"]))
                _, findings = get_run(run)
                key = max(findings, key=lambda k: len(findings[k]["path"]))
                for task, expected in [("path", "path_evidence"), ("quality", "collection_quality"), ("triage", None)]:
                    result = await investigate(run, key, task)
                    print(task, result["selected_tools"], result["status"], result["seconds"], flush=True)
                    assert (result["selected_tools"] == [expected] if expected else
                            set(result["selected_tools"]) == {"path_evidence", "collection_quality"})
            finally:
                server.shutdown()
                thread.join()
                lab.shutdown()


if __name__ == "__main__":
    asyncio.run(bench())
