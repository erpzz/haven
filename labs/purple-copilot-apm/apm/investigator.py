"""A bounded read-only review via the local Haven gateway and finding-scoped MCP."""
import argparse
import asyncio
import json
import os
import re
from datetime import timedelta
from time import perf_counter
from uuid import uuid4

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .local import now, request
from .path_history import get_run
from .samples import ROOT, save

QUESTIONS = {"path": "Which directed membership chain supports this finding?",
             "quality": "How reliable is the collector coverage and freshness for this finding?",
             "triage": "Investigate the selected nested membership and assess the limits of the collection. Consult both sources."}
TOOLS = {"path_evidence": "Read the directed membership chain and stable object identifiers.",
         "collection_quality": "Read collection timestamps, coverage issues and collector provenance."}


def permitted(message):
    calls = message.get("tool_calls", [])
    if len(calls) != 1:
        raise PermissionError("Exactly one structured read is required")
    call = calls[0]
    function = call["function"]
    if (call.get("type") != "function" or not call.get("id") or function["name"] not in TOOLS
            or json.loads(function["arguments"]) != {}):
        raise PermissionError("Unauthorized tool or arguments")
    return call


def check_report(name, text, citation):
    if "[E1]" not in text:
        raise ValueError("Missing evidence citation")
    claim = text.replace("[E1]", "").lower()
    numbers = re.findall(r"\b\d+\b", claim)
    if name == "collection_quality":
        if numbers or re.search(r"\b(hops?|paths?|chains?)\b", claim):
            raise ValueError("Collection tool cannot support a topology or numeric claim")
        if citation["confidence"] == "limited" and "limited" not in claim:
            raise ValueError("Limited evidence requires a qualified hypothesis")
    elif numbers != [str(len(citation["directed_edges"]))]:
        raise ValueError("Chain summary must cite its observed hop count")


def compact_evidence(citation, audit):
    compact = dict(citation)
    if "directed_edges" in compact:
        nodes = {}
        for source, _, target in compact["directed_edges"]:
            for node in (source, target):
                nodes.setdefault(node, f"Object-{len(nodes) + 1}")
        compact["directed_edges"] = [[nodes[s], k, nodes[t]] for s, k, t in citation["directed_edges"]]
        compact["hops"] = len(citation["directed_edges"])
        audit["object_references"] = {v: k for k, v in nodes.items()}
    return compact


async def investigate(run, key, question):
    evidence, findings = get_run(run)
    if evidence["origin"] != "ce-sample" or key not in findings:
        raise ValueError("Select a recorded CE finding")
    audit = dict(run=run, finding=key, question=question, observed=now(), classification="hypothesis",
                 messages=[], responses=[], status="incomplete")
    filename = "investigation-" + str(uuid4()) + ".json"
    start = perf_counter()
    try:
        headers = {"Authorization": "Bearer " + os.environ["HAVEN_GATEWAY_KEY"], "Content-Type": "application/json"}
        model = "haven-slink"
        route = next(m for m in request(8877, "GET", "/v1/models", headers=headers)["data"] if m["id"] == model)
        if route["haven"]["provider_id"] != "managed" or route["haven"]["egress"] != "NONE":
            raise PermissionError("Expected managed local inference")
        audit["route"] = route
        messages = audit["messages"]
        messages.extend([{"role": "system", "content": "You review a single synthetic membership finding. "
                          "Select exactly one supplied read tool matching the question. Use empty arguments. "
                          "After receipt of evidence, begin with [E1] and write one short sentence interpreting the result. "
                          "Leave identifiers in the attached citation. Do not infer compromise or remediation."},
                         {"role": "user", "content": QUESTIONS[question]}])
        payload = dict(model=model, messages=messages, max_tokens=160, temperature=0,
                       tools=[{"type": "function", "function": {"name": name, "description": desc,
                               "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}
                              for name, desc in TOOLS.items()])
        def complete():
            response = request(8877, "POST", "/v1/chat/completions", json.dumps(payload), headers, timeout=240)
            audit["responses"].append(response)
            return response["choices"][0]

        combined = question == "triage"
        citations = audit["citations"] = {}
        params = StdioServerParameters(command=str(ROOT / "community/.venv/bin/python"),
                    args=["-m", "apm.finding_mcp"], env={"APM_STATE": str(ROOT), "APM_FINDING_RUN": str(run),
                    "APM_FINDING_ID": key, **({"APM_ASSETS": os.environ["APM_ASSETS"]} if "APM_ASSETS" in os.environ else {})})
        async with stdio_client(params) as (rx, tx), ClientSession(rx, tx, read_timeout_seconds=timedelta(seconds=90)) as session:
            await session.initialize()
            budget = 2 if combined else 1
            while len(citations) < budget:
                msg = complete()["message"]
                calls = msg.get("tool_calls") or []
                if not 1 <= len(calls) <= budget - len(citations):
                    raise PermissionError("Structured reads exceed remaining budget")
                names = [permitted({"tool_calls": [call]})["function"]["name"] for call in calls]
                if len(set(names)) != len(names) or set(names).intersection(citations):
                    raise PermissionError("Repeated tool request")
                if not combined and names != [{"path": "path_evidence", "quality": "collection_quality"}[question]]:
                    raise PermissionError("Read does not support the requested review")
                messages.append(msg)
                for call, name in zip(calls, names):
                    audit.setdefault("selected_tools", []).append(name)
                    tool = await session.call_tool(name, {})
                    if tool.isError:
                        raise RuntimeError("Evidence tool failed")
                    citation = json.loads(tool.content[0].text)
                    citation["reference"] = "E2" if combined and name == "collection_quality" else "E1"
                    citations[name] = citation
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": json.dumps(compact_evidence(citation, audit))})
                if len(citations) < budget:
                    messages.append({"role": "user", "content": "Retrieve the remaining evidence source before concluding."})
                    payload["tools"] = [t for t in payload["tools"] if t["function"]["name"] not in citations]
        instruction = ("State the observed hop count as a digit and what the directed memberships show."
                       if name == "path_evidence" else
                       "Discuss collection confidence only. Use the confidence label from the receipt. Omit quantities.")
        if combined:
            instruction = ("Write a short review with both citations. Start with [E1] and the hop count as a digit. "
                           "Explain why an intermediate group merits review. Then cite [E2] and describe the "
                           "limited collection confidence. Use no other numbers or object aliases.")
        else:
            instruction = "Write one short sentence beginning with [E1]. " + instruction
        messages.append({"role": "user", "content": instruction})
        del payload["tools"]
        choice = complete()
        text = choice["message"].get("content") or ""
        if choice["finish_reason"] != "stop" or choice["message"].get("tool_calls") or "[E1]" not in text:
            raise ValueError("Response lacks a completed cited conclusion")
        if combined:
            if "[E2]" not in text or "limited" not in text.lower():
                raise ValueError("Missing collection qualification")
            check_report("path_evidence", text.replace("[E2]", ""), citations["path_evidence"])
        else:
            check_report(name, text, citation)
        audit.update(status="completed", hypothesis=text)
    finally:
        audit["seconds"] = round(perf_counter() - start, 3)
        save(filename, audit)
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=int)
    parser.add_argument("finding")
    parser.add_argument("question", choices=QUESTIONS)
    args = parser.parse_args()
    report = asyncio.run(investigate(args.run, args.finding, args.question))
    print(json.dumps({k: report[k] for k in ("selected_tools", "hypothesis", "citations", "seconds")}, indent=2))
