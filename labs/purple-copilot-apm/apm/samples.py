"""Content-addressed inputs for the isolated CE deployment."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(os.getenv("APM_STATE", Path.home() / ".local/state/purple-copilot-apm")).expanduser().resolve()
REVISION = "61d0859a461ccc0aad8b06fefabd6b4df0c079bc"
FILES = {
    "ad_sampledata.zip": "d32eb854bfaa1610078681c508a0ff7f2567f089eb9de00429a1cc951bf0b96e",
    "entra_sampledata.zip": "77c457ae41698844b28441827ca9c0ae74b6d1a3d47bfeea96ab7894aaa94662",
}


def checked(name):
    data = (ROOT / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != FILES[name]:
        raise ValueError(f"Unexpected sample hash for {name}")
    return data


def save(name, data):
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=ROOT, mode="w", delete=False) as f:
        json.dump(data, f)
    Path(f.name).replace(ROOT / name)


def read(name):
    return json.loads((ROOT / name).read_text())
