"""A fake Slink: canned probe and labctl answers, and a record of every call."""
from __future__ import annotations

import copy


def gpu(peers=(), lab=False):
    apps = [{"pid": 100 + i, "mib": 2000, "unit": u, "owner": "peer"} for i, u in enumerate(peers)]
    if lab:
        apps.append({"pid": 99, "mib": 4000, "unit": "haven-model-lab.service", "owner": "lab"})
    return {"name": "GPU", "mem_used_mib": 0, "mem_total_mib": 8192, "compute_apps": apps, "peer_units_busy": [],
            "strata_unit": "inactive", "free_for_lab": not peers}


class FakeSlink:
    def __init__(self, *, gpu_state=None, engine=None, connection=None, fail=None):
        self.gpu_state = gpu_state or gpu()
        self.engine = engine or {"state": "STOPPED", "ownership": "NONE"}
        self.connection = connection or {}
        self.fail = fail or {}  # labctl action -> exception to raise
        self.calls = []

    def probe(self, command, **kw):
        self.calls.append(("probe", command))
        if command == "gpu":
            return copy.deepcopy(self.gpu_state)
        if command == "status":
            return {"host": "slink", "lab": {"engine": self.engine, "connection": self.connection},
                    "gpu": copy.deepcopy(self.gpu_state), "units": ["haven-model-lab.service"],
                    "sentinel": {"counts": {}, "not_passing": []}}
        if command == "models":
            return {"loaded": None, "models": [{"id": "qwen35-4b", "downloaded": True}]}
        if command == "sentinel":
            return {"counts": {"pass:info": 3}, "not_passing": []}
        return {"unknown": True, "error": "unknown probe"}

    def labctl(self, *args, **kw):
        self.calls.append(("labctl",) + args)
        if args[0] in self.fail:
            raise self.fail[args[0]]
        if args[0] == "state":
            return {"engine": self.engine, "connection": self.connection}
        if args[0] == "load":
            self.engine = {"state": "STARTING", "ownership": "OWNED", "label": args[1]}
            return {"job_id": "job-load-1", "state": "RUNNING"}
        if args[0] == "unload":
            self.engine = {"state": "STOPPED", "ownership": "NONE"}
            return {"engine": self.engine}
        if args[0] == "disconnect":
            self.connection = {}
            return {"connection": {}}
        if args[0] == "strata":
            return {"job_id": "job-strata-1", "state": "RUNNING"}
        if args[0] == "job":
            return {"id": args[1], "state": "SUCCEEDED"}
        return {}

    def actions(self):
        return [c[1] for c in self.calls if c[0] == "labctl"]
