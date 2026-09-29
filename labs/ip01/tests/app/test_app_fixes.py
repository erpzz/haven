"""APP-FIX development regressions; synthetic callbacks, zero inference."""
import copy
import asyncio
from datetime import datetime, timezone
import time
import uuid
import pytest
from test_application import lab
from haven.contracts import digest


async def hold(job):
    pass


def queued(lab, monkeypatch, model=False):
    app, c, a, b = lab
    service = app.state.service
    monkeypatch.setattr(service, 'submit', hold)
    parent = a.note('Uncited ancestor', 'Parent')
    sid = a.note(parents=[parent])
    if model:
        gate = {'identity': {k: 'a'*64 for k in ('manifest_sha256','runtime_sha256','template_sha256','preprocessor_sha256')},
                'expires_utc': datetime.fromtimestamp(time.time()+300,timezone.utc).isoformat(),
                'slots': {'synthetic-only-token': {'allocation':'readiness'}}}
        snapshot = {'enabled':True,'gate':gate,'model_gate_sha256':digest(gate)}
        monkeypatch.setattr(service, 'model_gate', lambda: snapshot)
        monkeypatch.setenv('HAVEN_MODEL_ALLOCATION','readiness')
    jid = a.ask([sid], wait=False, route='model' if model else 'deterministic')
    with app.state.store.transaction(write=False) as tx:
        job=tx.get('jobs',jid); context=tx.get('contexts',job['context_id'])
    return job, context, parent


@pytest.mark.parametrize('reverse',[False,True])
def test_redundant_parent_longest_path(lab,reverse):
    app,c,a,b=lab
    ids=[a.note(title='c0')]
    for i in range(1,17):
        ids.append(a.note(title='c'+str(i),parents=[ids[-1]]))
    parents=[ids[8],ids[16]]
    if reverse: parents.reverse()
    r=a.call('POST','/api/notes',{'title':'root','text':'Depth17','parents':parents,'idempotency_key':uuid.uuid4().hex})
    assert r.status_code==413 and r.json()['code']=='LINEAGE_DEPTH_LIMIT',r.text
    # Exercise both stored edge orders directly as well; the HTTP layer sorts IDs.
    from haven import authority
    from haven.contracts import Denied
    with app.state.store.transaction() as tx:
        root=copy.deepcopy(tx.get('sources',ids[0]));root['id']='synthetic-root'
        root['parents']=[{'id':p,'revision':1} for p in parents]
        tx.put('sources',root['id'],root)
        with pytest.raises(Denied,match='LINEAGE_DEPTH_LIMIT'):
            authority.resolve_closure(tx,'A',[root['id']])


def test_fresh_grant_not_shadowed_old_claim_consumes(lab,monkeypatch):
    app,c,a,b=lab; sid=a.note(); g1=a.share(sid)
    first=b.ask([sid]); assert first['disposition']=='SUCCEEDED'
    import haven.app as app_module
    original_uid=app_module.uid
    monkeypatch.setattr(app_module,'uid',lambda prefix='r': 'grant_zzzz_fresh' if prefix=='grant' else original_uid(prefix))
    g2=a.share(sid)
    assert g1 < g2  # The exhausted grant must win the old lexical selection.
    second=b.ask([sid]); assert second['disposition']=='SUCCEEDED'
    assert b.consume(first).status_code==200
    with app.state.store.transaction(write=False) as tx:
        assert [tx.get('quota_ledger',g)['charged_units'] for g in (g1,g2)]==[1,1]
        claims=tx.all('grant_use_claims')
        assert {x['grant_id'] for x in claims if x['release_id']==first['output']['release_id']}=={g1}
        assert {x['grant_id'] for x in claims if x['release_id']==second['output']['release_id']}=={g2}


@pytest.mark.parametrize('change',['none','source','ancestor','cancel','gate','phase','unknown_commit','session','digest'])
def test_fresh_egress_exact_binding_no_second_claim(lab,monkeypatch,change):
    app,c,a,b=lab; job,context,parent=queued(lab,monkeypatch,True); service=app.state.service
    admitted=c.portal.call(service.admit_attempt,job['job_id'],job['attempt_id'],job['lease_fence'])
    assert admitted['decision']=='ADMITTED',admitted
    if change in ('source','ancestor'):
        sid=parent if change=='ancestor' else context['authority_vector']['source_dependencies'][-1]['id']
        with app.state.store.transaction() as tx:
            source=tx.get('sources',sid);source['revision']+=1;tx.put('sources',sid,source)
    elif change=='cancel': a.call('POST','/api/jobs/'+job['job_id']+'/cancel')
    elif change=='gate': monkeypatch.setattr(service,'model_gate',lambda:None)
    elif change=='phase': monkeypatch.setenv('HAVEN_MODEL_ALLOCATION','final')
    elif change=='session':
        with app.state.store.transaction() as tx:
            session=tx.get('sessions',job['session_id']);session['expires_at']=time.time()-1;tx.put('sessions',session['id'],session)
    elif change=='unknown_commit': app.state.store.fault_after_commit='egress:'+job['attempt_id']
    reply=c.portal.call(service.authorize_egress,job['job_id'],job['attempt_id'],job['lease_fence'],'f'*64 if change=='digest' else context['context_digest'])
    assert set(reply)=={'decision','reason','job_id','attempt_id','lease_fence','context_digest','cancel_epoch','decision_id','checked_at','valid_until','authority_vector_digest','model_gate_sha256'}
    assert reply['decision']==('AUTHORIZED' if change=='none' else 'UNKNOWN' if change=='unknown_commit' else 'DENIED'),reply
    if change=='none':
        assert 0<reply['valid_until']-reply['checked_at']<=1
        assert reply['authority_vector_digest']==digest(context['authority_vector'])
    if change=='unknown_commit': assert reply['decision_id'] is None
    with app.state.store.transaction(write=False) as tx:
        assert len(tx.all('attempts'))==1
        assert tx.all('grant_use_claims')==[] and tx.all('release_receipts')==[]
        assert any(e['kind']=='EGRESS_DECISION' for e in tx.all('events'))


def event(job,context,**changes):
    evidence={'job_disposition':'FAILED','reason':'DEADLINE_EXCEEDED','result_disposition':'NOT_PRODUCED',
              'context_digest':context['context_digest'],'claim_id':None,'admission_decision':'ADMITTED',
              'egress_decision_id':None,'cleanup_confirmed':True,'usage':{'model_calls':0,'certainty':'OBSERVED'}}
    evidence.update(changes.pop('evidence',{}))
    return {**{k:job[k] for k in ('job_id','request_id','attempt_id','lease_fence','cancel_epoch')},
            'event_id':uuid.uuid4().hex,'worker_instance_id':'worker','pid':None,'process_birth':None,
            'boot_id':'boot','nonce':'nonce','kind':'ATTEMPT_TERMINAL','observed_at':datetime.now(timezone.utc).isoformat(),
            'evidence':evidence,**changes}


@pytest.mark.parametrize('unknown',[False,True])
def test_terminal_projection_stable_and_stop_orthogonal(lab,monkeypatch,unknown):
    app,c,a,b=lab;job,ctx,_=queued(lab,monkeypatch)
    ev=event(job,ctx,evidence={'admission_decision':'UNKNOWN' if unknown else 'ADMITTED'})
    c.portal.call(app.state.service.on_event,ev)
    c.portal.call(app.state.service.on_event,ev)
    c.portal.call(app.state.service.on_event,event(job,ctx,evidence={'job_disposition':'CANCELLED'}))
    with app.state.store.transaction(write=False) as tx:
        saved=tx.get('jobs',job['job_id'])
        assert saved['disposition']==('INCONCLUSIVE' if unknown else 'FAILED')
        assert saved['compute_state']=='NOT_STARTED'
        assert tx.get('events',ev['event_id'])['evidence']['usage']==ev['evidence']['usage']
    c.portal.call(app.state.service.on_event,event(job,ctx,kind='STOP_CONFIRMED',evidence={'confirmed':True}))
    with app.state.store.transaction(write=False) as tx:
        assert tx.get('jobs',job['job_id'])['compute_state']=='STOP_CONFIRMED'


@pytest.mark.parametrize('bad',['request','fence','context','usage','nonce'])
def test_invalid_terminal_cannot_settle(lab,monkeypatch,bad):
    app,c,a,b=lab;job,ctx,_=queued(lab,monkeypatch)
    started=event(job,ctx,kind='PROCESS_STARTED');c.portal.call(app.state.service.on_event,started)
    ev=event(job,ctx)
    if bad=='request':ev['request_id']='wrong'
    if bad=='fence':ev['lease_fence']+=1
    if bad=='context':ev['evidence']['context_digest']='wrong'
    if bad=='usage':ev['evidence']['usage']={'model_calls':999}
    if bad=='nonce':ev['nonce']='wrong'
    c.portal.call(app.state.service.on_event,ev)
    with app.state.store.transaction(write=False) as tx:
        assert tx.get('jobs',job['job_id'])['disposition']=='QUEUED'


def test_real_supervisor_post_readiness_recheck_blocks_send(lab,monkeypatch):
    from haven.supervisor import Supervisor
    from haven.model_adapter import ModelAdapter
    from haven.app import wire_job
    app,c,a,b=lab;job,ctx,parent=queued(lab,monkeypatch,True)
    service=app.state.service
    calls=[]
    async def backend_stub(adapter,owned,admitted,deadline,cancel):
        calls.append('backend-ready')
        with app.state.store.transaction() as tx:
            source=tx.get('sources',parent);source['revision']+=1;tx.put('sources',parent,source)
        return {'synthetic_test_stub':True}
    monkeypatch.setattr(ModelAdapter,'start_for_attempt',backend_stub)
    async def result(candidate):
        calls.append('result')
        return await service.on_result(candidate)
    async def exercise():
        supervisor=Supervisor(runtime_dir=app.state.store.runtime_dir/'supervisor-integration',
            admit_attempt=service.admit_attempt,on_event=service.on_event,on_result=result,
            authorize_egress=service.authorize_egress)
        await supervisor.start()
        try:
            await supervisor.submit(wire_job(job))
            await asyncio.wait_for(supervisor.queue.join(),10)
            return await supervisor.snapshot(job['job_id'])
        finally:
            await supervisor.close(time.monotonic()+5)
    state=c.portal.call(exercise)
    assert calls==['backend-ready']
    assert state['disposition']=='FAILED' and state['compute_state']=='STOP_CONFIRMED',state
    with app.state.store.transaction(write=False) as tx:
        saved=tx.get('jobs',job['job_id'])
        assert saved['disposition']=='FAILED' and saved['compute_state']=='STOP_CONFIRMED',saved
        events=tx.all('events')
        assert any(e['kind']=='EGRESS_DECISION' and e['decision']=='DENIED' for e in events)
        assert any(e['kind']=='ATTEMPT_TERMINAL' and e['binding_valid'] and e['evidence_valid'] for e in events)
        assert not tx.all('outputs') and not tx.all('release_receipts')


def test_deterministic_unknown_admission_and_late_result_stay_inconclusive(lab,monkeypatch):
    from haven import authority
    app,c,a,b=lab;job,ctx,_=queued(lab,monkeypatch)
    app.state.store.fault_after_commit='admit:'+job['job_id']
    c.portal.call(app.state.service.deterministic,job['job_id'])
    payload=authority.deterministic_payload(ctx)
    result={**job,'payload':payload,'output_digest':digest(payload),'context_digest':ctx['context_digest'],'source_refs':payload['source_refs']}
    assert c.portal.call(app.state.service.on_result,result)['disposition']=='FENCED'
    with app.state.store.transaction(write=False) as tx:
        assert tx.get('jobs',job['job_id'])['disposition']=='INCONCLUSIVE'
        assert not tx.all('release_receipts')


def test_late_terminal_does_not_regress_committed_release(lab):
    app,c,a,b=lab;sid=a.note();public=a.ask([sid])
    with app.state.store.transaction(write=False) as tx:
        job=tx.get('jobs',public['job_id']);ctx=tx.get('contexts',job['context_id'])
        receipt=tx.get('release_receipts',job['release_id'])
    c.portal.call(app.state.service.on_event,event(job,ctx,evidence={'admission_decision':'UNKNOWN','result_disposition':'UNKNOWN'}))
    with app.state.store.transaction(write=False) as tx:
        assert tx.get('jobs',job['job_id'])['disposition']=='SUCCEEDED'
        assert tx.get('release_receipts',job['release_id'])==receipt
