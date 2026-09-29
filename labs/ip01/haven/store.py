"""Single-writer SQLite store; short transactions and separate continuity evidence.

Selective design adaptation: ASTRA astra/store.py at 3aa1ac646052124b98c73d9d1f361bef3c123d81
(SHA256 3533330a1957e5bdeb41275c1a62c5a600efc72cbf8f0f6ad490216fd6be0f75):
connection-scoped PRAGMA verification, BEGIN IMMEDIATE, request digest conflicts,
and after-commit fault testing. This is new IP-01 code, not original qualification.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from contextlib import contextmanager
from .contracts import Denied, UnknownCommit, canonical, digest, uid

TABLES = ('sessions', 'sources', 'source_revisions', 'grants', 'quota_ledger',
          'grant_use_claims', 'drafts', 'jobs', 'contexts', 'attempts', 'events',
          'outputs', 'release_receipts', 'consumption_receipts',
          'delivery_observations', 'eligibility_decisions', 'operations', 'changes', 'recovery')
IMMUTABLE = frozenset(('source_revisions', 'grant_use_claims', 'contexts', 'events',
                      'release_receipts', 'consumption_receipts', 'delivery_observations',
                      'eligibility_decisions', 'operations', 'changes', 'recovery'))


class Transaction:
    def __init__(self, store, connection):
        self.store, self.connection = store, connection

    def get(self, table, key):
        assert table in TABLES
        row = self.connection.execute(f'SELECT body FROM {table} WHERE id=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, table):
        assert table in TABLES
        return [json.loads(row[0]) for row in self.connection.execute(f'SELECT body FROM {table} ORDER BY rowid')]

    def put(self, table, key, value, *, insert=False):
        assert table in TABLES
        if insert or table in IMMUTABLE:
            self.connection.execute(f'INSERT INTO {table}(id,body) VALUES (?,?)', (key, canonical(value)))
        else:
            self.connection.execute(f'INSERT INTO {table}(id,body) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body', (key, canonical(value)))

    def meta(self, key, value=None):
        if value is not None:
            self.connection.execute('INSERT INTO meta(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, canonical(value)))
            return value
        row = self.connection.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    @property
    def sequence(self):
        return self.meta('commit_sequence') + 1

    def remember(self, owner, scope, key, request, result=None):
        op_id = digest([owner, scope, key])
        old = self.get('operations', op_id)
        request_digest = digest(request)
        if old:
            if old['request_digest'] != request_digest:
                raise Denied('IDEMPOTENCY_CONFLICT')
            return old['result']
        if result is not None:
            self.put('operations', op_id, {'id': op_id, 'owner': owner, 'scope': scope,
                'key': key, 'request_digest': request_digest, 'result': result}, insert=True)
        return None


class Store:
    def __init__(self, runtime_dir, *, clock=time.time):
        self.runtime_dir = Path(runtime_dir).resolve()
        self.path = self.runtime_dir / 'data' / 'haven.sqlite3'
        self.sidecar = self.runtime_dir / 'continuity' / 'haven-current.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sidecar.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.clock = clock
        self.fault_after_commit = None  # private development injection, never HTTP exposed
        self.continuity_uncertain = False
        self.continuity_status = 'NEW'
        self._initialize()

    def connect(self):
        c = sqlite3.connect(self.path, timeout=2, isolation_level=None)
        c.execute('PRAGMA busy_timeout=2000')
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('PRAGMA synchronous=FULL')
        if c.execute('PRAGMA synchronous').fetchone()[0] != 2 or c.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
            c.close()
            raise RuntimeError('SQLite safety settings unavailable')
        return c

    def _proof(self, tx):
        return {key: tx.meta(key) for key in ('generation', 'commit_sequence', 'commit_token')}

    def _write_proof(self, proof):
        temporary = self.sidecar.with_suffix('.pending')
        with temporary.open('w', encoding='utf-8', newline='\n') as f:
            f.write(canonical(proof) + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, self.sidecar)

    def _initialize(self):
        with self.lock:
            c = self.connect()
            try:
                if c.execute('PRAGMA journal_mode=WAL').fetchone()[0].lower() != 'wal':
                    raise RuntimeError('WAL unavailable')
                version = c.execute('PRAGMA user_version').fetchone()[0]
                if version not in (0, 1, 2):
                    raise RuntimeError('Unknown schema; preserved for review')
                if version == 0:
                    if c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                        raise RuntimeError('Unversioned database; preserved for review')
                    c.execute('BEGIN IMMEDIATE')
                    c.execute('CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL CHECK(json_valid(value)))')
                    for table in TABLES:
                        c.execute(f'CREATE TABLE {table}(id TEXT PRIMARY KEY, body TEXT NOT NULL CHECK(json_valid(body)))')
                    # DB constraints guard duplicate release/consume even if a caller races.
                    c.execute("CREATE UNIQUE INDEX release_job ON release_receipts(json_extract(body,'$.job_id'))")
                    c.execute("CREATE UNIQUE INDEX release_key ON release_receipts(json_extract(body,'$.release_key'))")
                    c.execute("CREATE UNIQUE INDEX consume_slot ON consumption_receipts(json_extract(body,'$.release_id'))")
                    c.execute("CREATE UNIQUE INDEX grant_claim ON grant_use_claims(json_extract(body,'$.release_id'),json_extract(body,'$.grant_id'),json_extract(body,'$.profile'))")
                    for table in IMMUTABLE:
                        c.execute(f"CREATE TRIGGER {table}_immutable_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'immutable history'); END")
                        c.execute(f"CREATE TRIGGER {table}_immutable_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT,'immutable history'); END")
                    tx = Transaction(self, c)
                    for k, v in {'generation': uid('db'), 'commit_sequence': 0, 'commit_token': uid('commit'),
                                 'authority_instance_epoch': uid('authority'), 'restore_epoch': 1,
                                 'review_only': False, 'last_time': self.clock()}.items():
                        tx.meta(k, v)
                    c.execute('PRAGMA user_version=1')
                    c.commit()
                    self._write_proof(self._proof(tx))
                else:
                    tx = Transaction(self, c)
                    try:
                        proof = json.loads(self.sidecar.read_text(encoding='utf-8'))
                    except (OSError, ValueError):
                        proof = None
                    self.continuity_status = 'INTACT_CURRENT' if proof == self._proof(tx) else 'UNPROVEN_REVIEW_ONLY'
                if version < 2:
                    c.execute('BEGIN IMMEDIATE')
                    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_model_allocation ON attempts(json_extract(body,'$.allocation_token')) WHERE json_extract(body,'$.allocation_token') IS NOT NULL")
                    c.execute('PRAGMA user_version=2')
                    c.commit()
            finally:
                if c.in_transaction:
                    c.rollback()
                c.close()
            # Recovery never resumes an old job, session, or output permit.
            with self.transaction(operation='startup') as tx:
                if self.continuity_status == 'UNPROVEN_REVIEW_ONLY':
                    tx.meta('review_only', True)
                    tx.meta('authority_instance_epoch', uid('authority'))
                    tx.meta('restore_epoch', tx.meta('restore_epoch') + 1)
                for session in tx.all('sessions'):
                    session['active'] = False
                    tx.put('sessions', session['id'], session)
                for job in tx.all('jobs'):
                    job['lease_fence'] += 1
                    if job['disposition'] == 'QUEUED' or job['compute_state'] in ('RUNNING', 'STOP_REQUESTED'):
                        job.update(disposition='INCONCLUSIVE', compute_state='UNKNOWN', error='RESTART_RECONCILIATION_REQUIRED')
                    tx.put('jobs', job['job_id'], job)
                rid = uid('recovery')
                tx.put('recovery', rid, {'id': rid, 'status': self.continuity_status, 'at': self.clock(),
                    'review_only': tx.meta('review_only'), 'resumed_jobs': 0})

    @contextmanager
    def transaction(self, *, write=True, operation=None):
        with self.lock:
            c = self.connect()
            committed = False
            try:
                c.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
                tx = Transaction(self, c)
                yield tx
                if write:
                    tx.meta('commit_sequence', tx.sequence)
                    tx.meta('commit_token', uid('commit'))
                    tx.meta('last_time', max(tx.meta('last_time') or 0, self.clock()))
                    proof = self._proof(tx)
                    c.commit()
                    committed = True
                    try:
                        self._write_proof(proof)
                    except OSError as error:
                        self.continuity_uncertain = True
                        raise UnknownCommit(operation) from error
                    if self.fault_after_commit is not None and self.fault_after_commit == operation:
                        self.fault_after_commit = None
                        raise UnknownCommit(operation)
                else:
                    c.rollback()
            except sqlite3.OperationalError as error:
                if committed:
                    raise UnknownCommit(operation) from error
                raise Denied('STORE_UNAVAILABLE', 503) from error
            finally:
                if c.in_transaction:
                    c.rollback()
                c.close()

    def close(self):
        with self.lock:
            c = self.connect()
            try:
                c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            finally:
                c.close()
