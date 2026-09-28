"""Fixed synthetic objective v1, not physics or a measurement model.

Lower is better. Pre-registered before candidate execution and not fitted to results.
"""
METRIC_VERSION = "synthetic-fit-score-1"
FORMULA = "abs(height_mm-40)+2*abs(slot_mm-20)+(base_mm*depth_mm*thickness_mm)/10000"

def score(dimensions):
    d=dimensions
    return round(abs(d["height_mm"]-40)+2*abs(d["slot_mm"]-20)
                 +(d["base_mm"]*d["depth_mm"]*d["thickness_mm"])/10000,6)
