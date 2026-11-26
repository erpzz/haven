"""A fixed, tool-free reasoning interface over a versioned observation."""
import argparse
import hashlib
import json
import os
from contextlib import closing

from .local import now, request
from .samples import ROOT
from .store import conclusion_writer, database

SKILLS = {
    "ad": ("bloodhound-ad-analysis", "For each result, classify confirmed graph facts vs inferred risk and include remediation-oriented notes."),
    "entra": ("azurehound-analysis", "Explain each path segment by platform and collector source."),
}
SKILL_REV = "f5dbbb23059c1186c695c832eedf88c8f3a0fcb4"


def analyze(run, gateway=True):
    with closing(database(True)) as db:
        row = db.execute("SELECT evidence FROM runs WHERE id=?", (run,)).fetchone()
    if row is None:
        raise ValueError("Unknown run")
    ev = json.loads(row[0])
    if ev.get("unavailable"):
        raise ValueError("Observation unavailable")
    skill, guidance = SKILLS[ev["scope"]]
    document = (ROOT / (skill + ".md")).read_bytes()
    if guidance not in document.decode():
        raise ValueError("Installed skill does not contain expected guidance")
    facts = {key: ev[key] for key in ("scope", "query", "source", "observed", "collected", "issues")}
    facts.update(snapshot=run, observed_memberships=len(ev["edges"]), example=ev["edges"][:1])
    headers = {"Content-Type": "application/json"}
    if gateway:
        port, model = 8877, "haven-slink"
        headers["Authorization"] = "Bearer " + os.environ["HAVEN_GATEWAY_KEY"]
        listing = request(port, "GET", "/v1/models", headers=headers)["data"]
        route = next(m for m in listing if m["id"] == model)
        if route["haven"]["provider_id"] != "managed" or route["haven"]["egress"] != "NONE":
            raise PermissionError("Requires the local managed Haven route")
    else:
        port, model = 8135, "purple-qwen3-8b"
        route = next(m for m in request(port, "GET", "/v1/models")["data"] if m["id"] == model)
    prompt = [
        {"role": "system", "content": "Review the supplied synthetic evidence only. " + guidance +
         " Return exactly one sentence, at most 25 words. Include the observed membership count. "
         "Omit object IDs and archive record totals from the sentence. "
         "Do not infer malicious behavior, remediation or additional access. /no_think"},
        {"role": "user", "content": json.dumps(facts)}]
    payload = {"model": model, "messages": prompt, "temperature": 0, "max_tokens": 224}
    if not gateway:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    result = request(port, "POST", "/v1/chat/completions", json.dumps(payload), headers, timeout=240)
    answer = result["choices"][0]["message"]["content"]
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Model returned no conclusion")
    provenance = dict(route=route, skill=skill, skill_revision=SKILL_REV, skill_sha256=hashlib.sha256(document).hexdigest())
    with closing(conclusion_writer()) as db, db:
        db.execute("INSERT INTO conclusions(run,created,model,prompt,response,classification) VALUES(?,?,?,?,?,'hypothesis')",
                   (run, now(), json.dumps(provenance), json.dumps(payload), json.dumps(result)))
    if result["choices"][0].get("finish_reason") != "stop":
        raise ValueError("Incomplete model response recorded for review")
    return answer


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=int)
    p.add_argument("--sample-runner", action="store_true")
    args = p.parse_args()
    print(analyze(args.run, not args.sample_runner))
