"""Exercise the real Haven gateway and a local model in an isolated Lab instance."""
import os
import re
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from apm.analyst import analyze
from apm.graph import snapshot
from apm.store import record

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "model-lab"))
from gateway import Gateway
from labcore import Lab
from server import Server


def check():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        lab = Lab(data)
        key = Gateway.issue_key(data, "purple-test", "member")
        lab.connect("http://127.0.0.1:8135/v1", kind="llama")
        with Server(("127.0.0.1", 8877), lab) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with patch.dict(os.environ, HAVEN_GATEWAY_KEY=key):
                    run = record(snapshot("entra"))
                    answer = analyze(run)
                    assert re.search(r"\b(1|one|single)\b", answer, re.I)
                    print("Authenticated Haven gateway returned a saved sample review for run", run)
            finally:
                server.shutdown()
                thread.join()
                lab.shutdown()


if __name__ == "__main__":
    check()
