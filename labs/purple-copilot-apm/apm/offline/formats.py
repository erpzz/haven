"""Strict, offline projections of pinned exporter formats. Raw bytes stay in the vault."""

import json
from datetime import datetime, timedelta
from uuid import UUID

EO = "5bdaebd1f8c4d8a037025b312e9a05405649e378"
M2 = "7413c42d3fcc724dfea94d2726e690ddd364d914"
M3 = "2d659e85c1ae57162412c499283ae4b431392379"
KINDS = {
    "AZUser": "user",
    "AZGroup": "group",
    "AZServicePrincipal": "servicePrincipal",
    "AZDevice": "device",
}
SYSTEMS = {
    "EntraID": "EntraRole",
    "Defender": "DefenderRole",
    "DeviceManagement": "IntuneRole",
    "IdentityGovernance": "IdGovRole",
    "ResourceApps": "AppRole",
}
RESULTS = {"Passed", "Failed", "Skipped", "NotRun", "Investigate", "Error"}
LIMIT = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    require(isinstance(value, str) and value.strip(), "Missing string identifier")
    return value


def guid(value):
    return str(UUID(text(value)))


def utc(value):
    stamp = datetime.fromisoformat(text(value))
    require(stamp.utcoffset() == timedelta(0), "UTC timestamp required")
    return stamp


def array(value):
    require(isinstance(value, list), "Expected an array")
    return value


def unique(values):
    require(len(set(values)) == len(values), "Duplicate identifier")


def parse(raw):
    def pairs(items):
        unique([k for k, _ in items])
        return dict(items)

    require(len(raw) <= LIMIT, "Input exceeds byte limit")
    return json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=pairs,
        parse_constant=lambda _: require(False, "Nonfinite JSON number"),
    )


def row(category, kind, native_id, data):
    return {"category": category, "kind": kind, "native_id": native_id, "data": data}


def mode(value, subtype):
    require(
        value in (None, "", "Eligible", "Active", "Permanent"),
        "Unknown PIM assignment type",
    )
    nested = "eligible" in str(subtype or "").lower()
    require(
        not (nested and value in ("Active", "Permanent")),
        "Conflicting eligibility evidence",
    )
    if nested or value == "Eligible":
        return "eligible"
    return value.lower() if value else "unknown"


def classifications(value):
    rows = array(value)
    require(all(isinstance(c, dict) for c in rows), "Malformed EAM classifications")
    return rows


def eam(doc, manifest):
    system = manifest.get("rbac_system")
    require(system in SYSTEMS, "Unknown EAM RBAC system")
    seen = []
    rows = []
    principals = [doc] if isinstance(doc, dict) else array(doc)
    for p in principals:
        if p.get("TenantId"):
            require(
                guid(p["TenantId"]) == guid(manifest["tenant"]), "Foreign principal"
            )
        kind = text(p["ObjectType"]).lower()
        kinds = {v.lower(): v for v in KINDS.values()}
        require(kind in kinds, "Unsupported principal kind")
        pid = guid(p["ObjectId"])
        seen.append(pid)
        rows.append(
            row(
                "principal",
                kinds[kind],
                pid,
                {
                    "rbac_system": system,
                    "classification": classifications(p["Classification"]),
                    "tier": p.get("ObjectAdminTierLevel"),
                },
            )
        )
        ids = []
        for a in array(p["RoleAssignments"]):
            require(
                a.get("RoleSystem", system) == system,
                "Assignment RoleSystem conflicts with receipt",
            )
            aid = text(a.get("RoleAssignmentInstanceId") or a.get("RoleAssignmentId"))
            ids.append(aid)
            rows.append(
                row(
                    "privilege",
                    kinds[kind],
                    pid,
                    dict(
                        assignment_id=text(a["RoleAssignmentId"]),
                        assignment_instance_id=a.get("RoleAssignmentInstanceId"),
                        rbac_system=system,
                        assignment_mode=mode(
                            a.get("PIMAssignmentType"), a.get("RoleAssignmentSubType")
                        ),
                        scope=a.get("RoleAssignmentScopeId"),
                        role_id=text(a["RoleDefinitionId"]),
                        classification=classifications(a["Classification"]),
                        assignment_type=a.get("RoleAssignmentType"),
                        subtype=a.get("RoleAssignmentSubType"),
                        transitive_by=a.get("TransitiveByObjectId"),
                    ),
                )
            )
        unique(ids)
    unique(seen)
    return rows


def opengraph(doc, manifest):
    require(
        set(doc) == {"graph"} and set(doc["graph"]) == {"nodes", "edges"},
        "Unsupported OpenGraph envelope",
    )
    nodes = {}
    declared_kinds = {}
    rows = []
    for n in array(doc["graph"]["nodes"]):
        node = text(n["id"]).upper()
        require(node not in nodes, "Duplicate node")
        declared = set(array(n["kinds"]))
        if declared.intersection(
            {"AZRole", "EO_DefenderRole", "EO_IdGovRole", "EO_IntuneRole", "EO_AppRole"}
        ):
            require(
                "@" in node
                and guid(node.rsplit("@", 1)[1]) == guid(manifest["tenant"]),
                "Foreign or unscoped role",
            )
        declared_kinds[node] = declared
        kinds = declared & KINDS.keys()
        require(len(kinds) <= 1, "Ambiguous native kind")
        kind = KINDS[next(iter(kinds))] if kinds else None
        nodes[node] = kind
        if not kind:
            rows.append(row("source_node", None, node, {"kinds": sorted(declared)}))
        if kind:
            rows.append(
                row(
                    "principal",
                    kind,
                    guid(node),
                    {
                        k: v
                        for k, v in n["properties"].items()
                        if k.startswith(("classification_", "entraopsadmin"))
                    },
                )
            )
    seen = []
    for edge in array(doc["graph"]["edges"]):
        rel = text(edge["kind"])
        for end in ("start", "end"):
            require(edge[end].get("match_by") == "id", "Unsupported endpoint selector")
        src, dst = (text(edge[end]["value"]).upper() for end in ("start", "end"))
        seen.append((src, rel, dst))
        if rel.startswith(("EO_EligibleFor", "EO_Has")) and "@" in dst:
            require(
                guid(dst.rsplit("@", 1)[1]) == guid(manifest["tenant"]),
                "Foreign role endpoint",
            )
        p = edge.get("properties", {})
        system = p.get("rbacsystem")
        suffix = SYSTEMS.get(system)
        supported = suffix and rel in (
            "EO_EligibleFor" + suffix,
            "EO_Has" + suffix,
            "EO_Has" + suffix + "Assignment",
        )
        known = {
            prefix + s + tail
            for s in SYSTEMS.values()
            for prefix, tail in [
                ("EO_EligibleFor", ""),
                ("EO_Has", ""),
                ("EO_Has", "Assignment"),
            ]
        }
        require(rel not in known or supported, "Relationship and RBAC system disagree")
        info = dict(edge_kind=rel, target=dst, traversable=False, rbac_system=system)
        if supported:
            if rel.endswith("Assignment"):
                target_kind = "EO_" + suffix + "Assignment"
            else:
                target_kind = "AZRole" if system == "EntraID" else "EO_" + suffix
            if dst in declared_kinds:
                require(
                    target_kind in declared_kinds[dst], "Unexpected role endpoint kind"
                )
            else:
                info["unresolved_target"] = True
            assignment = mode(
                p.get("pimassignmenttype"), p.get("roleassignmentsubtype")
            )
            if rel.startswith("EO_EligibleFor"):
                require(
                    assignment in ("unknown", "eligible"),
                    "Eligible edge contradicts properties",
                )
                assignment = "eligible"
            if rel == "EO_Has" + suffix:
                require(
                    assignment != "eligible", "Active role edge contradicts eligibility"
                )
            info.update(
                assignment_mode=assignment,
                scope=p.get("roleassignmentscopeid"),
                assignment_type=p.get("roleassignmenttype"),
                assignment_id=p.get("roleassignmentid"),
                assignment_instance_id=p.get("roleassignmentinstanceid"),
                subtype=p.get("roleassignmentsubtype"),
                classification={
                    k: p[k]
                    for k in (
                        "admintierlevel",
                        "admintierlevelname",
                        "service",
                        "taggedby",
                        "taggedbyrolesystem",
                    )
                    if k in p
                },
            )
        rows.append(
            row(
                "privilege" if supported and dst in nodes else "overlay_edge",
                nodes.get(src),
                src,
                info,
            )
        )
    unique(seen)
    return rows


def variant(doc):
    require(
        isinstance(doc, dict) and isinstance(doc.get("Tests"), list), "Invalid report"
    )
    require("Partitions" not in doc, "Merged Maester reports are unsupported")
    text(doc["Result"])
    utc(doc["ExecutedAt"])
    if "SchemaVersion" in doc:
        require(
            doc["SchemaVersion"] == "2.1"
            and text(doc["CatalogVersion"]).startswith("3."),
            "Unsupported preview schema",
        )
        return "maester_3_preview"
    require("CatalogVersion" not in doc, "Ambiguous report version")
    return "maester_2x"


def object_reference(obj, sources):
    kind = {
        "User": "user",
        "Group": "group",
        "ServicePrincipal": "servicePrincipal",
        "Device": "device",
    }.get(obj["Type"])
    native = None
    if (
        kind
        and obj["System"] == "EntraID"
        and obj["AnchorKind"] == "Instance"
        and "GraphObjects" in sources
        and obj.get("Id")
    ):
        native = guid(obj["Id"])
    return kind, native


def maester(doc, manifest):
    schema = variant(doc)
    require(schema == manifest["format"], "Report and manifest versions disagree")
    require(guid(doc["TenantId"]) == guid(manifest["tenant"]), "Tenant mismatch")
    require(
        utc(doc["ExecutedAt"]) == utc(manifest["collected_utc"]),
        "Execution timestamp mismatch",
    )
    version = doc["CurrentVersion"]
    if isinstance(version, dict):
        version = ".".join(str(version[k]) for k in ("Major", "Minor", "Build"))
    require(
        text(version)
        in (("2.3.0",) if schema == "maester_2x" else ("3.0.0", "3.0.0-rc83")),
        "Unsupported module version",
    )
    if schema == "maester_3_preview":
        require(
            doc["CatalogVersion"] in ("3.0.0", "3.0.0-rc83"),
            "Unsupported preview catalog",
        )
    if "TenantContext" in doc and doc["TenantContext"].get("TenantId"):
        require(
            guid(doc["TenantContext"]["TenantId"]) == guid(manifest["tenant"]),
            "Mixed tenant context",
        )
    tests = {}
    for t in doc["Tests"]:
        tid = text(t["Id"])
        require(
            tid not in tests and t["Result"] in RESULTS,
            "Duplicate test or unknown outcome",
        )
        detail = t.get("ResultDetail") or {}
        reason = t.get("ReasonCode") or detail.get("TestSkipped")
        applicability = "unknown"
        if reason in ("NotApplicable", "TenantTypeMismatch"):
            applicability = "not_applicable"
        elif t["Result"] in ("Passed", "Failed", "Investigate"):
            applicability = "executed"
        tests[tid] = dict(
            test_id=tid,
            result=t["Result"],
            severity=t.get("Severity"),
            reason=reason,
            stable_skip=detail.get("TestSkipped"),
            services=t.get("Service"),
            applicability=applicability,
            product=t.get("Product"),
            block=t.get("Block"),
            scope="tenant" if t.get("ResourceType") == "Tenant" else "unspecified",
            executed_at=doc["ExecutedAt"],
            catalog=doc.get("CatalogVersion"),
        )
    require(doc.get("TotalCount", len(tests)) == len(tests), "Report count mismatch")
    rows = [row("check", None, None, t) for t in tests.values()]
    # The aggregate merges sources across tests. Attribute mixed-source entries
    # to a test only when its own structured reference confirms the native ID.
    related = {}
    for t in doc["Tests"]:
        detail = t.get("ResultDetail") or {}
        for obj in array(detail.get("RelatedObjects") or []):
            kind, native = object_reference(obj, [obj["Source"]])
            if native is not None:
                key = (t["Id"], kind, native)
                require(key not in related, "Duplicate test-local object reference")
                related[key] = row(
                    "affected",
                    kind,
                    native,
                    dict(tests[t["Id"]], reference="RelatedObjects"),
                )

    derived = []
    native_refs = []
    for obj in array(doc.get("AffectedObjects", [])):
        uid = text(obj["UniqueId"])
        derived.append(uid)
        sources = array(obj["Sources"])
        kind, native = object_reference(obj, sources)
        if native:
            native_refs.append((kind, native))
        tids = array(obj["Tests"])
        unique(tids)
        for tid in tids:
            require(tid in tests, "Dangling affected-object test reference")
            key = (tid, kind, native)
            supported_ref = (
                native if set(sources) == {"GraphObjects"} or key in related else None
            )
            related.pop(key, None)
            rows.append(
                row(
                    "affected",
                    kind,
                    supported_ref,
                    dict(tests[tid], unique_id=uid, reference="AffectedObjects"),
                )
            )
    rows.extend(related.values())
    unique(derived)
    unique(native_refs)
    return rows


PARSERS = {
    "entraops_eam": ("entraops", EO, eam),
    "entraops_opengraph": ("entraops", EO, opengraph),
    "maester_2x": ("maester", M2, maester),
    "maester_3_preview": ("maester", M3, maester),
}
