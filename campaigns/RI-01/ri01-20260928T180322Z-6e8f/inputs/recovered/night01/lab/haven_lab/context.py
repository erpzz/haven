from .types import Denied, canonical

CATEGORIES = {"CURRENT_STATE", "HISTORICAL_FACT", "USER_STATEMENT", "MODEL_INTERPRETATION"}

def build_context(connection, principal, request, budget, timestamp):
    rows = connection.execute("SELECT document FROM records WHERE topic=? ORDER BY evidence_id",
                              (request["topic"],)).fetchall()
    import json
    from .store import permitted, access_revision
    selected = [json.loads(row[0]) for row in rows if permitted(connection, principal.actor,
                 json.loads(row[0])["evidence_id"], timestamp)]
    selected = selected[:budget.max_context_records]
    packet = {"mapping_version":1, "principal_id":principal.actor,
              "purpose":"assistant.context", "origin":"SIMULATED",
              "contains_real_private_data":False, "built_at":timestamp,
              "allowed_capabilities":[], "cloud_provider_allowlist":[],
              "records":selected, "access_revisions":{record["evidence_id"]:access_revision(connection, principal.actor, record["evidence_id"], timestamp) for record in selected}}
    if len(canonical(packet).encode()) > budget.max_context_bytes:
        raise Denied("CONTEXT_BUDGET_EXCEEDED")
    return packet
