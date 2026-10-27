"""Synthetic-only enrollment tests; no real network access or host mutation."""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tsz_fleet import (
    EnrollmentError, approve, attest, candidate_id, deployment_plan,
    locked_state, new_state, normalize_mac, parse_linux_neighbors,
    parse_macos_arp, passive_observe, record_observations, revoke,
    save_state, verify_receipt,
)

T = 1_800_000_000
OWNER_KEY = b"a" * 32
ATTESTOR_KEY = b"b" * 32
FINGERPRINT = "9" * 64


def sign(payload: dict, key: bytes) -> dict:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return {**payload, "signature": hmac.new(key, raw, hashlib.sha256).hexdigest()}


def grant(cid: str, *, nonce: str = "a" * 32, fp: str = FINGERPRINT):
    return sign({"kind": "tsz-approval-v1", "candidate_id": cid,
                 "node_id": "authorized-node", "device_key_sha256": fp,
                 "scopes": ["inference"], "expires_at": T + 3600,
                 "nonce": nonce}, OWNER_KEY)


def attestation(*, nonce="b" * 32, fp=FINGERPRINT, approval_nonce="a" * 32):
    return sign({"kind": "tsz-attestation-v1", "node_id": "authorized-node",
                 "device_key_sha256": fp, "approval_nonce": approval_nonce,
                 "expires_at": T + 3600, "nonce": nonce}, ATTESTOR_KEY)


def state_with_candidate():
    state = new_state()
    observed = [{"candidate_id": candidate_id("en0", "aa:bb:cc:dd:ee:ff"),
                 "address": "192.0.2.15", "mac": "aa:bb:cc:dd:ee:ff",
                 "interface": "en0", "origin": "fixture"}]
    record_observations(state, observed, T)
    return state, observed[0]["candidate_id"]


class DiscoveryTests(unittest.TestCase):
    def test_macos_cache_parser_scoped(self):
        sample = "? (192.0.2.15) at a:b:c:d:e:f on en0 ifscope [ethernet]\n" + \
                 "? (198.51.100.7) at ff:ee:dd:cc:bb:aa on en7 ifscope [ethernet]\n" + \
                 "? (192.0.2.25) at (incomplete) on en0 ifscope [ethernet]"
        parsed = parse_macos_arp(sample, {"en0"})
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["mac"], "0a:0b:0c:0d:0e:0f")

    def test_linux_neighbor_scope_and_failed(self):
        text = json.dumps([
            {"dst": "192.0.2.15", "lladdr": "aa:bb:cc:dd:ee:ff", "dev": "eth0", "state": "REACHABLE"},
            {"dst": "192.0.2.16", "lladdr": "aa:bb:cc:dd:ee:01", "dev": "eth0", "state": "FAILED"},
            {"dst": "198.51.100.1", "lladdr": "aa:bb:cc:dd:ee:02", "dev": "eth1", "state": "STALE"},
        ])
        parsed = parse_linux_neighbors(text, {"eth0"})
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["address"], "192.0.2.15")

    def test_passive_only_calls_fixed_os_utility(self):
        from subprocess import CompletedProcess
        with patch("tsz_fleet.platform.system", return_value="Darwin"), \
             patch("tsz_fleet.subprocess.run", return_value=CompletedProcess(
                 ["arp", "-an"], 0, "? (192.0.2.15) at aa:bb:cc:dd:ee:ff on en0", ""
             )) as process:
            found = passive_observe({"en0"})
        self.assertEqual(len(found), 1)
        self.assertEqual(process.call_args.args[0], ["arp", "-an"])

    def test_candidate_only_unverified(self):
        state, cid = state_with_candidate()
        self.assertEqual(state["candidates"][cid]["trust"], "UNVERIFIED")
        self.assertFalse(deployment_plan(state, T))

    def test_repeat_updates_not_readds(self):
        state, cid = state_with_candidate()
        observation = {"candidate_id": cid, "address": "192.0.2.17",
                       "mac": "aa:bb:cc:dd:ee:ff", "interface": "en0", "origin": "fixture"}
        self.assertEqual(record_observations(state, [observation], T + 1), 0)
        self.assertEqual(len(state["candidates"][cid]["addresses"]), 2)


class EnrollmentTests(unittest.TestCase):
    def test_grant_then_independent_attestation(self):
        state, cid = state_with_candidate()
        node = approve(state, grant(cid), OWNER_KEY, T)
        self.assertEqual(node["status"], "AWAITING_EXTERNAL_ATTESTATION")
        self.assertEqual(deployment_plan(state, T), [])
        node = attest(state, attestation(), ATTESTOR_KEY, T)
        self.assertEqual(node["status"], "AUTHORIZED_PENDING_DEPLOYMENT")
        self.assertEqual(len(deployment_plan(state, T)), 1)

    def test_discovered_unknown_cannot_approve_without_receipt(self):
        state, cid = state_with_candidate()
        fake = grant(cid)
        fake["device_key_sha256"] = "0" * 64
        with self.assertRaises(EnrollmentError):
            approve(state, fake, OWNER_KEY, T)
        self.assertFalse(state["nodes"])

    def test_grant_cannot_enroll_absent_candidate(self):
        with self.assertRaises(EnrollmentError):
            approve(new_state(), grant("neighbor-no-match"), OWNER_KEY, T)

    def test_expired_grants_fail(self):
        state, cid = state_with_candidate()
        with self.assertRaises(EnrollmentError):
            approve(state, grant(cid), OWNER_KEY, T + 3700)

    def test_approval_nonce_cannot_replay(self):
        state, cid = state_with_candidate()
        approve(state, grant(cid), OWNER_KEY, T)
        with self.assertRaises(EnrollmentError):
            approve(state, grant(cid), OWNER_KEY, T)

    def test_attestation_key_must_be_independent(self):
        state, cid = state_with_candidate()
        approve(state, grant(cid), OWNER_KEY, T)
        with self.assertRaises(EnrollmentError):
            attest(state, attestation(), OWNER_KEY, T)

    def test_attestation_binding_required(self):
        state, cid = state_with_candidate()
        approve(state, grant(cid), OWNER_KEY, T)
        with self.assertRaises(EnrollmentError):
            attest(state, attestation(approval_nonce="e" * 32), ATTESTOR_KEY, T)

    def test_no_dispatch_after_expiry(self):
        state, cid = state_with_candidate()
        approve(state, grant(cid), OWNER_KEY, T)
        attest(state, attestation(), ATTESTOR_KEY, T)
        self.assertEqual(deployment_plan(state, T + 3600), [])

    def test_revoke_and_replay(self):
        state, cid = state_with_candidate()
        approve(state, grant(cid), OWNER_KEY, T)
        attest(state, attestation(), ATTESTOR_KEY, T)
        payload = sign({"kind": "tsz-revocation-v1", "node_id": "authorized-node",
                        "device_key_sha256": FINGERPRINT,
                        "expires_at": T + 3600, "nonce": "c" * 32}, OWNER_KEY)
        self.assertEqual(revoke(state, payload, OWNER_KEY, T)["status"], "REVOKED")
        self.assertEqual(deployment_plan(state, T), [])
        with self.assertRaises(EnrollmentError):
            revoke(state, payload, OWNER_KEY, T)

    def test_receipt_rejects_non_hex_signature(self):
        receipt = {"kind": "tsz-approval-v1", "expires_at": T + 10, "nonce": "a" * 32, "signature": "../"}
        with self.assertRaises(EnrollmentError):
            verify_receipt(receipt, OWNER_KEY, "tsz-approval-v1", T)

    def test_private_persistence_permissions(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch) / "tsz"
            with locked_state(root) as state:
                record_observations(state, [{
                    "candidate_id": candidate_id("en0", "aa:bb:cc:dd:ee:ff"),
                    "address": "192.0.2.15", "mac": "aa:bb:cc:dd:ee:ff",
                    "interface": "en0", "origin": "fixture"
                }], T)
                save_state(root, state)
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertEqual((root / "fleet.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
