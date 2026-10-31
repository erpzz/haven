"""Generate synthetic Maester and Prowler outputs in each tool's real output format (see haven_cyber/normalize/*).

These are NOT captured from a real tenant. Field layout follows the upstream formatter source; values are
constructed to exercise the normalizers and the verifier:

- maester-weak.json: a Maester run against fixtures/tenants/contoso-weak.json (MT.1005/1007 fail, MT.1006 passes at its
  existence criterion although a Global Administrator is excluded, one skip).
- prowler-weak.ocsf.json: Prowler M365 Entra checks against the same weak tenant.
- prowler-hardened-fp.ocsf.json: a deliberately wrong FAIL against the hardened tenant (legacy auth "not blocked"),
  as a tool would emit if it judged a disabled duplicate policy. It exists to test refutation; it does not claim
  Prowler has this bug.
"""
from __future__ import annotations

import json
from pathlib import Path

TENANT_WEAK = "c7f3c2b5-5c1d-5d0e-8f43-2b6f8f2c9a11"
TENANT_HARD = "1e4b7e83-0b9f-5e3a-a3c9-7d1e5f9b2c20"


def maester(tests, tenant):
    counts = {k: sum(t["Result"] == k for t in tests) for k in ("Failed", "Passed", "Error", "Investigate", "Skipped", "NotRun")}
    return {"Result": "Failed" if counts["Failed"] else "Passed", "FailedCount": counts["Failed"], "PassedCount": counts["Passed"],
            "ErrorCount": counts["Error"], "InvestigateCount": counts["Investigate"], "SkippedCount": counts["Skipped"],
            "NotRunCount": counts["NotRun"], "TotalCount": len(tests), "ExecutedAt": "2026-10-31T12:05:00Z",
            "TotalDuration": "00:00:41", "TenantId": tenant, "TenantName": "Contoso (synthetic)", "Account": "auditor@contoso.example",
            "CurrentVersion": "2.3.0", "LatestVersion": "2.3.0", "Tests": tests, "Blocks": []}


def mt(i, tid, title, result, sev, desc, detail, url, tags=("Maester", "Entra", "CA")):
    return {"Index": i, "Id": tid, "Title": title, "Name": f"{tid}: {title}", "HelpUrl": url, "Severity": sev, "Tag": list(tags),
            "Result": result, "ScriptBlock": "", "ScriptBlockFile": f"tests/maester/entra/Test.{tid}.ps1", "ErrorRecord": [],
            "Block": "Maester/Entra", "Duration": "00:00:01.204",
            "ResultDetail": {"TestTitle": title, "TestDescription": desc, "TestResult": detail, "TestSkipped": None,
                             "SkippedReason": None, "TestInvestigate": None, "Severity": sev, "Service": "Entra ID"}}


def ocsf(i, check, title, status, sev, detail, tenant, rem, url, compliance=None):
    sev_id = {"Informational": 1, "Low": 2, "Medium": 3, "High": 4, "Critical": 5}[sev]
    return {"message": detail, "activity_id": 1, "activity_name": "Create",
            "finding_info": {"created_time": 1793448300, "created_time_dt": "2026-10-31T12:05:00Z", "desc": title,
                             "title": title, "uid": f"prowler-m365-{check}-{tenant}-global-{i}", "name": "Conditional Access Policies",
                             "types": []},
            "time": 1793448300, "time_dt": "2026-10-31T12:05:00Z",
            "remediation": {"desc": rem, "references": [url]}, "severity_id": sev_id, "severity": sev,
            "status_id": 1, "status": "New", "status_code": status, "status_detail": detail, "risk_details": "",
            "resources": [{"labels": [], "name": "Conditional Access Policies", "uid": "conditionalAccessPolicies",
                           "group": {"name": "entra"}, "type": "NotDefined", "cloud_partition": None, "region": "global", "data": {}}],
            "metadata": {"event_code": check, "product": {"uid": "prowler", "name": "Prowler", "vendor_name": "Prowler", "version": "5.14.0"},
                         "profiles": ["cloud", "datetime"], "tenant_uid": tenant, "version": "1.5.0"},
            "type_uid": 200401, "type_name": "Detection Finding: Create", "category_uid": 2, "class_uid": 2004,
            "unmapped": {"related_url": url, "categories": [], "depends_on": [], "related_to": [], "additional_urls": [],
                         "notes": "", "compliance": compliance or {}, "scan_id": "00000000-0000-4000-8000-00000000c0de",
                         "provider_uid": tenant, "provider": "m365"},
            "cloud": {"account": {"name": "Contoso (synthetic)", "type_id": 99, "type": "Other", "uid": tenant, "labels": []},
                      "org": {"uid": tenant, "name": "Contoso (synthetic)"}, "provider": "m365", "region": "global"}}


LEARN = "https://learn.microsoft.com/entra/identity/"


def main():
    here = Path(__file__).parent
    tests = [
        mt(1, "MT.1005", "All Conditional Access policies are configured to exclude at least one emergency/break glass account or group",
           "Failed", "High", "Exclude emergency access accounts from all Conditional Access policies.",
           "Policy 'CA002 Require MFA for administrators' does not exclude an emergency access account or group.",
           "https://maester.dev/docs/tests/maester/MT.1005"),
        mt(2, "MT.1006", "At least one Conditional Access policy is configured to require MFA for admins", "Passed", "High",
           "Require MFA for admin roles for all cloud apps.",
           "Conditional Access policy 'CA002 Require MFA for administrators' requires MFA for admin roles.", "https://maester.dev/docs/tests/maester/MT.1006"),
        mt(3, "MT.1007", "At least one Conditional Access policy is configured to require MFA for all users", "Failed", "High",
           "Require MFA for all users for all cloud apps.", "No enabled policy requires MFA for all users (one is report-only).",
           "https://maester.dev/docs/tests/maester/MT.1007"),
        mt(4, "EIDSCA.AP01", "Default Authorization Settings - Enabled Self service password reset for administrators", "Skipped",
           "Medium", "", "", "https://maester.dev/docs/tests/eidsca/EIDSCA.AP01", tags=("EIDSCA", "Entra")),
    ]
    tests[3]["ResultDetail"]["SkippedReason"] = "Not connected to the required service"
    (here / "maester-weak.json").write_text(json.dumps(maester(tests, TENANT_WEAK), indent=2) + "\n")

    weak = [
        ocsf(1, "entra_legacy_authentication_blocked", "At least one Conditional Access policy blocks legacy authentication", "PASS",
             "Critical", "Conditional Access Policy 'CA001 Block legacy authentication' blocks legacy authentication.", TENANT_WEAK,
             "Block legacy authentication with Conditional Access.", LEARN + "conditional-access/policy-block-legacy-authentication",
             {"CIS-4.0_M365": ["5.2.2.3"]}),
        ocsf(2, "entra_conditional_access_policy_device_code_flow_blocked", "Conditional Access policy blocks device code flow to prevent phishing attacks",
             "FAIL", "High", "No Conditional Access Policy blocks device code flow.", TENANT_WEAK,
             "Create a policy that blocks the device code authentication flow.", LEARN + "conditional-access/policy-block-authentication-flows"),
        ocsf(3, "entra_admin_users_phishing_resistant_mfa_enabled", "At least one Conditional Access policy requires phishing-resistant MFA strength for administrator roles",
             "FAIL", "High", "No enabled Conditional Access policy requires phishing-resistant MFA for administrator roles.", TENANT_WEAK,
             "Require the Phishing-resistant MFA authentication strength for admin roles.", LEARN + "conditional-access/policy-admin-phish-resistant-mfa"),
    ]
    (here / "prowler-weak.ocsf.json").write_text(json.dumps(weak, indent=2) + "\n")
    fp = [ocsf(1, "entra_legacy_authentication_blocked", "At least one Conditional Access policy blocks legacy authentication", "FAIL",
               "Critical", "Conditional Access Policy 'CA001-old Block legacy auth (superseded)' is disabled; legacy authentication is not blocked.",
               TENANT_HARD, "Block legacy authentication with Conditional Access.", LEARN + "conditional-access/policy-block-legacy-authentication")]
    (here / "prowler-hardened-fp.ocsf.json").write_text(json.dumps(fp, indent=2) + "\n")
    print("wrote 3 tool outputs")


if __name__ == "__main__":
    main()
