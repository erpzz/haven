"""Runnable Haven IP-01 synthetic local assistant. No inference on startup."""
from __future__ import annotations
import asyncio
import base64
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import importlib
import io
import json
import math
import os
from pathlib import Path
import secrets
import time
import warnings
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, UnidentifiedImageError
from .contracts import (Denied, UnknownCommit, canonical, digest, raw_digest, uid, LIMITS,
    SessionRequest, NoteRequest, NoteEdit, RevisionRequest, GrantRequest, DraftRequest,
    DraftEdit, AnswerRequest, ConsumeRequest, ObservationRequest)
from .store import Store
from . import authority as auth

HERE = Path(__file__).resolve().parent
CLONE = HERE.parents[2]
COOKIE = 'haven_session'
ALLOWED_HOSTS = {f'{host}:{port}' for host in ('127.0.0.1', 'localhost') for port in range(8765, 8768)}
MAX_REQUEST = 2 * 1024 * 1024 + 65536


def runtime_path(value=None):
    root = Path(value or os.environ.get('HAVEN_RUNTIME_DIR', CLONE / '.ip01-runtime')).resolve()
    if not root.is_relative_to(CLONE / '.ip01-runtime') and not root.is_relative_to(CLONE.with_name(CLONE.name + '-eval')):
        raise RuntimeError('Runtime state must stay in the assigned private runtime or evaluator sibling')
    root.mkdir(parents=True, exist_ok=True)
    return root


def wire_job(job):
    keys = ('job_id', 'request_id', 'request_digest', 'attempt_id', 'lease_fence', 'cancel_epoch',
            'route', 'deadline_utc', 'max_elapsed_ms', 'reservation_id')
    result = {k: job[k] for k in keys}
    result['deadline_utc'] = datetime.fromtimestamp(job['deadline_utc'], timezone.utc).isoformat()
    return result


def valid_runtime_usage(usage):
    """Defense in depth on the runtime's validated, attributed usage evidence."""
    if usage is None:
        return True
    bounds = {'model_calls': 1, 'prompt_tokens': 4096, 'output_tokens': 768, 'duration_ns': 120_000_000_000}
    if not isinstance(usage, dict) or not set(usage) <= set(bounds) | {'certainty'}:
        return False
    for name, value in usage.items():
        if name == 'certainty':
            if value not in ('OBSERVED', 'BACKEND_REPORTED', 'UNKNOWN'):
                return False
        elif value is not None and (type(value) is not int or not 0 <= value <= bounds[name]):
            return False
    return True


class ApplicationService:
    def __init__(self, store):
        self.store, self.supervisor = store, None
        self.tasks = set()
        self.runtime_status = 'NOT_AVAILABLE'

    def model_gate(self):
        # Metadata-only root gate; no load, model claim or inference here.
        try:
            from .model_adapter import ModelAdapter
            snapshot = ModelAdapter(self.store.runtime_dir).gate_snapshot()
            gate = snapshot.get('gate', {})
            expires = datetime.fromisoformat(gate.get('expires_utc', '').replace('Z', '+00:00')).timestamp()
        except (ImportError, OSError, ValueError, TypeError):
            return None
        if gate.get('version') != 'ip01.model-gate.v1' or not snapshot.get('enabled') or expires <= self.store.clock():
            return None
        if gate.get('scope') != 'SYNTHETIC_LOCAL_TEXT_IMAGE_ONLY' or not gate.get('independent_benign_receipt_sha256'):
            return None
        identity = gate.get('identity', {})
        if not all(isinstance(identity.get(k), str) and len(identity[k]) == 64 for k in ('manifest_sha256', 'runtime_sha256', 'template_sha256', 'preprocessor_sha256')):
            return None
        return snapshot

    async def admit_attempt(self, job_id, attempt_id, fence):
        try:
            with self.store.transaction(operation='admit:' + job_id) as tx:
                job = tx.get('jobs', job_id)
                if not job or job['attempt_id'] != attempt_id or job['lease_fence'] != fence:
                    raise Denied('STALE_ATTEMPT')
                if job['disposition'] != 'QUEUED' or tx.get('attempts', attempt_id):
                    raise Denied('ATTEMPT_ALREADY_ADMITTED')
                context = tx.get('contexts', job['context_id'])
                auth.check_current(tx, context['authority_vector'], phase='admission')
                model_identity, allocation, snapshot, phase = None, None, None, None
                if job['route'] == 'model':
                    snapshot = self.model_gate()
                    if not snapshot:
                        raise Denied('MODEL_GATE_CLOSED', 503)
                    gate = snapshot['gate']
                    used = {a.get('allocation_token') for a in tx.all('attempts')}
                    phase = os.environ.get('HAVEN_MODEL_ALLOCATION', 'readiness')
                    if phase not in ('readiness', 'lifecycle', 'final'):
                        raise Denied('INVALID_MODEL_ALLOCATION', 503)
                    allocation = next((token for token, slot in sorted(gate['slots'].items()) if token not in used and slot['allocation'] == phase), None)
                    if not allocation:
                        raise Denied('MODEL_ALLOCATION_EXHAUSTED', 503)
                    model_identity = {**gate['identity'], 'inference_authorized': True}
                    auth.check_current(tx, context['authority_vector'], phase='egress')
                tx.put('attempts', attempt_id, {'id': attempt_id, 'job_id': job_id, 'lease_fence': fence,
                    'cancel_epoch': job['cancel_epoch'], 'status': 'ADMITTED', 'at': self.store.clock(),
                    'allocation_token': allocation, 'model_identity': model_identity,
                    'job_binding': wire_job(job), 'binding_id': attempt_id,
                    'context_digest': context['context_digest'],
                    'authority_vector_digest': digest(context['authority_vector']),
                    'model_gate_sha256': snapshot['model_gate_sha256'] if snapshot else None,
                    'model_allocation': phase,
                    'execution_mode': 'IN_PROCESS_DETERMINISTIC' if job['route'] == 'deterministic' else 'OWNED_WORKER'})
                response = {'decision': 'ADMITTED', 'context': {k: v for k, v in context.items() if k != 'context_digest'},
                            'authority_vector': context['authority_vector'], 'job': wire_job(job),
                            'limits': dict(LIMITS), 'model_identity': model_identity}
                if context.get('image_source_id'):
                    source = tx.get('sources', context['image_source_id'])
                    image_bytes = (self.store.runtime_dir / 'media' / (source['id'] + '.png')).read_bytes()
                    if raw_digest(image_bytes) != source['image']['derivative_sha256']:
                        raise Denied('IMAGE_INTEGRITY_FAILED')
                    response['context']['image_base64'] = base64.b64encode(image_bytes).decode('ascii')
                    response['context']['image_sha256'] = source['image']['derivative_sha256']
                if allocation:
                    response['limits'].update(model_attempt_token=allocation, model_allocation=phase,
                        model_binding_id=attempt_id, model_gate_sha256=snapshot['model_gate_sha256'])
                if digest(response['context']) != context['context_digest']:
                    raise Denied('SEALED_CONTEXT_MISMATCH')
            return response
        except Denied as error:
            return {'decision': 'UNKNOWN' if isinstance(error, UnknownCommit) else 'DENIED', 'reason': error.code}

    async def authorize_egress(self, job_id, attempt_id, fence, context_digest):
        """Fresh post-readiness ordering point, never a new admission or claim."""
        empty = {'decision': 'UNKNOWN', 'reason': 'EGRESS_STATE_UNKNOWN', 'job_id': job_id,
            'attempt_id': attempt_id, 'lease_fence': fence, 'context_digest': context_digest,
            'cancel_epoch': None, 'decision_id': None, 'checked_at': None, 'valid_until': None,
            'authority_vector_digest': None, 'model_gate_sha256': None}
        try:
            with self.store.transaction(operation='egress:' + str(attempt_id)) as tx:
                response = dict(empty)
                vector_ref = None
                try:
                    job, attempt = tx.get('jobs', job_id), tx.get('attempts', attempt_id)
                    if not job or not attempt:
                        raise ValueError('unresolved admitted attempt')
                    response['cancel_epoch'] = attempt['cancel_epoch']
                    if (attempt['status'] != 'ADMITTED' or attempt['job_id'] != job_id or
                        job['attempt_id'] != attempt_id or attempt['lease_fence'] != fence or
                        job['lease_fence'] != fence or job['cancel_epoch'] != attempt['cancel_epoch'] or
                        attempt['job_binding'] != wire_job(job)):
                        raise Denied('EGRESS_ATTEMPT_BINDING_CONFLICT')
                    if job['route'] != 'model' or job['disposition'] != 'QUEUED':
                        raise Denied('EGRESS_JOB_NOT_ELIGIBLE')
                    context = tx.get('contexts', job['context_id'])
                    if not context:
                        raise ValueError('missing sealed context')
                    actual_digest = digest({k: v for k, v in context.items() if k != 'context_digest'})
                    if context_digest != actual_digest or context_digest != context['context_digest'] or context_digest != attempt.get('context_digest'):
                        raise Denied('EGRESS_CONTEXT_MISMATCH')
                    checked = auth.check_current(tx, context['authority_vector'], phase='egress')
                    vector_digest = digest(checked['vector'])
                    if vector_digest != attempt.get('authority_vector_digest'):
                        raise Denied('EGRESS_VECTOR_MISMATCH')
                    snapshot = self.model_gate()
                    if not snapshot:
                        gate_path = self.store.runtime_dir / 'model' / 'model-gate.json'
                        # Missing/explicitly closed gate is known denial. Corrupt
                        # enabled gate state is uncertainty and still sends nothing.
                        if gate_path.exists():
                            gate = json.loads(gate_path.read_text(encoding='utf-8'))
                            if gate.get('enabled') is True:
                                expires = datetime.fromisoformat(gate['expires_utc'].replace('Z', '+00:00')).timestamp()
                                if expires > self.store.clock():
                                    raise ValueError('enabled gate invalid')
                        raise Denied('MODEL_GATE_CLOSED')
                    gate = snapshot['gate']
                    slot = gate.get('slots', {}).get(attempt['allocation_token'])
                    if (snapshot['model_gate_sha256'] != attempt.get('model_gate_sha256') or
                        {**gate['identity'], 'inference_authorized': True} != attempt['model_identity'] or
                        not slot or slot['allocation'] != attempt.get('model_allocation') or
                        os.environ.get('HAVEN_MODEL_ALLOCATION', 'readiness') != attempt.get('model_allocation')):
                        raise Denied('EGRESS_GATE_BINDING_CONFLICT')
                    now = self.store.clock()
                    session = tx.get('sessions', job['session_id'])
                    expiry = min([now + 1.0, job['deadline_utc'], session['expires_at'],
                        datetime.fromisoformat(gate['expires_utc'].replace('Z', '+00:00')).timestamp()] +
                        [g['expires_at'] for g in checked['grants'].values()])
                    if expiry <= now:
                        raise Denied('EGRESS_EXPIRED')
                    response.update(decision='AUTHORIZED', reason='OK', checked_at=now, valid_until=expiry,
                        authority_vector_digest=vector_digest, model_gate_sha256=snapshot['model_gate_sha256'])
                    vector_ref = job['context_id']
                except Denied as error:
                    response.update(decision='DENIED', reason=error.code, checked_at=self.store.clock())
                except (ValueError, KeyError, TypeError, OSError):
                    response.update(decision='UNKNOWN', reason='EGRESS_STATE_UNKNOWN', checked_at=self.store.clock())
                decision_id = uid('egress')
                response['decision_id'] = decision_id
                tx.put('events', decision_id, {'id': decision_id, 'event_id': decision_id,
                    'kind': 'EGRESS_DECISION', **response, 'vector_ref': vector_ref,
                    'event_digest': digest(response), 'at': self.store.clock()})
            return response
        except UnknownCommit:
            return {**empty, 'reason': 'EGRESS_COMMIT_UNKNOWN'}
        except Exception:
            return empty

    async def on_event(self, event):
        with self.store.transaction(operation='event') as tx:
            event_id = event.get('event_id')
            required = {'event_id', 'job_id', 'request_id', 'attempt_id', 'lease_fence', 'cancel_epoch',
                'worker_instance_id', 'pid', 'process_birth', 'boot_id', 'nonce', 'kind', 'observed_at', 'evidence'}
            if not required <= set(event) or not event_id or len(canonical(event).encode()) > LIMITS['metadata_bytes']:
                raise Denied('INVALID_EVENT')
            identity_valid = all(isinstance(event[k], str) and 0 < len(event[k]) <= 256 for k in
                ('event_id', 'job_id', 'request_id', 'attempt_id', 'worker_instance_id', 'boot_id', 'nonce', 'kind', 'observed_at'))
            identity_valid = identity_valid and all(type(event[k]) is int and event[k] >= 1 for k in ('lease_fence', 'cancel_epoch'))
            pid, birth = event['pid'], event['process_birth']
            valid_birth = ((type(birth) in (int, float) and math.isfinite(birth) and birth > 0) or
                           (isinstance(birth, str) and birth.isascii() and birth.isdigit() and 0 < len(birth) <= 32 and int(birth) > 0))
            identity_valid = identity_valid and ((pid is None and birth is None) or
                (type(pid) is int and pid > 0 and valid_birth))
            if not isinstance(event['evidence'], dict):
                identity_valid = False
            old = tx.get('events', event_id)
            if old:
                if old['event_digest'] != digest(event):
                    conflict = uid('event_conflict')
                    tx.put('events', conflict, {'id': conflict, 'kind': 'CONFLICTING_EVENT', 'event_id': event_id,
                        'job_id': event.get('job_id'), 'event_digest': digest(event), 'at': self.store.clock()})
                return
            job = tx.get('jobs', event.get('job_id'))
            matched = bool(identity_valid and job and all(event.get(k) == job[k] for k in ('request_id', 'attempt_id', 'lease_fence', 'cancel_epoch')))
            attempt = tx.get('attempts', event['attempt_id'])
            attempt_matched = bool(identity_valid and attempt and all(event[k] == attempt['job_binding'][k]
                for k in ('job_id', 'request_id', 'attempt_id', 'lease_fence', 'cancel_epoch')))
            execution = {k: event.get(k) for k in ('worker_instance_id', 'pid', 'process_birth', 'boot_id', 'nonce')}
            if matched and job.get('execution_identity'):
                previous = job['execution_identity']
                matched = all(previous[k] == execution[k] for k in ('worker_instance_id', 'boot_id', 'nonce'))
                if previous.get('pid') is not None:
                    matched = matched and previous == execution
            evidence = event['evidence'] if isinstance(event['evidence'], dict) else {}
            terminal = event['kind'] == 'ATTEMPT_TERMINAL'
            terminal_keys = {'job_disposition', 'reason', 'result_disposition', 'context_digest', 'claim_id',
                'admission_decision', 'egress_decision_id', 'cleanup_confirmed', 'usage'}
            schema_valid = valid_runtime_usage(evidence.get('usage'))
            if terminal:
                schema_valid = schema_valid and terminal_keys <= set(evidence)
                schema_valid = schema_valid and evidence.get('job_disposition') in ('SUCCEEDED', 'FAILED', 'CANCELLED', 'INCONCLUSIVE')
                schema_valid = schema_valid and evidence.get('result_disposition') in ('RELEASE_ADMITTED', 'FENCED', 'REJECTED', 'UNKNOWN', 'NOT_PRODUCED')
                schema_valid = schema_valid and evidence.get('admission_decision') in ('ADMITTED', 'DENIED', 'UNKNOWN', 'NOT_REQUESTED')
                schema_valid = schema_valid and (evidence.get('cleanup_confirmed') is None or type(evidence.get('cleanup_confirmed')) is bool)
                schema_valid = schema_valid and isinstance(evidence.get('reason'), str) and 0 < len(evidence['reason']) <= 160
                schema_valid = schema_valid and all(evidence.get(k) is None or (isinstance(evidence[k], str) and 0 < len(evidence[k]) <= 256)
                    for k in ('context_digest', 'claim_id', 'egress_decision_id'))
                if job and evidence.get('context_digest') is not None:
                    sealed = tx.get('contexts', job['context_id'])
                    schema_valid = schema_valid and bool(sealed and evidence['context_digest'] == sealed['context_digest'])
            tx.put('events', event_id, {'id': event_id, **event, 'event_digest': digest(event),
                'binding_valid': matched, 'attempt_binding_valid': attempt_matched, 'evidence_valid': schema_valid})
            if not matched or not schema_valid:
                return
            job['execution_identity'] = execution
            kind = event['kind']
            if kind == 'PROCESS_STARTED' and job['compute_state'] == 'NOT_STARTED':
                job['compute_state'] = 'RUNNING'
            elif kind == 'STOP_REQUESTED' and job['compute_state'] != 'STOP_CONFIRMED':
                job['compute_state'] = 'STOP_REQUESTED'
            elif kind == 'STOP_CONFIRMED' and event.get('evidence', {}).get('confirmed') is True:
                job['compute_state'] = 'STOP_CONFIRMED'
            elif kind == 'UNKNOWN' and job['compute_state'] != 'STOP_CONFIRMED':
                job['compute_state'] = 'UNKNOWN'
            if terminal and job['disposition'] == 'QUEUED':
                disposition = evidence['job_disposition']
                if disposition != 'CANCELLED' and (evidence['admission_decision'] == 'UNKNOWN' or
                    evidence['result_disposition'] == 'UNKNOWN' or evidence['cleanup_confirmed'] is False):
                    disposition = 'INCONCLUSIVE'
                if disposition == 'SUCCEEDED':
                    # Runtime cannot invent APP's committed release history.
                    receipt = tx.get('release_receipts', job['release_id']) if job.get('release_id') else None
                    if not receipt or evidence['result_disposition'] != 'RELEASE_ADMITTED':
                        disposition = 'INCONCLUSIVE'
                job.update(disposition=disposition, error=evidence['reason'], terminal_event_id=event_id)
            tx.put('jobs', job['job_id'], job)

    async def on_result(self, result):
        job_id = result.get('job_id')
        try:
            with self.store.transaction(operation='release:' + str(job_id)) as tx:
                job = tx.get('jobs', job_id)
                if not job:
                    raise Denied('JOB_UNAVAILABLE', 404)
                if result.get('request_id') != job['request_id']:
                    raise Denied('REQUEST_IDENTITY_CONFLICT')
                if job['disposition'] != 'QUEUED' and not job.get('output_id'):
                    raise Denied('JOB_ALREADY_SETTLED')
                admitted_attempt = tx.get('attempts', job['attempt_id'])
                if not admitted_attempt or admitted_attempt['lease_fence'] != job['lease_fence']:
                    raise Denied('ATTEMPT_NOT_ADMITTED')
                if job['route'] == 'model':
                    identity = job.get('execution_identity')
                    if not identity or any(result.get(k) != v for k, v in identity.items()):
                        raise Denied('EXECUTION_IDENTITY_CONFLICT')
                    attempt = tx.get('attempts', job['attempt_id'])
                    if result.get('model_identity') != attempt['model_identity']:
                        raise Denied('MODEL_IDENTITY_CONFLICT')
                response = auth.authorize_release(tx, result, release_key='job:' + job_id,
                    request_digest=digest([job['request_digest'], result['output_digest'], result['context_digest'], result['source_refs']]))
            return response
        except UnknownCommit:
            with self.store.transaction(operation='release-unknown-observation') as tx:
                event_id = uid('release_unknown')
                tx.put('events', event_id, {'id': event_id, 'job_id': job_id, 'kind': 'RELEASE_UNKNOWN',
                    'at': self.store.clock(), 'output_digest': result.get('output_digest'),
                    'reason': 'Commit acknowledgement lost; reconcile exact release key, never resend from this callback.'})
            return {'disposition': 'UNKNOWN', 'reason': 'RELEASE_UNKNOWN'}
        except Denied as error:
            with self.store.transaction(operation='result-rejected') as tx:
                event_id = uid('result')
                tx.put('events', event_id, {'id': event_id, 'job_id': job_id, 'kind': 'RESULT_REJECTED',
                    'reason': error.code, 'at': self.store.clock(), 'output_digest': result.get('output_digest')})
                job = tx.get('jobs', job_id)
                if job and job['disposition'] == 'QUEUED':
                    job.update(disposition='FAILED', error=error.code)
                    tx.put('jobs', job_id, job)
            return {'disposition': 'FENCED', 'reason': error.code}

    async def deterministic(self, job_id):
        await asyncio.sleep(0.03)
        with self.store.transaction(write=False) as tx:
            job = tx.get('jobs', job_id)
        admitted = await self.admit_attempt(job_id, job['attempt_id'], job['lease_fence'])
        if admitted['decision'] != 'ADMITTED':
            with self.store.transaction(operation='deterministic-denied') as tx:
                current = tx.get('jobs', job_id)
                if current['disposition'] == 'QUEUED':
                    current.update(disposition='INCONCLUSIVE' if admitted['decision'] == 'UNKNOWN' else 'FAILED',
                                   error=admitted.get('reason', 'ADMISSION_UNKNOWN'))
                    tx.put('jobs', job_id, current)
            return
        await asyncio.sleep(0)
        payload = auth.deterministic_payload(admitted['context'])
        result = {**job, 'payload': payload, 'output_digest': digest(payload),
                  'context_digest': digest(admitted['context']), 'source_refs': payload['source_refs'],
                  'model_identity': None, 'certainty': 'DETERMINISTIC_EXCERPTS', 'outcome': 'COMPLETED', 'usage': {'model_calls': 0}}
        await self.on_result(result)

    async def submit(self, job):
        if job['route'] == 'deterministic':
            task = asyncio.create_task(self.deterministic(job['job_id']))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        elif self.supervisor:
            try:
                await self.supervisor.submit(wire_job(job))
            except Exception:
                with self.store.transaction(operation='submit-unknown') as tx:
                    current = tx.get('jobs', job['job_id'])
                    current.update(disposition='INCONCLUSIVE', error='RUNTIME_SUBMIT_UNKNOWN')
                    tx.put('jobs', job['job_id'], current)


def create_app(*, runtime_dir=None, supervisor_factory=None) -> FastAPI:
    root = runtime_path(runtime_dir)

    @asynccontextmanager
    async def lifespan(app):
        store = Store(root)
        service = ApplicationService(store)
        app.state.store, app.state.service = store, service
        factory = supervisor_factory
        if factory is None:
            try:
                factory = importlib.import_module('.supervisor', __package__).Supervisor
            except ImportError:
                factory = None
        if factory:
            try:
                service.supervisor = factory(runtime_dir=root, admit_attempt=service.admit_attempt,
                                             authorize_egress=service.authorize_egress,
                                             on_event=service.on_event, on_result=service.on_result)
                await service.supervisor.start()
                service.runtime_status = 'AVAILABLE'
            except Exception:
                service.runtime_status = 'UNAVAILABLE_START_FAILED'
                if service.supervisor:
                    try:
                        await service.supervisor.close(time.monotonic() + 5)
                    except Exception:
                        pass
                service.supervisor = None
        try:
            yield
        finally:
            for task in list(service.tasks):
                task.cancel()
            await asyncio.gather(*service.tasks, return_exceptions=True)
            if service.supervisor:
                app.state.shutdown_receipt = await service.supervisor.close(time.monotonic() + 10)
            store.close()

    app = FastAPI(title='Haven · local laboratory', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    templates = Jinja2Templates(directory=HERE / 'templates')
    app.mount('/static', StaticFiles(directory=HERE / 'static'), name='static')

    @app.middleware('http')
    async def guards(request, call_next):
        host = request.headers.get('host', '')
        if host not in ALLOWED_HOSTS:
            return JSONResponse({'code': 'HOST_DENIED', 'message': 'Use the assigned loopback address.'}, status_code=403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if request.headers.get('origin') != 'http://' + host:
                return JSONResponse({'code': 'ORIGIN_DENIED', 'message': 'This action requires the same local origin.'}, status_code=403)
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_REQUEST:
                    return JSONResponse({'code': 'REQUEST_LIMIT', 'message': 'The upload is too large.'}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    @app.exception_handler(Denied)
    async def denied_handler(request, error):
        return JSONResponse({'code': error.code, 'message': error.message, 'operation_id': error.operation_id,
                             'retryable': False}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request, error):
        return JSONResponse({'code': 'INVALID_INPUT', 'message': 'Check required fields, revisions, and supported values.',
                             'fields': [str(e['loc'][-1]) for e in error.errors()]}, status_code=422)

    def get_session(tx, request, *, write=False, bootstrap=False):
        token = request.cookies.get(COOKIE, '')
        session = tx.get('sessions', raw_digest(token.encode())) if token else None
        session = auth.active_session(tx, session, permit_bootstrap=bootstrap)
        if write and not secrets.compare_digest(request.headers.get('x-csrf-token', ''), session['csrf']):
            raise Denied('CSRF_DENIED', 403, 'The form session changed. Refresh and try again.')
        return session

    def create_session(tx, person=None):
        token = secrets.token_urlsafe(32)
        sid = raw_digest(token.encode())
        session = {'id': sid, 'person': person, 'csrf': secrets.token_urlsafe(32), 'active': True,
            'expires_at': tx.store.clock() + 8 * 3600, 'device_ref': uid('device'), 'device_epoch': 1,
            'destination_ref': uid('destination'), 'destination_epoch': 1,
            'authority_instance_epoch': tx.meta('authority_instance_epoch')}
        tx.put('sessions', sid, session, insert=True)
        return token, session

    def session_view(tx, session):
        return {'person': session['person'], 'csrf_token': session['csrf'], 'destination_ref': session['destination_ref'],
                'demo': True, 'review_only': tx.meta('review_only'), 'continuity': app.state.store.continuity_status,
                'model_available': bool(app.state.service.model_gate() and app.state.service.supervisor),
                'runtime_status': app.state.service.runtime_status}

    def set_cookie(response, token):
        response.set_cookie(COOKIE, token, httponly=True, samesite='strict', secure=False, max_age=8 * 3600, path='/')

    def bootstrap_session(tx, request):
        try:
            return None, get_session(tx, request, bootstrap=True)
        except Denied:
            return create_session(tx)

    def owner_source(tx, session, sid):
        source = tx.get('sources', sid)
        if not source or source['owner'] != session['person'] or source['tombstone']:
            raise Denied('SOURCE_UNAVAILABLE', 404)
        return source

    def source_view(tx, source, session):
        grants = []
        if source['owner'] == session['person']:
            for grant in tx.all('grants'):
                if grant['source_id'] == source['id']:
                    charged = tx.get('quota_ledger', grant['id'])['charged_units']
                    grants.append({k: grant[k] for k in ('id', 'recipient', 'expires_at', 'max_uses', 'status', 'authorization_revision')} |
                                  {'charged_units': charged, 'remaining': None if grant['max_uses'] is None else grant['max_uses'] - charged})
        return {k: source[k] for k in ('id', 'revision', 'title', 'text', 'kind', 'owner', 'updated_at')} | {
            'note_id': source['id'], 'owned': source['owner'] == session['person'], 'grants': grants,
            'image': source.get('image'), 'parents': source['parents']}

    def commit_change(tx, session, kind, target):
        receipt = {'id': uid('change'), 'actor': session['person'], 'kind': kind, 'target': target,
                   'sequence': tx.sequence, 'at': tx.store.clock()}
        tx.put('changes', receipt['id'], receipt)
        return receipt

    @app.get('/healthz')
    async def healthz():
        return {'service': 'haven-ip01', 'ready': True, 'stage': 'stateful', 'model_available': bool(app.state.service.model_gate() and app.state.service.supervisor)}

    @app.get('/')
    async def home(request: Request):
        with app.state.store.transaction(operation='bootstrap') as tx:
            token, session = bootstrap_session(tx, request)
            view = session_view(tx, session)
        response = templates.TemplateResponse(request=request, name='index.html', context={'session': view})
        if token:
            set_cookie(response, token)
        return response

    @app.get('/api/session')
    async def session_status(request: Request):
        with app.state.store.transaction(operation='bootstrap') as tx:
            token, session = bootstrap_session(tx, request)
            view = session_view(tx, session)
        response = JSONResponse(view)
        if token:
            set_cookie(response, token)
        return response

    @app.post('/api/session')
    async def login(request: Request, body: SessionRequest):
        with app.state.store.transaction(operation='demo-login') as tx:
            old = get_session(tx, request, write=True, bootstrap=True)
            old['active'] = False
            tx.put('sessions', old['id'], old)
            token, session = create_session(tx, body.person)
            view = session_view(tx, session)
        response = JSONResponse(view)
        set_cookie(response, token)
        return response

    @app.get('/api/notes')
    async def notes(request: Request):
        with app.state.store.transaction(write=False) as tx:
            session = get_session(tx, request)
            result = []
            for source in tx.all('sources'):
                if source['tombstone']:
                    continue
                try:
                    auth.resolve_closure(tx, session['person'], [source['id']])
                except Denied:
                    continue
                result.append(source_view(tx, source, session))
        return {'notes': result}

    @app.post('/api/notes', status_code=201)
    async def create_note(request: Request, body: NoteRequest):
        data = body.model_dump()
        with app.state.store.transaction(operation=body.idempotency_key) as tx:
            session = get_session(tx, request, write=True)
            auth.live(tx)
            old = tx.remember(session['person'], 'note', body.idempotency_key, data)
            if old:
                return old
            auth.resolve_closure(tx, session['person'], body.parents)
            sid = uid('source')
            source = {'id': sid, 'owner': session['person'], 'kind': 'note', 'title': body.title, 'text': body.text,
                'revision': 1, 'lineage_epoch': 1, 'authenticity_epoch': 1, 'sha256': raw_digest(body.text.encode()),
                'parents': [{'id': p, 'revision': tx.get('sources', p)['revision']} for p in sorted(set(body.parents))],
                'tombstone': False, 'updated_at': tx.store.clock(), 'claim_class': 'SYNTHETIC_USER_NOTE'}
            tx.put('sources', sid, source, insert=True)
            auth.resolve_closure(tx, session['person'], [sid])
            tx.put('source_revisions', sid + ':1', source)
            result = {'note_id': sid, 'revision': 1, 'commit_receipt': commit_change(tx, session, 'NOTE_CREATED', sid)}
            tx.remember(session['person'], 'note', body.idempotency_key, data, result)
        return result

    @app.patch('/api/notes/{sid}')
    async def edit_note(sid: str, request: Request, body: NoteEdit):
        with app.state.store.transaction(operation='edit-note') as tx:
            session = get_session(tx, request, write=True)
            auth.live(tx)
            source = owner_source(tx, session, sid)
            if source['kind'] != 'note':
                raise Denied('UNSUPPORTED_SOURCE_EDIT', 422)
            if source['revision'] != body.expected_revision:
                raise Denied('REVISION_CONFLICT')
            parents = [p['id'] for p in source['parents']] if body.parents is None else body.parents
            if sid in parents:
                raise Denied('LINEAGE_CYCLE')
            auth.resolve_closure(tx, session['person'], parents)
            source.update(title=body.title, text=body.text, revision=source['revision'] + 1,
                lineage_epoch=source['lineage_epoch'] + 1, sha256=raw_digest(body.text.encode()), updated_at=tx.store.clock(),
                parents=[{'id': p, 'revision': tx.get('sources', p)['revision']} for p in sorted(set(parents))])
            tx.put('sources', sid, source)
            auth.resolve_closure(tx, session['person'], [sid])
            tx.put('source_revisions', sid + ':' + str(source['revision']), source)
            receipt = commit_change(tx, session, 'NOTE_CORRECTED_DEPENDENTS_FENCED', sid)
        return {'note_id': sid, 'revision': source['revision'], 'commit_receipt': receipt}

    @app.delete('/api/notes/{sid}')
    async def delete_note(sid: str, request: Request, body: RevisionRequest):
        with app.state.store.transaction(operation='tombstone-note') as tx:
            session = get_session(tx, request, write=True)
            auth.live(tx)
            source = owner_source(tx, session, sid)
            if source['revision'] != body.expected_revision:
                raise Denied('REVISION_CONFLICT')
            source.update(tombstone=True, revision=source['revision'] + 1, lineage_epoch=source['lineage_epoch'] + 1,
                          updated_at=tx.store.clock())
            tx.put('sources', sid, source)
            tx.put('source_revisions', sid + ':' + str(source['revision']), source)
            receipt = commit_change(tx, session, 'SOURCE_TOMBSTONED', sid)
        return {'note_id': sid, 'revision': source['revision'], 'status': 'INACCESSIBLE', 'erasure': 'NOT_VERIFIED', 'commit_receipt': receipt}

    @app.post('/api/notes/{sid}/grants', status_code=201)
    async def grant_note(sid: str, request: Request, body: GrantRequest):
        data = body.model_dump(mode='json')
        with app.state.store.transaction(operation=body.idempotency_key) as tx:
            session = get_session(tx, request, write=True)
            auth.live(tx)
            owner_source(tx, session, sid)
            old = tx.remember(session['person'], 'grant:' + sid, body.idempotency_key, data)
            if old:
                return old
            if body.recipient == session['person'] or not tx.store.clock() < body.expires_at.timestamp() <= tx.store.clock() + 30 * 86400:
                raise Denied('INVALID_GRANT_SCOPE_OR_EXPIRY', 422)
            gid = uid('grant')
            grant = {'id': gid, 'source_id': sid, 'issuer': session['person'], 'recipient': body.recipient,
                'purpose': body.purpose, 'expires_at': body.expires_at.timestamp(), 'not_before': tx.store.clock(),
                'max_uses': body.max_uses, 'profile': body.profile, 'authorization_revision': 1, 'revocation_epoch': 1,
                'authority_instance_epoch': tx.meta('authority_instance_epoch'), 'status': 'ACTIVE',
                'approval_receipt': commit_change(tx, session, 'SHARING_APPROVED', sid)['id']}
            tx.put('grants', gid, grant, insert=True)
            tx.put('quota_ledger', gid, {'id': gid, 'charged_units': 0, 'accounting_sequence': 0}, insert=True)
            result = {'grant_id': gid, 'authorization_revision': 1, 'profile': body.profile}
            tx.remember(session['person'], 'grant:' + sid, body.idempotency_key, data, result)
        return result

    @app.post('/api/grants/{gid}/revoke')
    async def revoke_grant(gid: str, request: Request, body: RevisionRequest):
        with app.state.store.transaction(operation='revoke') as tx:
            session = get_session(tx, request, write=True)
            auth.live(tx)
            grant = tx.get('grants', gid)
            if not grant or grant['issuer'] != session['person']:
                raise Denied('GRANT_UNAVAILABLE', 404)
            if grant['authorization_revision'] != body.expected_revision:
                raise Denied('REVISION_CONFLICT')
            grant.update(status='REVOKED', authorization_revision=grant['authorization_revision'] + 1,
                         revocation_epoch=grant['revocation_epoch'] + 1)
            tx.put('grants', gid, grant)
            receipt = commit_change(tx, session, 'GRANT_REVOKED', gid)
        return {'grant_id': gid, 'authorization_revision': grant['authorization_revision'], 'commit_receipt': receipt}

    @app.get('/api/drafts')
    async def drafts(request: Request):
        with app.state.store.transaction(write=False) as tx:
            session = get_session(tx, request)
            rows = [d for d in tx.all('drafts') if d['owner'] == session['person']]
        return {'drafts': rows}

    @app.post('/api/drafts', status_code=201)
    async def create_draft(request: Request, body: DraftRequest):
        with app.state.store.transaction(operation=body.idempotency_key) as tx:
            session = get_session(tx, request, write=True)
            auth.live(tx)
            old = tx.remember(session['person'], 'draft', body.idempotency_key, body.model_dump())
            if old:
                return old
            did = uid('draft')
            row = {'id': did, 'owner': session['person'], 'kind': body.kind, 'text': body.text,
                   'revision': 1, 'done': False, 'dispatch': 'LOCAL_ONLY', 'updated_at': tx.store.clock()}
            tx.put('drafts', did, row, insert=True)
            tx.remember(session['person'], 'draft', body.idempotency_key, body.model_dump(), row)
        return row

    @app.patch('/api/drafts/{did}')
    async def edit_draft(did: str, request: Request, body: DraftEdit):
        with app.state.store.transaction(operation='edit-draft') as tx:
            session = get_session(tx, request, write=True)
            auth.live(tx)
            row = tx.get('drafts', did)
            if not row or row['owner'] != session['person']:
                raise Denied('DRAFT_UNAVAILABLE', 404)
            if row['revision'] != body.expected_revision:
                raise Denied('REVISION_CONFLICT')
            row.update(text=body.text, done=body.done, revision=row['revision'] + 1, updated_at=tx.store.clock())
            tx.put('drafts', did, row)
        return row

    @app.post('/api/images', status_code=201)
    async def import_image(request: Request):
        with app.state.store.transaction(write=False) as tx:
            get_session(tx, request, write=True)
            auth.live(tx)
        content_type = request.headers.get('content-type', '').split(';')[0]
        if content_type == 'multipart/form-data':
            form = await request.form(max_files=1, max_fields=2, max_part_size=2 * 1024 * 1024)
            file = form.get('file') or form.get('image')
            if not file or not hasattr(file, 'read'):
                raise Denied('IMAGE_REQUIRED', 422)
            raw = await file.read(2 * 1024 * 1024 + 1)
            content_type = file.content_type
        else:
            raw = await request.body()
        if not raw or len(raw) > 2 * 1024 * 1024:
            raise Denied('IMAGE_BYTE_LIMIT', 413)
        if content_type not in ('image/png', 'image/jpeg'):
            raise Denied('UNSUPPORTED_IMAGE', 422)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                probe = Image.open(io.BytesIO(raw))
                if probe.format != {'image/png': 'PNG', 'image/jpeg': 'JPEG'}[content_type] or getattr(probe, 'n_frames', 1) != 1:
                    raise ValueError('format or frames')
                width, height = probe.size
                if width * height > 8_000_000:
                    raise Denied('IMAGE_PIXEL_LIMIT', 413)
                probe.verify()
                decoded = Image.open(io.BytesIO(raw))
                decoded.load()
                clean = Image.new('RGB', decoded.size)
                clean.paste(decoded.convert('RGB'))
                output = io.BytesIO()
                clean.save(output, format='PNG')
                derivative = output.getvalue()
        except Denied:
            raise
        except (ValueError, OSError, SyntaxError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise Denied('INVALID_IMAGE', 422, 'Upload a valid, single-frame PNG or JPEG.') from error
        if len(derivative) > 8 * 1024 * 1024:
            raise Denied('IMAGE_DERIVATIVE_LIMIT', 413)
        sid = uid('source')
        image_info = {'raw_sha256': raw_digest(raw), 'derivative_sha256': raw_digest(derivative), 'width': width,
                      'height': height, 'preprocessing': 'PIL_DECODE_RGB_METADATA_STRIPPED_PNG.v1',
                      'media_type': content_type, 'derivative_bytes': len(derivative)}
        media = root / 'media'
        media.mkdir(exist_ok=True)
        (media / (sid + '.png')).write_bytes(derivative)
        try:
            with app.state.store.transaction(operation='image-import') as tx:
                session = get_session(tx, request, write=True)
                auth.live(tx)
                source = {'id': sid, 'owner': session['person'], 'kind': 'image', 'title': 'Imported synthetic image',
                    'text': '', 'revision': 1, 'lineage_epoch': 1, 'authenticity_epoch': 1,
                    'sha256': raw_digest(raw), 'parents': [], 'tombstone': False, 'updated_at': tx.store.clock(),
                    'image': image_info, 'claim_class': 'SYNTHETIC_UPLOADED_IMAGE'}
                tx.put('sources', sid, source, insert=True)
                tx.put('source_revisions', sid + ':1', source)
                receipt = commit_change(tx, session, 'IMAGE_IMPORTED', sid)
        except UnknownCommit:
            raise
        except Exception:
            (media / (sid + '.png')).unlink(missing_ok=True)
            raise
        return {'source_id': sid, 'revision': 1, 'preprocessing_identity': image_info, 'commit_receipt': receipt}

    @app.get('/api/images/{sid}/content')
    async def image_content(sid: str, request: Request):
        with app.state.store.transaction(write=False) as tx:
            session = get_session(tx, request)
            sources, _, _ = auth.resolve_closure(tx, session['person'], [sid])
            if sources[sid]['kind'] != 'image':
                raise Denied('SOURCE_UNAVAILABLE', 404)
            content = (root / 'media' / (sid + '.png')).read_bytes()
            if raw_digest(content) != sources[sid]['image']['derivative_sha256']:
                raise Denied('IMAGE_INTEGRITY_FAILED')
        return Response(content, media_type='image/png')

    @app.post('/api/answers', status_code=202)
    async def answer(request: Request, body: AnswerRequest):
        data = body.model_dump()
        service = app.state.service
        with app.state.store.transaction(operation=body.idempotency_key) as tx:
            session = get_session(tx, request, write=True)
            auth.live(tx)
            if body.destination_ref != session['destination_ref']:
                raise Denied('DESTINATION_CONFLICT')
            old = tx.remember(session['person'], 'answer', body.idempotency_key, data)
            if old:
                return old
            if body.route == 'model' and not (service.model_gate() and service.supervisor):
                raise Denied('MODEL_UNAVAILABLE', 503, 'The local model route has not passed its runtime and allocation gate. Use deterministic excerpts.')
            if sum(j['disposition'] == 'QUEUED' for j in tx.all('jobs')) >= 32:
                raise Denied('QUEUE_FULL', 503)
            jid = uid('job')
            job = {'job_id': jid, 'request_id': uid('request'), 'request_digest': digest(data), 'request': data,
                'owner': session['person'], 'session_id': session['id'], 'route': body.route, 'attempt_id': uid('attempt'),
                'lease_fence': 1, 'cancel_epoch': 1, 'deadline_utc': tx.store.clock() + 120,
                'max_elapsed_ms': 120000, 'reservation_id': uid('reservation'), 'created_at': tx.store.clock(),
                'disposition': 'QUEUED', 'compute_state': 'NOT_STARTED', 'output_id': None, 'release_id': None,
                'error': None, 'context_id': uid('context'), 'execution_identity': None,
                'execution_mode': 'IN_PROCESS_DETERMINISTIC' if body.route == 'deterministic' else 'OWNED_WORKER'}
            tx.put('jobs', jid, job, insert=True)
            context = auth.build_context(tx, session, {**data, 'job_id': jid})
            tx.put('contexts', job['context_id'], context)
            result = {'job_id': jid, 'status_url': '/api/jobs/' + jid, 'disposition': 'QUEUED'}
            tx.remember(session['person'], 'answer', body.idempotency_key, data, result)
        await service.submit(job)
        return result

    def job_view(tx, session, job):
        if not job or job['owner'] != session['person']:
            raise Denied('JOB_UNAVAILABLE', 404)
        view = {k: job[k] for k in ('job_id', 'route', 'disposition', 'compute_state', 'created_at', 'error', 'execution_mode', 'cancel_epoch', 'lease_fence')}
        view['question'] = job['request']['question']
        view['sources'] = []
        view['timeline'] = [{'kind': 'QUEUED', 'at': job['created_at']}] + [
            {k: event.get(k) for k in ('kind', 'observed_at', 'reason')} for event in tx.all('events') if event.get('job_id') == job['job_id']]
        context = tx.get('contexts', job['context_id'])
        try:
            current = auth.check_current(tx, context['authority_vector'], phase='status')
            view['sources'] = [{'id': s['id'], 'revision': s['revision'], 'title': s['title'], 'kind': s['kind']} for s in current['sources'].values()]
            view['source_eligibility'] = 'CURRENT'
        except Denied as error:
            view['source_eligibility'] = 'UNAVAILABLE'
            view['eligibility_reason'] = error.code
        if job['output_id']:
            output = tx.get('outputs', job['output_id'])
            view['output'] = {k: output[k] for k in ('output_id', 'release_id', 'output_digest', 'nonce', 'destination_ref', 'expires_at')}
            view['output']['consumed'] = bool(output['consumption_id'])
            view['output']['message'] = 'Previously consumed; reload does not replay this answer.' if output['consumption_id'] else 'Ready for an explicit, current-authority consume check.'
        return view

    @app.get('/api/jobs')
    async def jobs(request: Request):
        with app.state.store.transaction(write=False) as tx:
            session = get_session(tx, request)
            rows = [job_view(tx, session, j) for j in reversed(tx.all('jobs')) if j['owner'] == session['person']]
        return {'jobs': rows}

    @app.get('/api/jobs/{jid}')
    async def job_status(jid: str, request: Request):
        with app.state.store.transaction(write=False) as tx:
            session = get_session(tx, request)
            view = job_view(tx, session, tx.get('jobs', jid))
        return view

    @app.post('/api/jobs/{jid}/cancel')
    async def cancel(jid: str, request: Request):
        with app.state.store.transaction(operation='cancel:' + jid) as tx:
            session = get_session(tx, request, write=True)
            job = tx.get('jobs', jid)
            job_view(tx, session, job)
            if job['disposition'] != 'CANCELLED':
                job['cancel_epoch'] += 1
                job['disposition'] = 'CANCELLED'
                if job['compute_state'] in ('RUNNING', 'UNKNOWN'):
                    job['compute_state'] = 'STOP_REQUESTED'
                tx.put('jobs', jid, job)
                commit_change(tx, session, 'JOB_CANCELLED_FUTURE_OUTPUT_FENCED', jid)
        runtime = None
        if job['route'] == 'model' and app.state.service.supervisor:
            try:
                runtime = await app.state.service.supervisor.cancel(jid, job['cancel_epoch'], 'User requested cancellation')
            except Exception:
                runtime = {'compute_state': 'UNKNOWN', 'reason': 'STOP_REQUEST_UNCONFIRMED'}
        return {'job_id': jid, 'disposition': 'CANCELLED', 'cancel_epoch': job['cancel_epoch'],
                'compute_state': (runtime or job)['compute_state'], 'runtime': runtime,
                'message': 'Future output is fenced. Previous consumption and delivery history are retained.'}

    @app.post('/api/outputs/{oid}/consume')
    async def consume(oid: str, request: Request, body: ConsumeRequest):
        try:
            with app.state.store.transaction(operation='consume:' + oid) as tx:
                session = get_session(tx, request, write=True)
                result = auth.consume_output(tx, session, {'output_id': oid, **body.model_dump()})
        except UnknownCommit:
            with app.state.store.transaction(operation='consume-response-unknown-observation') as tx:
                output = tx.get('outputs', oid)
                if output:
                    event_id = uid('consume_unknown')
                    tx.put('events', event_id, {'id': event_id, 'job_id': output['job_id'],
                        'kind': 'CONSUMPTION_RESPONSE_UNKNOWN', 'output_id': oid, 'at': tx.store.clock(),
                        'reason': 'Slot may be consumed; reconcile history without replay.'})
            raise
        return JSONResponse(result, status_code=409 if result['status'] == 'DENIED' else 200)

    @app.get('/api/outputs/{oid}/receipts')
    async def output_receipts(oid: str, request: Request):
        with app.state.store.transaction(operation='eligibility-check') as tx:
            session = get_session(tx, request)
            result = auth.receipts(tx, session, oid)
        return result

    @app.post('/api/outputs/{oid}/observations', status_code=201)
    async def observation(oid: str, request: Request, body: ObservationRequest):
        with app.state.store.transaction(operation=body.idempotency_key) as tx:
            session = get_session(tx, request, write=True)
            output = auth.output_for_session(tx, session, oid)
            if session['id'] != output['session_id'] or any(getattr(body, k) != output[k] for k in ('release_id', 'output_digest', 'destination_ref', 'nonce', 'consumption_id')):
                raise Denied('OBSERVATION_BINDING_CONFLICT')
            old = tx.remember(session['person'], 'observation:' + oid, body.idempotency_key, body.model_dump())
            if old:
                return old
            consume_receipt = tx.get('consumption_receipts', output['consumption_id'])
            if not consume_receipt:
                raise Denied('CONSUMPTION_REQUIRED')
            rid = uid('observation')
            row = {**auth.binding(output), 'id': rid, 'consumption_id': output['consumption_id'],
                'consumption_sequence': consume_receipt['consumption_sequence'], 'kind': body.kind,
                'nonce': body.nonce, 'at': tx.store.clock(), 'reporter': session['id'],
                'authority_vector_digest': digest(output['vector']), 'human_perception_proven': False}
            tx.put('delivery_observations', rid, row)
            result = auth.public_receipt(row)
            tx.remember(session['person'], 'observation:' + oid, body.idempotency_key, body.model_dump(), result)
        return result

    return app
