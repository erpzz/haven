import base64
import hmac
import io
import json
import zipfile

from .local import now, request
from .policy import authorize
from .samples import FILES, checked, read


def _signed(method, path, body=None):
    token = read("reader.json")
    date = now()
    sig = token["key"].encode()
    for data in [(method + path).encode(), date[:13].encode(), body or b""]:
        sig = hmac.digest(sig, data, "sha256")
    return request(8080, method, path, body, {
        "RequestDate": date, "Signature": base64.b64encode(sig).decode(),
        "Authorization": "bhesignature " + token["id"], "Content-Type": "application/json"})


def verify_reader():
    identity = _signed("GET", "/api/v2/self")["data"]
    if identity["principal_name"] != "purple-sample-reader" or [r["name"] for r in identity["roles"]] != ["Read-Only"]:
        raise PermissionError("Expected the dedicated Read-Only identity")


def expected(review):
    with zipfile.ZipFile(io.BytesIO(checked(review.source))) as archive:
        for member in archive.namelist():
            if review.label == "Group" and not member.endswith("_groups.json"):
                continue
            content = json.loads(archive.read(member))
            rows = content["data"]
            counts = [content["meta"]["count"], len(rows)]
            for row in rows:
                if review.label == "Group" and row["ObjectIdentifier"] == review.target:
                    return ([m["ObjectIdentifier"] for m in row["Members"]], member,
                            member[:14], counts)
                if row.get("kind") == "AZGroupMember" and row["data"]["groupId"] == review.target:
                    return ([m["member"]["id"] for m in row["data"]["members"]], member, None, counts)
    raise ValueError("Source inventory unavailable")


def snapshot(name):
    review = authorize(name)
    verify_reader()
    members, source_file, collector_time, counts = expected(review)
    ingest = read("ingest.json")
    status = ingest["status"]
    result = _signed("POST", "/api/v2/graphs/cypher", json.dumps({
        "query": review.query, "include_properties": False}).encode())["data"]
    edges = set()
    for edge in result["edges"]:
        source = result["nodes"][str(edge["source"])]["objectId"]
        target = result["nodes"][str(edge["target"])]["objectId"]
        if target != review.target or edge["kind"] != review.kind or not source:
            raise ValueError("Graph result outside approved scope")
        edges.add((source, review.kind, target))
    issues = []
    if counts[0] != counts[1]:
        issues.append(f"Collector declared {counts[0]} records, archive contains {counts[1]}")
    if (ingest["archives"] != FILES or status["status"] != 2 or status["total_files"] != 32
            or status["failed_files"] or status["partial_failed_files"]):
        issues.append("Incomplete sample upload")
    if set(members) != {edge[0] for edge in edges}:
        issues.append("Graph and archive membership differ")
    return dict(scope=name, query=review.query, source=FILES[review.source], collected=collector_time,
                archive_member=source_file, observed=now(), ingest=status["end_time"], job=status["id"],
                expected_members=members, graph=result, issues=issues, edges=sorted(edges))
