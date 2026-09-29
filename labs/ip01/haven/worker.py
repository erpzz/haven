"""Fixed, tool-free worker. One bounded request, one attributed candidate.

Only supervisor-authored IPC is read. It has no store handle or authority API.
The worker uses the base interpreter; all dependencies here are stdlib.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

# -I prevents ambient PYTHONPATH/user site injection. This is the fixed sibling
# source directory, not a path supplied by notes, requests or model output.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from supervisor import (read_frame, write_frame, canonical, digest, context_digest, MAX_METADATA,
                            MAX_OUTPUT, boot_id, process_birth, K)
else:
    from .supervisor import (read_frame, write_frame, canonical, digest, context_digest, MAX_METADATA,
                             MAX_OUTPUT, boot_id, process_birth, K)


def execute(request):
    context, job = request["context"], request["job"]
    if request["context_digest"] != context_digest(context):
        raise ValueError("context digest mismatch")
    identity = request["identity"]
    if (identity["pid"] != os.getpid() or identity["process_birth"] != process_birth(K.GetCurrentProcess())
            or identity["boot_id"] != boot_id()):
        raise ValueError("worker process identity mismatch")
    sources = context.get("sources", [])
    if len(sources) > 32:
        raise ValueError("source bound")
    # The full context is an influencing dependency regardless of citations.
    metadata = {k: v for k, v in context.items() if k != "image_base64"}
    if len(canonical(metadata)) > MAX_METADATA:
        raise ValueError("context metadata bound")
    refs = [s["id"] for s in sources]
    if job["route"] == "model":
        if __package__ in (None, ""):
            from model_adapter import generate
        else:
            from .model_adapter import generate
        answer, usage = generate(context, request["backend"], request["model_identity"])
        payload = {"text": answer, "route": "model", "source_refs": refs,
                   "limitations": "Local model proposal on supplied synthetic evidence; APP checks current authority."}
    elif job["route"] == "deterministic":
        text = "\n\n".join(f"{s.get('title', 'Source')}: {s.get('text', '')}" for s in sources)
        payload = {"text": text or "No eligible source supports an answer.",
                   "route": "deterministic", "source_refs": refs,
                   "limitations": "Deterministic source excerpt; no model inference."}
        usage = {"model_calls": 0, "certainty": "OBSERVED"}
    else:
        raise ValueError("unsupported route")
    if len(canonical(payload)) > MAX_OUTPUT:
        raise ValueError("output bound")
    return {"identity": identity, "request_digest": job["request_digest"],
            "context_digest": request["context_digest"], "payload": payload,
            "output_digest": digest(payload), "source_refs": refs,
            "model_identity": request["model_identity"], "outcome": "COMPLETED",
            "usage": usage, "certainty": "OBSERVED"}


if __name__ == "__main__":
    try:
        write_frame(sys.stdout.buffer, execute(read_frame(sys.stdin.buffer)), MAX_OUTPUT + MAX_METADATA)
    except Exception:
        # Do not echo secrets, request bodies or exceptions into logs/IPC.
        raise SystemExit(2)
