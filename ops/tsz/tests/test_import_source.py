"""Offline owner-network-inventory input checks."""
from pathlib import Path
import json
import tempfile
import unittest

from ops.tsz import import_source as m

NOW = 1_800_000_000


def sample(**kw):
    record = {"schema": m.SCHEMA, "observed_at": NOW-5, "source": "home-router",
              "devices": [{"address": "192.0.2.80", "mac": "aa:bb:cc:dd:ee:ff", "interface": "home-lan"}]}
    record.update(kw)
    return record


class ImportTests(unittest.TestCase):
    def test_parse_owner_inventory_as_unverified_candidate(self):
        nodes = m.parse_network_inventory(sample(), {"home-lan"}, NOW)
        self.assertEqual(len(nodes), 1)
        self.assertTrue(nodes[0]["candidate_id"].startswith("neighbor-"))
        self.assertNotIn("approved", nodes[0])
        self.assertEqual(nodes[0]["origin"], "owner-export:home-router")

    def test_wrong_interface_excluded(self):
        self.assertEqual(m.parse_network_inventory(sample(), {"guest-lan"}, NOW), [])

    def test_stale_or_future_data_rejected(self):
        for observed in (NOW-3601, NOW+10, "unknown"):
            with self.subTest(observed=observed), self.assertRaises(m.InventoryError):
                m.parse_network_inventory(sample(observed_at=observed), {"home-lan"}, NOW)

    def test_bad_macs_and_ips_rejected(self):
        for mac, ip in (("garbage", "192.0.2.50"), ("aa:bb:cc:dd:ee:ff", "not-a-host")):
            with self.subTest(mac=mac,ip=ip), self.assertRaises(m.InventoryError):
                m.parse_network_inventory(sample(devices=[{
                    "address": ip,"mac":mac,"interface":"home-lan"}]), {"home-lan"}, NOW)

    def test_malformed_interface_is_rejected(self):
        doc = sample(devices=[{"address": "192.0.2.5", "mac": "aa:bb:cc:dd:ee:ff", "interface": []}])
        with self.assertRaises(m.InventoryError):
            m.parse_network_inventory(doc, {"home-lan"}, NOW)

    def test_mixed_interfaces_only_selected(self):
        doc = sample(devices=sample()["devices"] + [{"address":"198.51.100.1",
            "mac":"00:11:22:33:44:55","interface":"guest-lan"}])
        self.assertEqual(len(m.parse_network_inventory(doc,{"home-lan"}, NOW)),1)

    def test_owner_file_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"inventory.json"
            p.write_text(json.dumps(sample()))
            p.chmod(0o644)
            with self.assertRaises(m.InventoryError):m.read_owner_inventory(p)
            p.chmod(0o600)
            self.assertEqual(m.read_owner_inventory(p)["source"],"home-router")

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"inventory.json";p.write_text(json.dumps(sample()));p.chmod(0o600)
            symlink=Path(folder)/"inventory-symlink.json";symlink.symlink_to(p)
            with self.assertRaises(m.InventoryError):m.read_owner_inventory(symlink)

    def test_oversized_device_list_rejected(self):
        doc=sample(devices=sample()["devices"]*(m.MAX_DEVICES+1))
        with self.assertRaises(m.InventoryError):m.parse_network_inventory(doc,{"home-lan"},NOW)


if __name__ == "__main__":unittest.main()
