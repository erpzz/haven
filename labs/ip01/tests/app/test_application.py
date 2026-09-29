"""Author development tests; independent QA and qualification remain separate."""
import asyncio
import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sqlite3
import time
import uuid
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from haven.app import create_app
from haven import authority
from haven.contracts import Denied, digest, canonical, AuthorityVector
from haven.store import Store

BASE = 'http://127.0.0.1:8767'


class Person:
    def __init__(self, client, person):
        self.client, self.cookies, self.csrf, self.destination = client, {}, '', ''
        r = self.call('GET', '/api/session')
        self.csrf = r.json()['csrf_token']
        r = self.call('POST', '/api/session', {'person': person})
        assert r.status_code == 200, r.text
        self.csrf, self.destination = r.json()['csrf_token'], r.json()['destination_ref']

    def call(self, method, url, data=None, **kwargs):
        self.client.cookies.clear()
        for name,value in self.cookies.items():
            self.client.cookies.set(name,value,domain='127.0.0.1',path='/')
        headers = {'Origin': BASE, 'X-CSRF-Token': self.csrf}
        headers.update(kwargs.pop('headers', {}))
        r = self.client.request(method, url, json=data, headers=headers, **kwargs)
        self.cookies = dict(self.client.cookies)
        return r

    def note(self, text='Pack water and a rain jacket for the lake walk.', title='Lake walk', parents=None):
        r = self.call('POST', '/api/notes', {'title': title, 'text': text, 'parents': parents or [], 'idempotency_key': uuid.uuid4().hex})
        assert r.status_code == 201, r.text
        return r.json()['note_id']

    def share(self, sid, uses=1, seconds=3600):
        r = self.call('POST', f'/api/notes/{sid}/grants', {'recipient': 'B', 'purpose': 'answer', 'max_uses': uses,
             'expires_at': datetime.fromtimestamp(time.time() + seconds, timezone.utc).isoformat(), 'idempotency_key': uuid.uuid4().hex})
        assert r.status_code == 201, r.text
        return r.json()['grant_id']

    def ask(self, sources=None, key=None, wait=True, **extra):
        data = {'question': 'What should I pack for the lake walk?', 'destination_ref': self.destination,
                'idempotency_key': key or uuid.uuid4().hex, **extra}
        if sources is not None:
            data['source_ids'] = sources
        r = self.call('POST', '/api/answers', data)
        assert r.status_code == 202, r.text
        jid = r.json()['job_id']
        if not wait:
            return jid
        for _ in range(100):
            job = self.call('GET', '/api/jobs/' + jid).json()
            if job['disposition'] != 'QUEUED':
                return job
            time.sleep(.02)
        raise AssertionError('job never settled')

    def consume(self, job, key='consume'):
        o = job['output']
        return self.call('POST', '/api/outputs/' + o['output_id'] + '/consume', {
            **{k: o[k] for k in ('release_id', 'output_digest', 'destination_ref', 'nonce')}, 'idempotency_key': key})


@pytest.fixture
def lab(tmp_path):
    app = create_app(runtime_dir=tmp_path)
    with TestClient(app, base_url=BASE) as c:
        yield app, c, Person(c, 'A'), Person(c, 'B')


def test_useful_private_shared_finite_once_history(lab):
    app, c, a, b = lab
    sid = a.note()
    assert b.call('GET', '/api/notes').json()['notes'] == []
    denied = b.call('POST', '/api/answers', {'question': 'walk', 'source_ids': [sid], 'destination_ref': b.destination, 'idempotency_key': 'denied'})
    assert denied.status_code == 404
    private = a.ask([sid])
    assert 'rain jacket' in a.consume(private).json()['payload']['text']
    gid = a.share(sid)
    job = b.ask([sid])
    assert job['disposition'] == 'SUCCEEDED'
    assert 'payload' not in canonical(job)
    with app.state.store.transaction(write=False) as tx:
        assert tx.get('quota_ledger', gid)['charged_units'] == 1
        assert tx.get('grants', gid)['authorization_revision'] == 1
    consumed = b.consume(job)
    assert consumed.status_code == 200 and 'rain jacket' in consumed.json()['payload']['text']
    duplicate = b.consume(job).json()
    assert duplicate['status'] == 'HISTORY_ONLY' and 'payload' not in duplicate
    assert b.consume(job, 'conflict').status_code == 409
    assert 'payload' not in b.call('GET', '/api/jobs/' + job['job_id']).text
    history = b.call('GET', '/api/outputs/' + job['output']['output_id'] + '/receipts').json()
    assert set(history) >= {'ReleaseAuthorizationReceipt','ConsumptionPermitReceipt','DeliveryObservation','PermitEligibilityDecision'}
    assert 'payload' not in canonical(history)
    assert history['DeliveryObservation'][0]['kind'] == 'DELIVERY_UNKNOWN'
    assert b.ask([sid])['error'] == 'GRANT_QUOTA_EXHAUSTED'


def test_edit_revoke_tombstone_and_immutable_receipts(lab):
    app, c, a, b = lab
    sid = a.note(); gid = a.share(sid, uses=5); job = b.ask([sid])
    with app.state.store.transaction(write=False) as tx:
        before = tx.get('release_receipts', job['output']['release_id'])
    assert a.call('PATCH', '/api/notes/' + sid, {'title':'Lake walk','text':'Pack an umbrella instead.','expected_revision':1}).status_code == 200
    assert b.consume(job).status_code == 409
    assert a.call('PATCH', '/api/notes/' + sid, {'title':'x','text':'x','expected_revision':1}).status_code == 409
    job2 = b.ask([sid]); assert job2['disposition'] == 'SUCCEEDED'
    assert a.call('POST', '/api/grants/' + gid + '/revoke', {'expected_revision':1}).status_code == 200
    assert b.consume(job2).status_code == 409
    assert b.call('GET', '/api/notes').json()['notes'] == []
    assert a.call('DELETE', '/api/notes/' + sid, {'expected_revision':2}).json()['erasure'] == 'NOT_VERIFIED'
    with app.state.store.transaction(write=False) as tx:
        assert before == tx.get('release_receipts', job['output']['release_id'])
        assert tx.get('quota_ledger', gid)['charged_units'] == 2


def test_uncited_ancestor_fences_release_and_consumption(lab):
    app, c, a, b = lab
    ancestor = a.note('Earlier plan has the lake path open.', 'Original plan')
    child = a.note('Pack water for the lake walk.', 'Packing', [ancestor])
    job = a.ask([child])
    with app.state.store.transaction(write=False) as tx:
        output = tx.get('outputs', job['output']['output_id'])
        assert ancestor not in output['payload']['source_refs']
        assert ancestor in [s['id'] for s in output['vector']['source_dependencies']]
    a.call('PATCH', '/api/notes/' + ancestor, {'title':'Original plan','text':'Lake path is closed.','expected_revision':1})
    assert a.consume(job).status_code == 409
    r = a.call('POST','/api/answers',{'question':'packing','source_ids':[child], 'destination_ref':a.destination,'idempotency_key':'stale-child'})
    assert r.status_code == 409


def test_joint_atomic_deduplicated_claims(lab):
    app, c, a, b = lab
    parent = a.note('Lake route note', 'Common parent')
    x = a.note('Lake walk x', 'X', [parent]); y = a.note('Lake walk y', 'Y', [parent])
    gp, gx, gy = [a.share(s, uses=1) for s in (parent,x,y)]
    job = b.ask([x,y])
    assert job['disposition']=='SUCCEEDED'
    with app.state.store.transaction(write=False) as tx:
        claims = [r for r in tx.all('grant_use_claims') if r['release_id']==job['output']['release_id']]
        assert len(claims)==3 and {r['grant_id'] for r in claims}=={gp,gx,gy}
    assert b.consume(job).status_code==200
    second=b.ask([x,y]); assert second['error']=='GRANT_QUOTA_EXHAUSTED'
    with app.state.store.transaction(write=False) as tx:
        assert [tx.get('quota_ledger', g)['charged_units'] for g in (gp,gx,gy)]==[1,1,1]


def test_concurrent_single_quota(lab):
    app,c,a,b=lab; sid=a.note(); gid=a.share(sid)
    first=b.ask([sid],wait=False); second=b.ask([sid],wait=False)
    time.sleep(.2)
    results=[b.call('GET','/api/jobs/'+j).json() for j in (first,second)]
    assert sorted(j['disposition'] for j in results)==['FAILED','SUCCEEDED']
    with app.state.store.transaction(write=False) as tx:
        assert tx.get('quota_ledger',gid)['charged_units']==1


def test_expiry_and_lost_consume_reply(lab):
    app,c,a,b=lab; sid=a.note(); gid=a.share(sid); job=b.ask([sid])
    app.state.store.fault_after_commit='consume:'+job['output']['output_id']
    response=b.consume(job)
    assert response.status_code==503 and 'payload' not in response.json()
    duplicate=b.consume(job).json(); assert duplicate['status']=='HISTORY_ONLY' and 'payload' not in duplicate
    a.call('POST','/api/grants/'+gid+'/revoke',{'expected_revision':1})
    history=b.call('GET','/api/outputs/'+job['output']['output_id']+'/receipts').json()
    assert history['DeliveryObservation'][0]['kind']=='DELIVERY_UNKNOWN'
    assert history['PermitEligibilityDecision']['decision']=='DENIED'
    sid2=a.note('Water for the walk'); a.share(sid2); job2=b.ask([sid2])
    original=app.state.store.clock; app.state.store.clock=lambda: original()+4000
    assert b.consume(job2).status_code==409


def test_unknown_release_reconciliation_no_second_charge(lab):
    app,c,a,b=lab; sid=a.note(); gid=a.share(sid)
    async def hold(job): pass
    app.state.service.submit=hold
    jid=b.ask([sid],wait=False)
    app.state.store.fault_after_commit='release:'+jid
    c.portal.call(app.state.service.deterministic,jid)
    job=b.call('GET','/api/jobs/'+jid).json()
    assert job['disposition']=='SUCCEEDED' and 'payload' not in job
    assert b.consume(job).status_code==200
    with app.state.store.transaction(write=False) as tx:
        assert tx.get('quota_ledger',gid)['charged_units']==1


def test_cancel_queued_and_released(lab):
    app,c,a,b=lab; sid=a.note()
    async def hold(job): pass
    app.state.service.submit=hold
    jid=a.ask([sid],wait=False)
    assert a.call('POST','/api/jobs/'+jid+'/cancel').json()['compute_state']=='NOT_STARTED'
    c.portal.call(app.state.service.deterministic,jid)
    assert 'output' not in a.call('GET','/api/jobs/'+jid).json()


FIELDS = list(AuthorityVector.model_fields)
@pytest.mark.parametrize('phase',['retrieval','admission','release','consume'])
@pytest.mark.parametrize('field',FIELDS)
def test_each_vector_precondition_rejects_altered_snapshot(lab,field,phase):
    app,c,a,b=lab; sid=a.note(); job=a.ask([sid])
    with app.state.store.transaction(write=False) as tx:
        vector=copy.deepcopy(tx.get('outputs',job['output']['output_id'])['vector'])
        value=vector[field]
        if isinstance(value,list):
            vector[field]=[] if value else [{'id':'unrecognized','revision':1,'revocation_epoch':1}]
        elif isinstance(value,int): vector[field]=value+1
        else: vector[field]=value+'.changed'
        with pytest.raises(Denied): authority.check_current(tx,vector,phase=phase)


def test_security_headers_and_spoofing(lab):
    app,c,a,b=lab
    assert a.call('POST','/api/drafts',{'kind':'draft','text':'x','idempotency_key':'x'},headers={'Origin':'http://evil.example'}).status_code==403
    assert a.call('POST','/api/drafts',{'kind':'draft','text':'x','idempotency_key':'x'},headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert a.call('GET','/healthz',headers={'Host':'evil.example'}).status_code==403
    assert a.call('POST','/api/notes',{'title':'x','text':'x','idempotency_key':'x','owner':'B'}).status_code==422
    assert a.call('POST','/api/session',{'person':'C'}).status_code==422
    sid=a.note(); assert b.call('DELETE','/api/notes/'+sid,{'expected_revision':1}).status_code==404
    assert 'default-src' in a.call('GET','/').headers['content-security-policy']


def test_images_safe_metadata_and_hostile(lab):
    app,c,a,b=lab
    buf=io.BytesIO(); Image.new('RGB',(32,24),'green').save(buf,format='PNG')
    r=a.call('POST','/api/images',content=buf.getvalue(),headers={'Content-Type':'image/png'})
    assert r.status_code==201, r.text
    sid=r.json()['source_id']; meta=r.json()['preprocessing_identity']; assert meta['width']==32
    assert b.call('GET','/api/images/'+sid+'/content').status_code==404
    assert a.call('GET','/api/images/'+sid+'/content').status_code==200
    assert a.call('POST','/api/images',content=b'<svg onload="alert(1)"/>',headers={'Content-Type':'image/png'}).status_code==422
    assert a.call('POST','/api/images',content=buf.getvalue(),headers={'Content-Type':'image/jpeg'}).status_code==422
    assert a.call('POST','/api/images',content=b'x'*(2*1024*1024+1),headers={'Content-Type':'image/png'}).status_code==413
    image_job=a.ask([],image_source_id=sid)
    assert image_job['disposition']=='SUCCEEDED'
    with app.state.store.transaction(write=False) as tx:
        j=tx.get('jobs',image_job['job_id']); context=tx.get('contexts',j['context_id'])
        assert digest({k:v for k,v in context.items() if k!='context_digest'})==context['context_digest']
        assert context['image_sha256']==meta['derivative_sha256']


def test_drafts_idempotency_and_persistence(lab):
    app,c,a,b=lab; data={'kind':'task','text':'Bring water','idempotency_key':'draft1'}
    first=a.call('POST','/api/drafts',data).json(); second=a.call('POST','/api/drafts',data).json(); assert first==second
    assert a.call('POST','/api/drafts',{**data,'text':'different'}).status_code==409
    assert b.call('GET','/api/drafts').json()['drafts']==[]
    assert a.call('PATCH','/api/drafts/'+first['id'],{'expected_revision':1,'text':'Bring water','done':True}).json()['done']
    with sqlite3.connect(app.state.store.path) as db:
        assert json.loads(db.execute('SELECT body FROM drafts WHERE id=?',(first['id'],)).fetchone()[0])['done'] is True


def test_current_restart_and_rollback_quarantine(tmp_path):
    store=Store(tmp_path)
    with store.transaction(operation='seed') as tx:
        tx.put('drafts','x',{'id':'x','text':'before'})
    store.close()
    saved=store.path.read_bytes()
    current=Store(tmp_path); assert current.continuity_status=='INTACT_CURRENT'
    with current.transaction() as tx:
        tx.put('drafts','x',{'id':'x','text':'after'})
        old_epoch=tx.meta('authority_instance_epoch')
    current.close(); current.path.write_bytes(saved)
    restored=Store(tmp_path)
    assert restored.continuity_status=='UNPROVEN_REVIEW_ONLY'
    with restored.transaction(write=False) as tx:
        assert tx.meta('review_only') is True and tx.meta('authority_instance_epoch')!=old_epoch
        with pytest.raises(Denied): authority.live(tx)
    restored.close()


def test_immutable_receipts_and_migration_version(lab):
    app,c,a,b=lab; sid=a.note(); job=a.ask([sid])
    with sqlite3.connect(app.state.store.path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==2
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM release_receipts')


def test_bound_sources_depth_and_cycle(lab):
    app,c,a,b=lab
    ids=[a.note('Lake walk','note '+str(i)) for i in range(33)]
    with app.state.store.transaction(write=False) as tx:
        assert len(authority.resolve_closure(tx,'A',ids[:32])[0])==32
        with pytest.raises(Denied): authority.resolve_closure(tx,'A',ids)
    parent=ids[0]
    for depth in range(16): parent=a.note('Lake walk','depth '+str(depth),[parent])
    r=a.call('POST','/api/notes',{'title':'overflow','text':'Lake walk','parents':[parent],'idempotency_key':'deep'})
    assert r.status_code==413
    assert a.call('PATCH','/api/notes/'+ids[0],{'title':'cycle','text':'Lake','parents':[ids[0]],'expected_revision':1}).status_code==409


def test_model_route_closed_without_root_gate(lab):
    app,c,a,b=lab
    r=a.call('POST','/api/answers',{'question':'hello','route':'model','destination_ref':a.destination,'idempotency_key':'model'})
    assert r.status_code==503 and r.json()['code']=='MODEL_UNAVAILABLE'
    assert not (app.state.store.runtime_dir/'model'/'model-calls.jsonl').exists()


def test_grant_edge_and_metadata_bounds(lab):
    app,c,a,b=lab
    roots=[a.note('Lake walk detail','root '+str(i)) for i in range(17)]
    for sid in roots: a.share(sid,uses=2)
    with app.state.store.transaction(write=False) as tx:
        assert len(authority.resolve_closure(tx,'B',roots[:16])[1])==16
        with pytest.raises(Denied,match='CLOSURE_LIMIT'): authority.resolve_closure(tx,'B',roots)
    children=[a.note('Lake walk child','child '+str(i),roots[:16]) for i in range(9)]
    with app.state.store.transaction(write=False) as tx:
        assert len(authority.resolve_closure(tx,'A',children[:8])[2])==128
        with pytest.raises(Denied,match='LINEAGE_EDGE_LIMIT'): authority.resolve_closure(tx,'A',children)
    large=[a.note('lake '+('x'*3995),'large '+str(i)) for i in range(16)]
    r=a.call('POST','/api/answers',{'question':'lake','source_ids':large,'destination_ref':a.destination,'idempotency_key':'metadata-overflow'})
    assert r.status_code==413 and r.json()['code']=='METADATA_LIMIT'


@pytest.mark.parametrize('over',[False,True])
def test_exact_output_byte_boundary_and_duplicate_release(lab,over):
    app,c,a,b=lab; sid=a.note()
    async def hold(job): pass
    app.state.service.submit=hold
    jid=a.ask([sid],wait=False)
    with app.state.store.transaction(write=False) as tx:
        job=tx.get('jobs',jid); context=tx.get('contexts',job['context_id'])
    payload={'text':''}
    payload['text']='x'*(262144-len(canonical(payload).encode())+int(over))
    candidate={**job,'payload':payload,'output_digest':digest(payload),'context_digest':context['context_digest'],'source_refs':[sid]}
    with app.state.store.transaction(operation='test-output-limit') as tx:
        if over:
            with pytest.raises(Denied,match='OUTPUT_LIMIT'):
                authority.authorize_release(tx,candidate,release_key='test:'+jid,request_digest=digest(candidate))
        else:
            first=authority.authorize_release(tx,candidate,release_key='test:'+jid,request_digest=digest(candidate))
            repeated=authority.authorize_release(tx,candidate,release_key='test:'+jid,request_digest=digest(candidate))
            assert first['release_id']==repeated['release_id'] and repeated['disposition']=='HISTORY_ONLY'
            assert 'payload' not in repeated


def test_late_display_observation_wrong_tuple_and_conflict(lab):
    app,c,a,b=lab; sid=a.note(); gid=a.share(sid); job=b.ask([sid]); result=b.consume(job).json()
    o=job['output']; data={k:o[k] for k in ('release_id','output_digest','destination_ref','nonce')}
    data.update(consumption_id=result['ConsumptionPermitReceipt']['consumption_id'],kind='DISPLAY_REPORTED',idempotency_key='ack')
    a.call('POST','/api/grants/'+gid+'/revoke',{'expected_revision':1})
    assert b.call('POST','/api/outputs/'+o['output_id']+'/observations',{**data,'output_digest':'wrong'}).status_code==409
    late=b.call('POST','/api/outputs/'+o['output_id']+'/observations',data)
    assert late.status_code==201
    assert b.call('POST','/api/outputs/'+o['output_id']+'/observations',data).json()==late.json()
    assert b.call('POST','/api/outputs/'+o['output_id']+'/observations',{**data,'kind':'STOP_REPORTED'}).status_code==409
    history=b.call('GET','/api/outputs/'+o['output_id']+'/receipts').json()
    assert [r['kind'] for r in history['DeliveryObservation']]==['DELIVERY_UNKNOWN','DISPLAY_REPORTED']
    assert history['PermitEligibilityDecision']['decision']=='DENIED'


def test_callback_requires_exact_request_and_admitted_attempt(lab):
    app,c,a,b=lab; sid=a.note()
    async def hold(job): pass
    app.state.service.submit=hold
    jid=a.ask([sid],wait=False)
    with app.state.store.transaction(write=False) as tx:
        job=tx.get('jobs',jid); context=tx.get('contexts',job['context_id'])
    payload=authority.deterministic_payload(context)
    result={**job,'payload':payload,'output_digest':digest(payload),'context_digest':context['context_digest'],'source_refs':payload['source_refs']}
    rejected=c.portal.call(app.state.service.on_result,result)
    assert rejected['reason']=='ATTEMPT_NOT_ADMITTED'
    with app.state.store.transaction(write=False) as tx:
        assert tx.get('jobs',jid)['output_id'] is None
    jid2=a.ask([sid],wait=False)
    with app.state.store.transaction(write=False) as tx:
        job2=tx.get('jobs',jid2); context2=tx.get('contexts',job2['context_id'])
    assert c.portal.call(app.state.service.admit_attempt,jid2,job2['attempt_id'],job2['lease_fence'])['decision']=='ADMITTED'
    result.update(job2); result.update(request_id='wrong',context_digest=context2['context_digest'])
    assert c.portal.call(app.state.service.on_result,result)['reason']=='REQUEST_IDENTITY_CONFLICT'
