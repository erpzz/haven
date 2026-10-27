"""Regression coverage for malformed state, private I/O and concurrent updates."""
import copy
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ops.tsz import fleet, private_io, worker_runtime as worker

NOW = 1800000000


def seeded():
    state = fleet.empty_state()
    seen = fleet.observation('192.0.2.1', 'aa:bb:cc:dd:ee:ff', 'test0', 'synthetic')
    fleet.update_candidates(state, [seen], NOW)
    export = {'schema': fleet.DECISION_SCHEMA, 'revision': 1, 'expires_at': NOW + 300,
              'nodes': [{'node_id': 'test-node', 'candidate_id': seen['candidate_id'], 'roles': ['inventory', 'engineering']}]}
    fleet.reconcile_approved(state, export, NOW)
    return state, export


def increment(path):
    for _ in range(10):
        with fleet.fleet_lock(Path(path)):
            state = fleet.read_state(Path(path))
            state['generation'] += 1
            fleet.write_state(Path(path), state)


class HardeningTests(unittest.TestCase):
    def test_revoke_then_rebind_forbidden(self):
        state, export = seeded()
        empty = {**export, 'revision': 2, 'nodes': []}
        fleet.reconcile_approved(state, empty, NOW)
        seen = fleet.observation('192.0.2.2', 'aa:bb:cc:dd:ee:00', 'test0', 'synthetic')
        fleet.update_candidates(state, [seen], NOW)
        export['revision'] = 3
        export['nodes'][0]['candidate_id'] = seen['candidate_id']
        with self.assertRaises(fleet.FleetError):
            fleet.reconcile_approved(state, export, NOW)

    def test_approval_rollback_conflict_and_downgrade_rejected(self):
        state, export = seeded()
        revoked = {**export, 'revision': 2, 'nodes': []}
        fleet.reconcile_approved(state, revoked, NOW)
        for doc in (export, {**export, 'revision': 2}, {k: v for k, v in export.items() if k != 'revision'}):
            with self.subTest(doc=doc), self.assertRaises(fleet.FleetError):
                fleet.reconcile_approved(state, doc, NOW)
        self.assertEqual(state['nodes'], {})
        fleet.reconcile_approved(state, revoked, NOW)  # exact retry is idempotent in authority

    def test_invalid_snapshot_does_not_partially_apply(self):
        state, export = seeded()
        old = copy.deepcopy(state)
        export['revision'] = 2
        export['nodes'].append({'node_id': 'bad', 'roles': [[]]})
        with self.assertRaises(fleet.FleetError):
            fleet.reconcile_approved(state, export, NOW)
        self.assertEqual(state, old)

    def test_import_capture_time_preserved_and_never_regresses(self):
        state, _ = seeded()
        seen = fleet.observation('192.0.2.1', 'aa:bb:cc:dd:ee:00', 'test0', 'synthetic')
        seen['observed_at'] = NOW - 100
        fleet.update_candidates(state, [seen], NOW)
        self.assertEqual(state['candidates'][seen['candidate_id']]['last_seen'], NOW - 100)
        seen['observed_at'] = NOW - 200
        fleet.update_candidates(state, [seen], NOW)
        self.assertEqual(state['candidates'][seen['candidate_id']]['last_seen'], NOW - 100)

    def test_malformed_persisted_node_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            state, _ = seeded()
            state['nodes']['test-node']['approved_until'] = 'forever'
            fleet.write_state(Path(temp), state)
            with self.assertRaises(fleet.FleetError):
                fleet.read_state(Path(temp))

    def test_linux_array_failure_states_are_not_candidates(self):
        records = [{'dev': 'test0', 'dst': '192.0.2.1', 'lladdr': 'aa:bb:cc:dd:ee:ff', 'state': ['FAILED']}]
        self.assertEqual(fleet.parse_linux(json.dumps(records), {'test0'}), [])

    def test_malformed_heartbeat_and_roles_fail_closed(self):
        state, _ = seeded()
        for hb in (None, [], 'oops', {'schema': worker.SCHEMA, 'roles': [[]]}):
            self.assertFalse(worker.usable_heartbeat(state, 'test-node', hb, NOW))
        for value in ('future', True, None, float('nan')):
            state['nodes']['test-node']['approved_until'] = value
            self.assertFalse(worker.usable_heartbeat(state, 'test-node', {}, NOW))

    def test_malformed_jobs_have_domain_error(self):
        for job in (None, [], {'id': 'bad', 'role': []}):
            with self.assertRaises(worker.WorkerError):
                worker.place_jobs({'nodes': {}}, {}, [job], NOW)

    def test_concurrent_state_updates_no_lost_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            state, _ = seeded()
            fleet.write_state(path, state)
            ctx = multiprocessing.get_context('spawn')
            processes = [ctx.Process(target=increment, args=(temp,)) for _ in range(3)]
            for process in processes:
                process.start()
            for process in processes:
                process.join(15)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(fleet.read_state(path)['generation'], state['generation'] + 30)

    def test_reject_duplicate_keys_nan_oversize_and_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.json'
            for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '[]', ' ' * (private_io.MAX_SIZE + 1)):
                path.write_text(raw)
                path.chmod(0o600)
                with self.assertRaises(ValueError):
                    private_io.read_json(path)
            path.write_text('{}')
            for mode in (0o644, 0o660, 0o700):
                path.chmod(mode)
                with self.assertRaises(ValueError):
                    private_io.read_json(path)

    def test_oversized_write_preserves_previous_state(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.json'
            private_io.write_json(path, {'value': 'original'})
            with self.assertRaises(ValueError):
                private_io.write_json(path, {'value': 'x' * private_io.MAX_SIZE})
            self.assertEqual(private_io.read_json(path), {'value': 'original'})

    def test_fifo_and_hardlink_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.json'
            os.mkfifo(path, 0o600)
            with self.assertRaises(ValueError):
                private_io.read_json(path)
            path.unlink()
            private_io.write_json(path, {})
            os.link(path, Path(temp) / 'linked')
            with self.assertRaises(ValueError):
                private_io.read_json(path)

    def test_swapped_file_is_checked_after_open(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.json'
            private_io.write_json(path, {})
            original = os.open
            def replaced(name, flags, *args, **kwargs):
                path.chmod(0o644)
                return original(name, flags, *args, **kwargs)
            with patch.object(private_io.os, 'open', side_effect=replaced), self.assertRaises(ValueError):
                private_io.read_json(path)

    def test_symlink_directory_lock_and_dangling_output_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            link = path / 'link'
            link.symlink_to(path, target_is_directory=True)
            with self.assertRaises(ValueError):
                private_io.private_dir(link)
            lock = path / '.fleet.lock'
            lock.symlink_to(path / 'absent')
            with self.assertRaises(OSError):
                with private_io.lock(path):
                    self.fail('followed lock symlink')
            with self.assertRaises(ValueError):
                private_io.write_json(lock, {})
