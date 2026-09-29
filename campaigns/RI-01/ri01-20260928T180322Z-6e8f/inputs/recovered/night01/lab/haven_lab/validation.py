from . import LABEL
from .types import Denied, canonical

def validate_output(output, context, request, budget):
    fields = {"schema_version","label","kind","claims","proposal","external_spend_usd","tool_calls"}
    if type(output) is not dict or set(output) != fields:
        raise Denied("OUTPUT_FIELDS")
    if type(output["schema_version"]) is not int or output["schema_version"] != 1 or output["label"] != LABEL:
        raise Denied("OUTPUT_METADATA")
    for key in ("external_spend_usd", "tool_calls"):
        if type(output[key]) is not int or output[key] != 0:
            raise Denied("OUTPUT_BUDGET")
    expected = "ANSWER" if request["kind"] == "PROJECT_RECALL" else "PROPOSAL"
    if output["kind"] != expected:
        raise Denied("ACTION_CLASS_DENIED")
    if expected == "ANSWER" and output["proposal"] is not None:
        raise Denied("UNEXPECTED_PROPOSAL")
    if expected == "PROPOSAL":
        p = output["proposal"]
        if type(p) is not dict or set(p) != {"kind","state","execution_enabled"}:
            raise Denied("PROPOSAL_FIELDS")
        if p["kind"] != "DRAFT_NOTE" or p["state"] != "PROPOSED" or p["execution_enabled"] is not False:
            raise Denied("PROPOSAL_NOT_INERT")
    claims = output["claims"]
    if type(claims) is not list or not 1 <= len(claims) <= budget.max_context_records:
        raise Denied("CLAIM_BUDGET")
    permitted = {r["evidence_id"]:r for r in context["records"]}
    seen = set()
    for claim in claims:
        if type(claim) is not dict or set(claim) != {"evidence_id","quote"}:
            raise Denied("CLAIM_FIELDS")
        eid = claim["evidence_id"]
        if type(eid) is not str or eid not in permitted or eid in seen:
            raise Denied("EVIDENCE_NOT_SELECTED")
        seen.add(eid)
        if type(claim["quote"]) is not str or claim["quote"] != permitted[eid]["text"]:
            raise Denied("UNGROUNDED_QUOTE")
    if len(canonical(output).encode()) > budget.max_output_bytes:
        raise Denied("OUTPUT_BUDGET")
    return output
