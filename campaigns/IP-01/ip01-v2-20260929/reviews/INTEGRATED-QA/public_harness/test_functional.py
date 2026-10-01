import asyncio,copy,io,json,sqlite3,time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,PngImagePlugin
import pytest
from common import key,db_rows,no_payload,sha,canonical

def assert_success(r,code=200):assert r.status_code==code,r.text
def only(rows):assert len(rows)==1;return rows[0]
def marker_payload(a,state,marker):
    result=a.fresh_payload(state);assert marker in result['payload']['text'];return result
def hold(lab):
    saved=lab['app'].state.service.submit;queued=[]
    async def delayed(job):queued.append(job)
    lab['app'].state.service.submit=delayed
    return queued,saved

def test_private_useful_B_forbidden_and_explicit_shared(lab):
    a,b,s=lab['a'],lab['b'],lab['store'];marker='CEDAR-'+key()
    note=a.note('The synthetic cabinet key is '+marker+'.')
    state,job,_=a.answer('What is the synthetic cabinet key?',[note['note_id']])
    reply=marker_payload(a,state,marker)
    assert reply['payload']['source_refs']==[note['note_id']]
    assert marker not in b.request('GET','/api/notes').text
    assert b.request('GET',job['status_url']).status_code==404
    denied,_=b.submit('What is the synthetic cabinet key?',[note['note_id']]);assert denied.status_code==404
    a.share(note,2)
    state,_,_=b.answer('What is the synthetic cabinet key?',[note['note_id']]);marker_payload(b,state,marker)
    assert len(db_rows(s.path,'release_receipts'))==2

def test_one_use_at_zero_duplicate_and_no_refund(lab):
    a,b,s=lab['a'],lab['b'],lab['store'];n=a.note('The synthetic safe label is AMBER.');g=a.share(n,1)
    state,job,req=b.answer('What is the safe label?',[n['note_id']])
    ledger=only(db_rows(s.path,'quota_ledger'));claim=only(db_rows(s.path,'grant_use_claims'))
    assert ledger['charged_units']==1 and claim['claim_units']==1
    assert only(db_rows(s.path,'grants'))['authorization_revision']==g['authorization_revision']
    operation=key();r,body=b.consume(state,operation);assert_success(r);assert 'AMBER' in r.json()['payload']['text']
    dup,_=b.consume(state,operation);assert_success(dup);no_payload(dup.json())
    assert len(db_rows(s.path,'consumption_receipts'))==1
    assert only(db_rows(s.path,'quota_ledger'))['charged_units']==1
    same=b.request('POST','/api/answers',json=req);assert_success(same,202);assert same.json()['job_id']==job['job_id']
    conflict=dict(req,question='Changed immutable question');assert b.request('POST','/api/answers',json=conflict).status_code==409
    second,_,_=b.answer('What is the safe label?',[n['note_id']]);assert second['disposition']=='FAILED' and second['error']=='GRANT_QUOTA_EXHAUSTED'
    a.revoke(g)
    assert only(db_rows(s.path,'quota_ledger'))['charged_units']==1
    assert len(db_rows(s.path,'grant_use_claims'))==1

def test_four_records_immutable_history_and_conflicting_observation(lab):
    a,b,s=lab['a'],lab['b'],lab['store'];n=a.note('The synthetic folder color is GREEN.');g=a.share(n,1)
    state,job,_=b.answer('What is the folder color?',[n['note_id']]);r,consume=b.consume(state);assert_success(r)
    receipt=r.json()['ConsumptionPermitReceipt'];o=state['output'];before={t:db_rows(s.path,t) for t in ('release_receipts','consumption_receipts')}
    body={k:o[k] for k in ('release_id','output_digest','destination_ref','nonce')};body.update(consumption_id=receipt['consumption_id'],idempotency_key=key(),kind='DISPLAY_REPORTED')
    endpoint='/api/outputs/'+o['output_id']+'/observations'
    assert_success(b.request('POST',endpoint,json=body),201)
    assert_success(b.request('POST',endpoint,json=body),201)
    conflict=dict(body,kind='STOP_REPORTED');assert b.request('POST',endpoint,json=conflict).status_code==409
    wrong=dict(body,idempotency_key=key(),output_digest='0'*64);assert b.request('POST',endpoint,json=wrong).status_code==409
    a.revoke(g)
    assert_success(b.request('POST',job['status_url']+'/cancel'))
    history=b.request('GET','/api/outputs/'+o['output_id']+'/receipts');assert_success(history);no_payload(history.json())
    assert set(('ReleaseAuthorizationReceipt','ConsumptionPermitReceipt','DeliveryObservation','PermitEligibilityDecision')).issubset(history.json())
    assert history.json()['PermitEligibilityDecision']['decision']=='DENIED'
    observations=db_rows(s.path,'delivery_observations')
    assert sum(x['kind']=='DISPLAY_REPORTED' for x in observations)==1
    assert any(x['kind']=='DELIVERY_UNKNOWN' for x in observations)
    assert not any(x['kind'] in ('NOT_SENT','SUPPRESSED') for x in observations)
    for table,rows in before.items():assert db_rows(s.path,table)==rows

def test_edit_CAS_tombstone_and_fence_old_output(lab):
    a=lab['a'];n=a.note('The synthetic departure time is 09:17.')
    state,_,_=a.answer('What is the departure time?',[n['note_id']])
    updated=a.edit(n,'The synthetic departure time is 10:43.')
    stale=a.request('PATCH','/api/notes/'+n['note_id'],json={'title':'Stale','text':'Wrong','expected_revision':n['revision']});assert stale.status_code==409
    denied,_=a.consume(state);assert denied.status_code==409;no_payload(denied.json())
    current,_,_=a.answer('What is the departure time?',[n['note_id']]);result=marker_payload(a,current,'10:43');assert '09:17' not in result['payload']['text']
    deleted=a.request('DELETE','/api/notes/'+n['note_id'],json={'expected_revision':updated['revision']});assert_success(deleted)
    denied,_=a.submit('Departure time',[n['note_id']]);assert denied.status_code==404

@pytest.mark.parametrize('mutation',['edit','tombstone','revoke'])
def test_uncited_ancestor_mutation_queued(lab,mutation):
    a,b,s=lab['a'],lab['b'],lab['store']
    parent=a.note('Underlying synthetic restriction applies.')
    child=a.note('The displayed synthetic route is NORTH.',parents=[parent['note_id']])
    pg=a.share(parent,2);a.share(child,2)
    queued,_=hold(lab)
    r,_=b.submit('Which route is displayed?',[child['note_id']]);assert_success(r,202);job=r.json()
    context=only(db_rows(s.path,'contexts'));assert {x['id'] for x in context['sources']}=={parent['note_id'],child['note_id']}
    assert next(x for x in context['sources'] if x['id']==parent['note_id'])['selected'] is False
    if mutation=='edit':a.edit(parent,'Underlying restriction changed.')
    elif mutation=='tombstone':assert_success(a.request('DELETE','/api/notes/'+parent['note_id'],json={'expected_revision':parent['revision']}))
    else:a.revoke(pg)
    lab['first'].portal.call(lab['app'].state.service.deterministic,job['job_id'])
    state=b.wait(job);assert state['disposition']=='FAILED'
    assert not db_rows(s.path,'release_receipts') and not db_rows(s.path,'grant_use_claims')

def test_uncited_ancestor_after_admission_before_release(lab):
    a,s=lab['a'],lab['store'];parent=a.note('Underlying synthetic fact one.');child=a.note('Selected synthetic fact TWO.',parents=[parent['note_id']])
    captured=[];original=lab['app'].state.service.on_result
    async def capture(result):captured.append(result);return {'disposition':'UNKNOWN','reason':'EVALUATOR_RELEASE_BARRIER'}
    lab['app'].state.service.on_result=capture
    r,_=a.submit('What is the selected fact?',[child['note_id']]);assert_success(r,202)
    end=time.monotonic()+3
    while not captured and time.monotonic()<end:time.sleep(.01)
    assert captured and captured[0]['source_refs']==[child['note_id']]
    assert len(db_rows(s.path,'attempts'))==1
    a.edit(parent,'Underlying synthetic fact changed.')
    response=lab['first'].portal.call(original,captured[0]);assert response['disposition']=='FENCED'
    assert not db_rows(s.path,'release_receipts')

def test_joint_grant_atomicity_and_closure_dedup(lab):
    a,b,s=lab['a'],lab['b'],lab['store']
    parent=a.note('Common synthetic ancestor.');left=a.note('Left synthetic branch.',parents=[parent['note_id']]);right=a.note('Right synthetic branch.',parents=[parent['note_id']])
    for n in (parent,left,right):a.share(n,1)
    state,_,_=b.answer('Show both branches',[left['note_id'],right['note_id']]);b.fresh_payload(state)
    claims=db_rows(s.path,'grant_use_claims');assert len(claims)==3 and len({c['grant_id'] for c in claims})==3
    assert all(x['charged_units']==1 for x in db_rows(s.path,'quota_ledger'))
    fresh=a.note('Additional eligible synthetic source.');newgrant=a.share(fresh,1)
    failed,_,_=b.answer('Joint exhausted and fresh sources',[left['note_id'],fresh['note_id']]);assert failed['disposition']=='FAILED'
    assert next(x for x in db_rows(s.path,'quota_ledger') if x['id']==newgrant['grant_id'])['charged_units']==0
    assert len(db_rows(s.path,'grant_use_claims'))==3

def test_concurrent_quota_one_winner(lab):
    a,b,s=lab['a'],lab['b'],lab['store'];n=a.note('Concurrency synthetic value QUARTZ.');a.share(n,1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(b.answer,'Concurrency value',[n['note_id']]) for _ in range(2)]
        states=[f.result()[0] for f in futures]
    assert sum(x['disposition']=='SUCCEEDED' for x in states)==1
    winner=next(x for x in states if x['disposition']=='SUCCEEDED');marker_payload(b,winner,'QUARTZ')
    assert len(db_rows(s.path,'release_receipts'))==1 and len(db_rows(s.path,'grant_use_claims'))==1
    assert only(db_rows(s.path,'quota_ledger'))['charged_units']==1

def test_unknown_release_commit_reconciles_same_identity(lab):
    a,b,s=lab['a'],lab['b'],lab['store'];n=a.note('Unknown-commit synthetic value OPAL.');a.share(n,1);hold(lab)
    r,request=b.submit('Unknown commit value',[n['note_id']]);assert_success(r,202);job=r.json()
    s.fault_after_commit='release:'+job['job_id']
    lab['first'].portal.call(lab['app'].state.service.deterministic,job['job_id'])
    assert len(db_rows(s.path,'release_receipts'))==1 and not db_rows(s.path,'consumption_receipts')
    assert any(x['kind']=='RELEASE_UNKNOWN' for x in db_rows(s.path,'events'))
    state=b.wait(job);no_payload(state)
    duplicate=b.request('POST','/api/answers',json=request);assert_success(duplicate,202);assert duplicate.json()['job_id']==job['job_id']
    marker_payload(b,state,'OPAL')
    assert len(db_rows(s.path,'grant_use_claims'))==1 and only(db_rows(s.path,'quota_ledger'))['charged_units']==1

def test_unknown_consume_commit_no_replay_or_refund(lab):
    a,b,s=lab['a'],lab['b'],lab['store'];n=a.note('Unknown-consume synthetic value JADE.');a.share(n,1)
    state,_,_=b.answer('Unknown consumption value',[n['note_id']]);s.fault_after_commit='consume:'+state['output']['output_id']
    operation=key();r,body=b.consume(state,operation);assert r.status_code==503;no_payload(r.json())
    assert len(db_rows(s.path,'consumption_receipts'))==1
    r,_=b.consume(state,operation);assert_success(r);assert r.json()['status']=='HISTORY_ONLY';no_payload(r.json())
    assert only(db_rows(s.path,'quota_ledger'))['charged_units']==1 and len(db_rows(s.path,'grant_use_claims'))==1
    assert any(x['kind']=='CONSUMPTION_RESPONSE_UNKNOWN' for x in db_rows(s.path,'events'))

@pytest.mark.parametrize('change',[
    {'headers':{'X-CSRF-Token':''}}, {'headers':{'Origin':'http://hostile.invalid'}}, {'headers':{'Host':'hostile.invalid'}},
])
def test_session_web_boundaries(lab,change):
    a=lab['a'];r=a.request('POST','/api/notes',json={'text':'must not commit','title':'Blocked','idempotency_key':key()},**change);assert r.status_code==403
    assert not db_rows(lab['store'].path,'sources')

def test_principal_spoof_and_strict_contracts(lab):
    a,b=lab['a'],lab['b'];n=a.note('Owner-private synthetic record.')
    r=b.request('PATCH','/api/notes/'+n['note_id'],json={'title':'Spoof','text':'wrong','expected_revision':1});assert r.status_code==404
    r=b.request('POST','/api/notes',json={'title':'Spoof','text':'wrong','owner':'A','person':'A','idempotency_key':key()});assert r.status_code==422
    r=a.request('POST','/api/answers',json={'question':'x','route':'deterministic','destination_ref':a.destination,'idempotency_key':key(),'shell':'anything'});assert r.status_code==422

def test_drafts_tasks_edit_and_isolation(lab):
    a,b=lab['a'],lab['b']
    for kind in ('draft','task'):
        r=a.request('POST','/api/drafts',json={'kind':kind,'text':kind+' synthetic item','idempotency_key':key()});assert_success(r,201);d=r.json()
        r=a.request('PATCH','/api/drafts/'+d['id'],json={'expected_revision':d['revision'],'text':kind+' edited synthetic item','done':kind=='task'});assert_success(r)
    assert 'edited synthetic item' in a.request('GET','/api/drafts').text
    assert 'edited synthetic item' not in b.request('GET','/api/drafts').text

@pytest.mark.parametrize('kind',['svg','html','truncated','mismatch','animated','too_large'])
def test_image_hostile_imports(lab,kind):
    samples={'svg':b'<svg onload="alert(1)"/>','html':b'<script>alert(1)</script>','truncated':b'\x89PNG\r\n\x1a\n','too_large':b'x'*(2*1024*1024+1)}
    content_type='image/png'
    if kind in ('animated','mismatch'):
        buf=io.BytesIO();im=Image.new('RGB',(12,12),'red')
        if kind=='animated':im.save(buf,format='PNG',save_all=True,append_images=[Image.new('RGB',(12,12),'blue')],duration=50)
        else:im.save(buf,format='JPEG')
        raw=buf.getvalue()
    else:raw=samples[kind]
    # APP accepts raw image bytes, not multipart.
    r=lab['a'].request('POST','/api/images',content=raw,headers={'Content-Type':content_type,'X-Filename':'../../synthetic.png'})
    assert r.status_code in (400,413,415,422),r.text
    assert not db_rows(lab['store'].path,'sources')

def test_image_valid_metadata_stripped_private_and_inert(lab):
    a,b,s=lab['a'],lab['b'],lab['store'];buf=io.BytesIO();info=PngImagePlugin.PngInfo();info.add_text('Comment','<script>alert(1)</script>')
    Image.new('RGB',(40,30),'blue').save(buf,format='PNG',pnginfo=info)
    r=a.request('POST','/api/images',content=buf.getvalue(),headers={'Content-Type':'image/png'});assert_success(r,201);source=r.json()
    derivative=(lab['runtime']/'media'/(source['source_id']+'.png')).read_bytes()
    assert b'<script>' not in derivative
    with Image.open(io.BytesIO(derivative)) as image:assert image.size==(40,30) and not image.info
    assert b.request('GET','/api/images/'+source['source_id']+'/content').status_code==404
    assert a.request('GET','/api/images/'+source['source_id']+'/content').content==derivative
