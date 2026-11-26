import json
import unittest

from haven_cyber import FIXTURES, ROOT
from haven_cyber.tools.entra_ca import assess, assess_dict


def statuses(bundle):
    return {f.source_check_id: f.status for f in bundle.findings}


class EntraCATests(unittest.TestCase):
    def test_weak_tenant(self):
        st = statuses(assess(FIXTURES / "tenants" / "contoso-weak.json", ROOT))
        self.assertEqual(st["HCA-001"], "fail")  # non-emergency group excluded
        self.assertEqual(st["HCA-002"], "fail")  # Global Administrator excluded
        self.assertEqual(st["HCA-003"], "fail")  # report-only
        self.assertEqual(st["HCA-005"], "fail")  # emergency accounts in scope of admin MFA policy
        self.assertEqual(st["HCA-006"], "manual")
        self.assertEqual(st["HCA-007"], "fail")
        self.assertEqual(st["HCA-008"], "pass")
        self.assertEqual(st["HCA-010"], "fail")  # deleted user reference

    def test_hardened_tenant_has_no_failures(self):
        b = assess(FIXTURES / "tenants" / "contoso-hardened.json", ROOT)
        self.assertEqual([f.source_check_id for f in b.findings if f.status == "fail"], [])

    def test_every_observation_pointer_resolves(self):
        from haven_cyber.evidence import json_pointer_get
        for name in ("contoso-weak", "contoso-hardened"):
            path = FIXTURES / "tenants" / f"{name}.json"
            snap = json.loads(path.read_text())
            b = assess(path, ROOT)
            for o in b.observations:
                self.assertEqual(json_pointer_get(snap, o.pointer), o.value, (name, o.pointer))

    def test_or_with_compliant_device_is_not_mfa(self):
        snap = json.loads((FIXTURES / "tenants" / "contoso-hardened.json").read_text())
        p = snap["conditionalAccessPolicies"][1]
        p["grantControls"]["builtInControls"] = ["mfa", "compliantDevice"]
        p["grantControls"]["operator"] = "OR"
        snap["conditionalAccessPolicies"][2]["state"] = "disabled"  # all-users MFA also covers admins
        snap["conditionalAccessPolicies"][3]["state"] = "disabled"  # and so does the phishing-resistant strength policy
        self.assertEqual(statuses(assess_dict(snap))["HCA-002"], "fail")

    def test_guest_exclusion_respected(self):
        snap = json.loads((FIXTURES / "tenants" / "contoso-hardened.json").read_text())
        from haven_cyber.tools.entra_ca import Snapshot, in_scope
        p = snap["conditionalAccessPolicies"][2]
        p["conditions"]["users"]["excludeUsers"] = ["GuestsOrExternalUsers"]
        s = Snapshot.from_dict(snap)
        guest = next(u["id"] for u in snap["users"] if u["userType"] == "Guest")
        self.assertFalse(in_scope(p, guest, s))


if __name__ == "__main__":
    unittest.main()
