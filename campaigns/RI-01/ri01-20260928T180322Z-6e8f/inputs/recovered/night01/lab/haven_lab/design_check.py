"""Separate deterministic fixture checker; NOT independent physical evidence.

The writer also authored this checker. Read-only peer review is reported separately.
These arithmetic limits are invented synthetic criteria, not a safety/structural test.
"""
from .types import digest

CHECK_VERSION = "synthetic-holdout-check-1"

def evaluate(design):
    d=design["dimensions"]
    checks={"slot_fits":d["base_mm"]>=d["slot_mm"]+4,
            "synthetic_aspect_ratio":d["height_mm"]<=1.5*d["base_mm"],
            "synthetic_depth":d["depth_mm"]>=12}
    return {"checker":CHECK_VERSION,"design_sha256":digest(design),
            "status":"PASS" if all(checks.values()) else "REJECTED",
            "checks":checks,"physical_measurement":False,
            "qualification_state":"UNQUALIFIED"}
