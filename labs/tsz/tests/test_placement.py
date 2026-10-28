"""Synthetic-only tests. They never access a network or real host."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from placement import plan


def node(identity, free, *, enrolled=True, online=True, grant=True, mbps=1000):
    return {"id": identity, "accelerator_free_mib": free, "enrolled": enrolled,
            "online": online, "inference_grant": grant,
            "fabric_mbps": mbps, "backend": "example"}


def case(nodes):
    return {"model": {"weights_mib": 3000, "kv_mib": 1000, "layers": 20,
                      "boundary_activation_kib": 256}, "nodes": nodes}


class PlacementTests(unittest.TestCase):
    def test_single_node_preferred(self):
        outcome = plan(case([node("slink", 5500), node("mac", 5500)]))
        self.assertEqual(outcome["status"], "ESTIMATED_SINGLE_NODE_FIT")
        self.assertEqual(outcome["assignments"][0]["node_id"], "mac")
        self.assertEqual(outcome["cross_node_boundaries"], 0)

    def test_contiguous_shards(self):
        outcome = plan(case([node("a", 2300), node("b", 2100)]))
        self.assertEqual(outcome["status"], "ESTIMATED_PIPELINE_FIT")
        self.assertEqual([(r["start_layer"], r["end_layer_exclusive"]) for r in outcome["assignments"]],
                         [(0, 11), (11, 20)])
        self.assertGreater(outcome["transfer_floor_ms_per_token"], 0)

    def test_discovered_unknown_never_selected(self):
        outcome = plan(case([node("unknown", 9000, enrolled=False), node("owner", 3500)]))
        self.assertEqual(outcome["status"], "INSUFFICIENT_AGGREGATE_ACCELERATOR_MEMORY")
        self.assertIn("unknown", outcome["ignored_nodes"])

    def test_revoked_grant_excluded(self):
        self.assertEqual(plan(case([node("revoked", 9999, grant=False)]))["status"],
                         "NO_ENROLLED_READY_INFERENCE_NODES")

    def test_offline_excluded(self):
        self.assertEqual(plan(case([node("offline", 9000, online=False)]))["status"],
                         "NO_ENROLLED_READY_INFERENCE_NODES")

    def test_duplicate_node_rejected(self):
        with self.assertRaises(ValueError):
            plan(case([node("a", 2500), node("a", 2600)]))

    def test_bad_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            plan(case([node("a", 2600, mbps=0)]))

    def test_no_artificial_node_cap(self):
        outcome = plan(case([node(f"n{i}", 210) for i in range(21)]))
        self.assertEqual(outcome["status"], "ESTIMATED_PIPELINE_FIT")
        self.assertEqual(len(outcome["assignments"]), 20)
        self.assertEqual(outcome["assignments"][-1]["end_layer_exclusive"], 20)

    def test_malformed_manifest_and_node_rejected(self):
        for manifest in (None, [], {}, {"model": None}, case([None]), case([{}])):
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                plan(manifest)

    def test_nonfinite_capacity_and_overflow_rejected(self):
        for value in (float('nan'), float('inf'), True, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                plan(case([node('a', value)]))
        manifest = case([node('a', 1e308)])
        manifest['model'].update(weights_mib=1e308, kv_mib=1e308)
        with self.assertRaises(ValueError):
            plan(manifest)

    def test_tiny_memory_shortfall_does_not_round_up_capacity(self):
        manifest = case([node('a', 2000 - 1e-8), node('b', 2000 - 1e-8)])
        self.assertEqual(plan(manifest)['status'], 'INSUFFICIENT_AGGREGATE_ACCELERATOR_MEMORY')

    def test_empty_fleet(self):
        self.assertEqual(plan(case([]))["status"], "NO_ENROLLED_READY_INFERENCE_NODES")


if __name__ == "__main__":
    unittest.main()
