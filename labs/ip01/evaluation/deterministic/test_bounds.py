"""Executable at-and-beyond boundaries against real HTTP and authority state."""
import copy,json,os,time
from pathlib import Path
import pytest
from common import key,db_rows,write,canonical
from haven import authority as auth
from haven.contracts import LIMITS,Denied,digest
from test_functional import hold

def receipt(bound,at,beyond,adapter):write(Path(os.environ['QA_RUN_DIR'])/('bound-'+bound+'.json'),{'bound':bound,'limit':LIMITS[bound],'at':at,'beyond':beyond,'adapter':adapter,'status':'PASS'})

def test_people_bound(lab):
    for person in ('A','B'):assert lab[person.lower()].request('GET','/api/session').json()['person']==person
    r=lab['a'].request('POST','/api/session',json={'person':'C'});assert r.status_code==422
    receipt('people',2,3,'Real HTTP separate A/B cookie jars and rejected third principal')

def test_sources_bound(lab):
    a=lab['a'];notes=[a.note('Boundary source '+str(i)) for i in range(33)];hold(lab)
    r,_=a.submit('Bound sources',[n['note_id'] for n in notes[:32]]);assert r.status_code==202,r.text
    r,_=a.submit('Excess sources',[n['note_id'] for n in notes]);assert r.status_code==422,r.text
    # Closure bypasses request-list length: one extra ancestor is still rejected.
    child=a.note('Boundary child',parents=[notes[0]['note_id']]);r,_=a.submit('Excess closure',[child['note_id'],*[n['note_id'] for n in notes[1:32]]]);assert r.status_code==413,r.text
    receipt('sources',32,33,'HTTP explicit list plus 33-member expanded ancestry')

def test_grants_bound(lab):
    a,b=lab['a'],lab['b'];notes=[a.note('Grant boundary '+str(i)) for i in range(17)]
    for n in notes:a.share(n,5)
    hold(lab);r,_=b.submit('Sixteen grants',[n['note_id'] for n in notes[:16]]);assert r.status_code==202,r.text
    r,_=b.submit('Seventeen grants',[n['note_id'] for n in notes]);assert r.status_code==413,r.text
    assert not db_rows(lab['store'].path,'grant_use_claims')
    receipt('grants',16,17,'HTTP source-grant closure')

def test_depth_bound(lab):
    a=lab['a'];last=a.note('Root depth zero')
    for depth in range(1,17):last=a.note('Depth '+str(depth),parents=[last['note_id']])
    hold(lab);r,_=a.submit('Depth sixteen',[last['note_id']]);assert r.status_code==202,r.text
    r=a.request('POST','/api/notes',json={'text':'Depth seventeen','title':'Beyond depth','parents':[last['note_id']],'idempotency_key':key()});assert r.status_code==413,r.text
    receipt('depth',16,17,'HTTP ancestry construction/retrieval')

def test_edges_bound(lab):
    a=lab['a'];leaves=[a.note('Leaf '+str(i)) for i in range(16)];branches=[a.note('Branch '+str(i),parents=[x['note_id'] for x in leaves]) for i in range(8)]
    hold(lab);r,_=a.submit('128 edge closure',[x['note_id'] for x in branches]);assert r.status_code==202,r.text
    extra=a.note('Extra edge',parents=[leaves[0]['note_id']]);r,_=a.submit('129 edge closure',[x['note_id'] for x in branches]+[extra['note_id']]);assert r.status_code==413,r.text
    receipt('edges',128,129,'HTTP actual DAG with sixteen leaves and eight parents')

def test_metadata_exact_bound(lab):
    a,s=lab['a'],lab['store'];notes=[a.note('x','m') for _ in range(16)];hold(lab);r,request=a.submit('Metadata bound',[n['note_id'] for n in notes]);assert r.status_code==202
    stored_job=db_rows(s.path,'jobs')[0];job={**request,'job_id':stored_job['job_id']};context=db_rows(s.path,'contexts')[0];session_id=context['authority_vector']['session_revision']
    context_without_digest={k:v for k,v in context.items() if k!='context_digest'}
    # Stored context adds its immutable identity outside the sealed context payload.
    context_without_digest.pop('id',None)
    with s.transaction(write=False) as tx:
        ctx=auth.build_context(tx,tx.get('sessions',session_id),job)
    base=len(canonical({k:v for k,v in ctx.items() if k!='context_digest'}));extra=LIMITS['metadata_bytes']-base
    assert 0<extra<=16*3999
    lengths=[1]*16
    for i in range(16):take=min(extra,3999);lengths[i]+=take;extra-=take
    def install(delta=0):
        with s.transaction(operation='qa-metadata-size') as tx:
            for i,n in enumerate(notes):
                source=tx.get('sources',n['note_id']);source['text']='x'*(lengths[i]+(delta if i==15 else 0));tx.put('sources',n['note_id'],source)
    install()
    with s.transaction(write=False) as tx:
        ctx=auth.build_context(tx,tx.get('sessions',session_id),job)
        assert len(canonical({k:v for k,v in ctx.items() if k!='context_digest'}))==65536
    install(1)
    with s.transaction(write=False) as tx:
        with pytest.raises(Denied) as denied:auth.build_context(tx,tx.get('sessions',session_id),job)
    assert denied.value.code=='METADATA_LIMIT'
    receipt('metadata_bytes',65536,65537,'Actual context builder, private source text fault seeding; sealed vector never edited')

@pytest.mark.parametrize('size',[262144,262145])
def test_output_exact_bound(lab,size):
    a,s=lab['a'],lab['store'];n=a.note('Output bound synthetic source');captured=[];service=lab['app'].state.service;original=service.on_result
    async def capture(result):captured.append(result);return {'disposition':'UNKNOWN','reason':'QA_OUTPUT_BOUND_BARRIER'}
    service.on_result=capture;r,_=a.submit('Output bound',[n['note_id']]);assert r.status_code==202
    end=time.monotonic()+4
    while not captured and time.monotonic()<end:time.sleep(.01)
    assert captured
    result=captured[0];payload={'text':''};payload['text']='x'*(size-len(canonical(payload)));assert len(canonical(payload))==size
    result['payload']=payload;result['output_digest']=digest(payload)
    outcome=lab['first'].portal.call(original,result)
    assert outcome['disposition']==('RELEASE_ADMITTED' if size==262144 else 'FENCED'),outcome
    assert len(db_rows(s.path,'release_receipts'))==(1 if size==262144 else 0)
    write(Path(os.environ['QA_RUN_DIR'])/('output-'+str(size)+'.json'),{'bound':'output_bytes','bytes':size,'outcome':outcome,'status':'PASS','adapter':'Actual on_result after admitted deterministic job; evaluator replacement payload with recomputed digest'})
