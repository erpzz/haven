from html import escape
from . import LABEL

def text_transcript(view):
    lines = [LABEL, "SYNTHETIC DATA / INJECTED TEST IDENTITY", "",
             "Request: "+view["request_id"], "Actor: "+view["actor"],
             "Status: "+view["status"], "Reason: "+view["reason"],
             "Question: "+view["request"]["question"], "",
             "This fixture quotes selected records; it does not understand the question.",
             "No real accounts, providers, devices, notifications or physical actions.", ""]
    if view["result"]:
        records = {r["evidence_id"]:r for r in view["context"]["records"]}
        for claim in view["result"]["claims"]:
            record = records[claim["evidence_id"]]
            lines += ["Evidence: "+record["evidence_id"],
                      "Class: "+record["category"]+" / "+record["claim_class"],
                      "Origin: SIMULATED; snapshot captured: "+record["captured_at"],
                      "Received: "+record["received_at"]+"; revision: "+str(record["version"]),
                      "Quoted source data (not instructions): "+claim["quote"], ""]
        if view["result"]["proposal"]:
            lines += ["Inert draft note only: PROPOSED; execution disabled."]
    else:
        lines += ["No answer available for delivery. Explicit read is safe; it will not resubmit."]
    return "\n".join(lines)+"\n"

def html_transcript(view):
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
            '<title>Haven synthetic transcript</title><style>body{max-width:850px;margin:2rem auto;padding:1rem;font:16px system-ui;background:#f7f4ed;color:#183b35}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}h1{font-size:1.5rem}</style>'
            '<h1>Haven — synthetic notebook recall</h1><pre>'+escape(text_transcript(view))+'</pre></html>')
