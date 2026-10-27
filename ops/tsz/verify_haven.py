"""Isolated integration check against an explicitly supplied Haven engineer tree.

Uses a SYNTHETIC approval/binding and real local telemetry/Executor.call.
Never reads owner approvals, enrolls a real node, uses SSH, calls a model,
starts a service or modifies the supplied source tree. All writes are temporary.
Run as: python3 -m ops.tsz.verify_haven --engineer-dir /path/to/labs/engineer
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

from . import fleet, haven_adapter as adapter


def verify(engineer_dir):
    engineer_dir = Path(engineer_dir).resolve()
    sys.path.insert(0, str(engineer_dir))
    from executor import Executor
    from ledger import Ledger
    from policy import Scope
    spec = importlib.util.spec_from_file_location('haven_engineer_fleet', engineer_dir / 'fleet.py')
    haven_fleet = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(haven_fleet)
    source_hashes = {name: hashlib.sha256((engineer_dir / name).read_bytes()).hexdigest()
                     for name in ('fleet.py', 'executor.py', 'policy.py', 'ledger.py')}
    with tempfile.TemporaryDirectory(prefix='tsz-integration-') as temp:
        root = Path(temp)
        workspace = root / 'fixture-workspace'
        workspace.mkdir()
        (workspace / 'fixture.txt').write_text('synthetic workspace\n')
        state_dir = root / 'coordinator'
        state_dir.mkdir(mode=0o700)
        now = int(time.time())
        state = fleet.empty_state()
        seen = fleet.observation('192.0.2.1', '02:00:00:00:00:01', 'fixture0', 'synthetic')
        fleet.update_candidates(state, [seen], now)
        fleet.reconcile_approved(state, {'schema': fleet.DECISION_SCHEMA, 'revision': 1,
            'expires_at': now + 300, 'nodes': [{'node_id': 'fixture-node',
                'candidate_id': seen['candidate_id'], 'roles': ['inventory']}]}, now)
        fleet.write_state(state_dir, state)
        registry = {'nodes': [{'name': 'fixture-host', 'kind': 'local', 'roles': ['tools'], 'trust': 'LOCAL_HOST'}]}
        bindings = {'fixture-node': {'haven_name': 'fixture-host', 'kind': 'local', 'candidate_id': seen['candidate_id']}}
        coordinator = adapter.Coordinator(state_dir, lambda: registry, lambda: bindings)
        reports = adapter.collect(state, registry, bindings, haven_fleet)
        if not reports:
            raise RuntimeError('real local observer did not supply usable telemetry')
        job = {'id': 'fixture-list', 'role': 'inventory', 'cpu_cores': 1, 'memory_mib': 16,
               'tool': 'list_dir', 'args': {'path': '.', 'depth': 1}}
        rec = coordinator.reserve(job, reports, ttl=60)
        if rec['status'] != 'RESERVED':
            raise RuntimeError('insufficient real capacity for the bounded fixture')
        # Executor scratch writes stay inside this fixture, not the owner HOME.
        with patch.object(Path, 'home', return_value=root):
            ledger = Ledger(root / 'receipts' / 'actions.jsonl', session='tsz-fixture')
            executor = Executor(workspace, Scope(mode='observe', network=False), ledger,
                                agent='tsz-integration-fixture', state_dir=root / 'executor-state')
            result = coordinator.dispatch_local('fixture-list', rec['token'], executor, haven_fleet)
        if result.get('status') != 'succeeded' or 'fixture.txt' not in result.get('text', ''):
            raise RuntimeError('existing executor failed the fixture directory diagnostic')
        if not any(r['receipt'] == result['receipt'] and r['status'] == 'succeeded' for r in ledger.receipts()):
            raise RuntimeError('no matching succeeded executor receipt')
        try:
            coordinator.dispatch_local('fixture-list', rec['token'], executor, haven_fleet)
        except adapter.AdmissionError:
            pass
        else:
            raise RuntimeError('duplicate dispatch was accepted')
        return {'status': 'PASS', 'approval': 'SYNTHETIC_FIXTURE_ONLY', 'telemetry': 'REAL_LOCAL_OBSERVER',
                'execution': 'REAL_HAVEN_EXECUTOR', 'tool': 'list_dir', 'receipt_verified': True,
                'replay_rejected': True, 'source_sha256': source_hashes}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engineer-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.engineer_dir), indent=2))
