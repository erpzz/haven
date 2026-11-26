"""Verify unmodified output files from serialize.ps1 using production import functions."""
import hashlib
import sys
from pathlib import Path

from apm.offline.demo import fixture
from apm.offline.vault import ingest
from apm.offline.formats import parse

for name, fmt in (("opengraph", "entraops_opengraph"), ("maester", "maester_2x")):
    raw = (Path(sys.argv[1]) / (name + ".json")).read_bytes()
    manifest = dict(fixture(fmt + ".receipt"), run="upstream-synthetic-" + name,
                    sha256=hashlib.sha256(raw).hexdigest())
    aid, status = ingest(raw, manifest)
    doc = parse(raw)
    if name == "opengraph":
        assert len(doc["graph"]["edges"]) == 4
    else:
        assert doc["Tests"][0]["Id"] == "MT.SYN.824" and doc["Tests"][0]["Result"] == "Passed"
    print(name, status, manifest["sha256"])
