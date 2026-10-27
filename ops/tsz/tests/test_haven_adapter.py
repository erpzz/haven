"""Synthetic integration tests. No host probes, SSH connections or inference."""
import copy
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from ops.tsz import fleet, haven_adapter as adapter, private_io
from test_hardening import NOW, seeded


def fixture():
    state, export = seeded()
    registry = {'nodes': [{'name': 'fixture-local', 'kind': 'local', 'roles': ['tools'], 'trust': 'LOCAL_HOST'}]}
    bindings = {'test-node': {'haven_name': 'fixture-local', 'kind': 'local',
                             'candidate_id': export['nodes'][0]['candidate_id']}}
    return state, registry, bindings


def job(name='test-job'):
    return {'id': name, 'role': 'engineering', 'cpu_cores': 1, 'memory_mib': 128,
            'tool': 'list_dir', 'args': {'path': '.', 'depth': 1}}


def observer(cores=1, memory=128):
    return Mock(observe_local=Mock(return_value={'os': 'Linux test', 'cores': cores, 'mem_avail': memory * 1024 * 1024}))


def reserve_process(path, name, queue):
    state, registry, bindings = fixture()
    coord = adapter.Coordinator(path, lambda: registry, lambda: bindings, lambda: NOW)
    with patch('ops.tsz.worker_runtime.platform.system', return_value='Linux'):
        reports = adapter.collect(state, registry, bindings, observer(), NOW)
        queue.put(coord.reserve(job(name), reports)['status'])


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.state, self.registry, self.bindings = fixture()
        fleet.write_state(self.path, self.state)
        self.now = NOW
        self.coord = adapter.Coordinator(self.path, lambda: self.registry, lambda: self.bindings, lambda: self.now)
        self.probe = observer()
        self.platform = patch('ops.tsz.worker_runtime.platform.system', return_value='Linux')
        self.platform.start()
        self.addCleanup(self.platform.stop)
        self.reports = adapter.collect(self.state, self.registry, self.bindings, self.probe, NOW)
        self.executor = Mock(call=Mock(return_value={'receipt': 'R-synthetic', 'status': 'succeeded'}))

    def reserve(self, name='test-job'):
        return self.coord.reserve(job(name), self.reports)

    def dispatch(self, rec):
        return self.coord.dispatch_local(rec['job']['id'], rec['token'], self.executor, self.probe)

    def test_vertical_slice_existing_executor_interface(self):
        rec = self.reserve()
        result = self.dispatch(rec)
        self.executor.call.assert_called_once_with('list_dir', {'path': '.', 'depth': 1})
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(self.reserve('next-job')['status'], 'RESERVED')
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)
        with self.assertRaises(adapter.AdmissionError):
            self.reserve()

    def test_reservations_persist_across_instances(self):
        self.reserve()
        other = adapter.Coordinator(self.path, lambda: self.registry, lambda: self.bindings, lambda: NOW)
        self.assertEqual(other.reserve(job('second'), self.reports)['status'], 'NO_ELIGIBLE_CAPACITY')

    def test_concurrent_processes_cannot_overbook(self):
        ctx = multiprocessing.get_context('spawn')
        queue = ctx.Queue()
        processes = [ctx.Process(target=reserve_process, args=(str(self.path), f'j{i}', queue)) for i in range(3)]
        for p in processes:
            p.start()
        for p in processes:
            p.join(15)
            self.assertEqual(p.exitcode, 0)
        results = [queue.get(timeout=3) for _ in processes]
        self.assertEqual(results.count('RESERVED'), 1)
        self.assertEqual(results.count('NO_ELIGIBLE_CAPACITY'), 2)

    def test_revoked_node_cannot_dispatch(self):
        rec = self.reserve()
        self.state['nodes'] = {}
        fleet.write_state(self.path, self.state)
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)
        self.executor.call.assert_not_called()

    def test_role_downgrade_cannot_dispatch(self):
        rec = self.reserve()
        self.state['nodes']['test-node']['roles'] = ['inventory']
        fleet.write_state(self.path, self.state)
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)
        self.executor.call.assert_not_called()

    def test_registry_and_binding_changes_cannot_dispatch(self):
        rec = self.reserve()
        self.bindings['test-node']['haven_name'] = 'different'
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)
        self.executor.call.assert_not_called()

    def test_expiry_during_probe_does_not_dispatch(self):
        rec = self.reserve()
        def probe():
            self.now = NOW + 31
            return {'os': 'Linux', 'cores': 1, 'mem_avail': 128 * 1024 * 1024}
        self.probe.observe_local.side_effect = probe
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)
        self.executor.call.assert_not_called()

    def test_registry_revocation_during_probe_blocks_dispatch(self):
        rec = self.reserve()
        def probe():
            self.registry['nodes'][0]['roles'] = []
            return {'os': 'Linux', 'cores': 1, 'mem_avail': 128 * 1024 * 1024}
        self.probe.observe_local.side_effect = probe
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)
        self.executor.call.assert_not_called()

    def test_reprobe_capacity_loss_blocks(self):
        rec = self.reserve()
        self.probe.observe_local.return_value['mem_avail'] = 0
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)
        self.executor.call.assert_not_called()

    def test_cancel_releases_only_unstarted_reservation(self):
        rec = self.reserve()
        self.coord.cancel('test-job', rec['token'])
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)
        self.assertEqual(self.reserve('second')['status'], 'RESERVED')

    def test_expired_pending_released_but_not_replayed(self):
        rec = self.reserve()
        self.now += 31
        self.assertEqual(self.reserve('second')['status'], 'RESERVED')
        with self.assertRaises(adapter.AdmissionError):
            self.dispatch(rec)

    def test_unknown_execution_retains_capacity_after_expiry(self):
        rec = self.reserve()
        self.executor.call.side_effect = RuntimeError('transport lost')
        with self.assertRaises(RuntimeError):
            self.dispatch(rec)
        self.now += 31
        self.assertEqual(self.reserve('second')['status'], 'NO_ELIGIBLE_CAPACITY')
        with self.assertRaises(adapter.AdmissionError):
            self.coord.cancel('test-job', rec['token'])

    def test_executor_unknown_or_no_receipt_does_not_release(self):
        rec = self.reserve()
        self.executor.call.return_value = {'status': 'unknown', 'receipt': 'R-unknown'}
        self.dispatch(rec)
        self.assertEqual(self.reserve('second')['status'], 'NO_ELIGIBLE_CAPACITY')

    def test_remote_handoff_never_falls_back_to_local_executor(self):
        self.registry['nodes'][0].update(kind='ssh', ssh='fixture-node', trust='OWNER_SSH', host_fingerprint='SHA256:fixture')
        self.bindings['test-node'].update(kind='ssh', ssh='fixture-node', host_fingerprint='SHA256:fixture')
        self.probe.observe_ssh.return_value = {'os': 'Linux', 'cores': 1, 'mem_avail': 128 * 1024 * 1024}
        self.reports = adapter.collect(self.state, self.registry, self.bindings, self.probe, NOW)
        rec = self.reserve()
        with self.assertRaisesRegex(adapter.AdmissionError, 'remote Executor transport'):
            self.dispatch(rec)
        self.executor.call.assert_not_called()
        self.probe.observe_ssh.assert_called_once()

    def test_untrusted_ssh_and_option_alias_are_not_probed(self):
        self.registry['nodes'][0].update(kind='ssh', ssh='-oProxyCommand=bad', trust='OWNER_SSH', host_fingerprint='SHA256:fixture')
        self.bindings['test-node'].update(kind='ssh', ssh='-oProxyCommand=bad', host_fingerprint='SHA256:fixture')
        self.assertEqual(adapter.collect(self.state, self.registry, self.bindings, self.probe, NOW), {})
        self.probe.observe_ssh.assert_not_called()

    def test_offline_ssh_report_is_excluded(self):
        self.registry['nodes'][0].update(kind='ssh', ssh='fixture-node', trust='OWNER_SSH', host_fingerprint='SHA256:fixture')
        self.bindings['test-node'].update(kind='ssh', ssh='fixture-node', host_fingerprint='SHA256:fixture')
        self.probe.observe_ssh.return_value = {'status': 'UNTRUSTED'}
        self.assertEqual(adapter.collect(self.state, self.registry, self.bindings, self.probe, NOW), {})

    def test_duplicate_local_host_cannot_multiply_capacity(self):
        candidate = fleet.observation('192.0.2.2', 'aa:bb:cc:dd:ee:00', 'test0', 'synthetic')
        fleet.update_candidates(self.state, [candidate], NOW)
        self.state['nodes']['another'] = {**self.state['nodes']['test-node'], 'candidate_id': candidate['candidate_id']}
        self.registry['nodes'].append({**self.registry['nodes'][0], 'name': 'local-alias'})
        self.bindings['another'] = {'haven_name': 'local-alias', 'kind': 'local', 'candidate_id': candidate['candidate_id']}
        with self.assertRaises(adapter.AdmissionError):
            adapter.approved_view(self.state, self.registry, self.bindings, NOW)

    def test_failed_or_refused_receipt_releases_capacity(self):
        for status in ('failed', 'refused'):
            rec = self.reserve('job-' + status)
            self.executor.call.return_value = {'receipt': 'R-fixture', 'status': status}
            self.dispatch(rec)
            self.assertEqual(self.coord._load()['jobs']['job-' + status]['status'], 'DONE')

    def test_running_after_crash_is_not_reclaimed_by_ttl(self):
        self.reserve()
        data = self.coord._load()
        data['jobs']['test-job']['status'] = 'RUNNING'
        self.coord._save(data)
        self.now += 31
        self.assertEqual(self.reserve('second')['status'], 'NO_ELIGIBLE_CAPACITY')

    def test_legacy_unversioned_approval_not_dispatchable(self):
        del self.state['approval_revision']
        with self.assertRaises(adapter.AdmissionError):
            adapter.approved_view(self.state, self.registry, self.bindings, NOW)

    def test_stale_future_malformed_telemetry_no_capacity(self):
        for value in (None, [], {**self.reports['test-node'], 'recorded_at': NOW - 91},
                      {**self.reports['test-node'], 'recorded_at': NOW + 1}):
            self.reports['test-node'] = value
            self.assertEqual(self.reserve()['status'], 'NO_ELIGIBLE_CAPACITY')

    def test_arbitrary_tool_and_training_not_admitted(self):
        for change in ({'role': 'training'}, {'tool': 'run_command'}, {'args': {'path': '..', 'depth': 4}}, {'cpu_cores': True}):
            with self.assertRaises(adapter.AdmissionError):
                self.coord.reserve({**job(), **change}, self.reports)

    def test_malformed_reservations_are_not_reset(self):
        private_io.write_json(self.path / 'reservations.json', {'schema': 'tsz-reservations-v1', 'jobs': {'bad': []}})
        with self.assertRaises(adapter.AdmissionError):
            self.reserve()
