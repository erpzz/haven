"""Synthetic TSZ controller tests. No network access, installs, or inference."""
from pathlib import Path
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "fleet.py"
spec = importlib.util.spec_from_file_location("tsz_fleet", MODULE)
fleet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fleet)

NOW = 1800000000


def neighbor(ip="192.0.2.15", mac="aa:bb:cc:dd:ee:ff", iface="en0"):
    return fleet.observation(ip, mac, iface, "test-neighbor-cache")


def state_with_candidate():
    state = fleet.empty_state()
    seen = neighbor()
    fleet.update_candidates(state, [seen], NOW)
    return state, seen["candidate_id"]


def approved(candidate, **overrides):
    result = {"schema": fleet.DECISION_SCHEMA, "expires_at": NOW + 3600,
              "nodes": [{"node_id": "mac-worker",
                         "candidate_id": candidate, "roles": ["inference"]}]}
    result.update(overrides)
    return result


class DiscoveryTests(unittest.TestCase):
    def test_neighbor_is_never_automatically_approved(self):
        state, candidate = state_with_candidate()
        self.assertEqual(state["candidates"][candidate]["state"], "DISCOVERED_UNVERIFIED")
        self.assertEqual(fleet.work_orders(state, NOW), [])

    def test_normalize_mac_and_candidate_id(self):
        self.assertEqual(fleet.normalize_mac("a:b:c:d:e:f"), "0a:0b:0c:0d:0e:0f")
        self.assertEqual(fleet.candidate_id("en0", "A:B:C:D:E:F"),
                         fleet.candidate_id("en0", "0a:0b:0c:0d:0e:0f"))

    def test_macos_cache_is_scoped(self):
        parsed = fleet.parse_macos(
            "? (192.0.2.15) at a:b:c:d:e:f on en0 ifscope [ethernet]\n"
            "? (192.0.2.16) at aa:aa:aa:aa:aa:aa on en7 ifscope [ethernet]\n"
            "? (192.0.2.20) at (incomplete) on en0 ifscope [ethernet]",
            {"en0"})
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["address"], "192.0.2.15")

    def test_linux_cache_skips_failed(self):
        parsed = fleet.parse_linux(json.dumps([
            {"dst": "192.0.2.2", "lladdr": "aa:bb:cc:dd:ee:ff",
             "dev": "eth0", "state": "REACHABLE"},
            {"dst": "192.0.2.3", "lladdr": "00:11:22:33:44:55",
             "dev": "eth0", "state": "FAILED"},
            {"dst": "192.0.2.4", "lladdr": "00:11:22:33:44:55",
             "dev": "eth1", "state": "STALE"},
        ]), {"eth0"})
        self.assertEqual(len(parsed), 1)

    def test_unobserved_devices_do_not_appear(self):
        self.assertEqual(fleet.parse_macos("", {"en0"}), [])
        self.assertEqual(fleet.work_orders(fleet.empty_state(), NOW), [])

    def test_repeat_discovery_updates_address_without_duplication(self):
        state, cid = state_with_candidate()
        count = fleet.update_candidates(
            state, [neighbor(ip="192.0.2.17")], NOW + 1)
        self.assertEqual(count, 0)
        self.assertEqual(len(state["candidates"]), 1)
        self.assertEqual(len(state["candidates"][cid]["addresses"]), 2)

    def test_cache_read_uses_fixed_no_probe_command(self):
        from subprocess import CompletedProcess
        output = CompletedProcess(args=["arp", "-an"], returncode=0,
                                  stdout="? (192.0.2.15) at aa:bb:cc:dd:ee:ff on en0", stderr="")
        with patch.object(fleet.platform, "system", return_value="Darwin"), \
             patch.object(fleet.subprocess, "run", return_value=output) as run:
            fleet.observe({"en0"})
        self.assertEqual(run.call_args.args[0], ["arp", "-an"])


class ApprovalTests(unittest.TestCase):
    def test_external_approved_snapshot_enables_inert_order(self):
        state, cid = state_with_candidate()
        report = fleet.reconcile_approved(state, approved(cid), NOW)
        self.assertEqual(report["approved_nodes"], 1)
        orders = fleet.work_orders(state, NOW)
        self.assertEqual(orders[0]["action"], "PREPARE_USERSPACE_WORKER")
        self.assertNotIn("address", orders[0])
        self.assertNotIn("command", orders[0])

    def test_replaced_snapshot_implicitly_revokes_missing_nodes(self):
        state, cid = state_with_candidate()
        fleet.reconcile_approved(state, approved(cid), NOW)
        fleet.reconcile_approved(state, approved(cid, nodes=[]), NOW)
        self.assertEqual(fleet.work_orders(state, NOW), [])

    def test_expiry_produces_no_orders(self):
        state, cid = state_with_candidate()
        fleet.reconcile_approved(state, approved(cid), NOW)
        self.assertEqual(fleet.work_orders(state, NOW + 3600), [])

    def test_unknown_device_reference_is_rejected(self):
        state, _ = state_with_candidate()
        with self.assertRaises(fleet.FleetError):
            fleet.reconcile_approved(state, approved("neighbor-other"), NOW)
        self.assertEqual(state["nodes"], {})

    def test_role_abuse_is_rejected(self):
        state, cid = state_with_candidate()
        for roles in (["root"], ["inference", "inference"], [], ["inference", 42]):
            with self.subTest(roles=roles), self.assertRaises(fleet.FleetError):
                fleet.reconcile_approved(state, approved(cid, nodes=[
                    {"node_id": "mac-worker", "candidate_id": cid, "roles": roles},
                ]), NOW)

    def test_expired_or_far_future_decisions_rejected(self):
        state, cid = state_with_candidate()
        for expires in (NOW, NOW - 1, NOW + 86401, "tomorrow"):
            with self.subTest(expires=expires), self.assertRaises(fleet.FleetError):
                fleet.reconcile_approved(state, approved(cid, expires_at=expires), NOW)

    def test_duplicate_node_or_candidate_rejected(self):
        state, cid = state_with_candidate()
        for duplicate in (
            {"node_id": "mac-worker", "candidate_id": cid, "roles": ["inventory"]},
            {"node_id": "another", "candidate_id": cid, "roles": ["inventory"]},
        ):
            with self.subTest(duplicate=duplicate), self.assertRaises(fleet.FleetError):
                fleet.reconcile_approved(state, approved(cid, nodes=[
                    {"node_id": "mac-worker", "candidate_id": cid, "roles": ["inference"]},
                    duplicate,
                ]), NOW)

    def test_node_id_cannot_be_rebound(self):
        state, cid = state_with_candidate()
        fleet.reconcile_approved(state, approved(cid), NOW)
        cid2 = neighbor(ip="192.0.2.50", mac="aa:bb:cc:dd:ee:11")["candidate_id"]
        fleet.update_candidates(state, [neighbor(ip="192.0.2.50", mac="aa:bb:cc:dd:ee:11")], NOW)
        with self.assertRaises(fleet.FleetError):
            fleet.reconcile_approved(state, approved(cid2), NOW)
        self.assertEqual(state["nodes"]["mac-worker"]["candidate_id"], cid)

    def test_external_export_is_owner_private(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "approved.json"
            path.write_text(json.dumps(approved("neighbor-test")))
            path.chmod(0o644)
            with self.assertRaises(fleet.FleetError):
                fleet.load_approved_file(path)
            path.chmod(0o600)
            self.assertEqual(fleet.load_approved_file(path)["schema"], fleet.DECISION_SCHEMA)

    def test_private_inventory_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = fleet.private_dir(Path(folder) / "tsz")
            state, cid = state_with_candidate()
            fleet.write_state(directory, state)
            reloaded = fleet.read_state(directory)
            self.assertIn(cid, reloaded["candidates"])
            self.assertEqual((directory / "inventory.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
