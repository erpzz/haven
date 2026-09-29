"""Independent executable regression repros from CODE-EARLY; require safe behavior."""
import copy,importlib,os
import pytest
from pathlib import Path
from common import db_rows,key,write

@pytest.mark.parametrize('reverse',[False,True])
def test_CE_F04_shared_ancestor_longest_depth(lab,reverse):
    a,s=lab['a'],lab['store'];seed=a.note('Synthetic lineage fixture template');template=next(x for x in db_rows(s.path,'sources') if x['id']==seed['note_id'])
    with s.transaction(operation='qa-deterministic-DAG-fixture') as tx:
        for i in range(17):
            row=copy.deepcopy(template);row['id']='qa-c%02d'%i;row['parents']=[] if i==0 else [{'id':'qa-c%02d'%(i-1),'revision':1}]
            tx.put('sources',row['id'],row,insert=True)
    at=a.request('POST','/api/notes',json={'title':'At depth16','text':'Synthetic at-bound DAG','parents':['qa-c07','qa-c15'],'idempotency_key':key()})
    beyond=a.request('POST','/api/notes',json={'title':'Beyond depth17','text':'Synthetic beyond-bound DAG','parents':['qa-c16','qa-c08'] if reverse else ['qa-c08','qa-c16'],'idempotency_key':key()})
    write(Path(os.environ['QA_RUN_DIR'])/'CE-F04.json',{'at16':{'status':at.status_code,'body':at.json()},'beyond17':{'status':beyond.status_code,'body':beyond.json()},'fixture':'17-node chain; redundant shorter parent sorts first; actual POST notes invokes closure validation'})
    assert at.status_code==201,at.text
    assert beyond.status_code==413,'CE-F04: actual HTTP accepted longest-path depth17: '+str(beyond.status_code)

def test_CE_F05_new_grant_after_exhausted_grant(lab,monkeypatch):
    app=importlib.import_module('haven.app');original=app.uid;ids=iter(['grant_0001_qa','grant_0002_qa'])
    monkeypatch.setattr(app,'uid',lambda prefix='r':next(ids) if prefix=='grant' else original(prefix))
    a,b,s=lab['a'],lab['b'],lab['store'];n=a.note('Synthetic overlapping-grant value LAPIS.');g1=a.share(n,1)
    old,_,_=b.answer('First release',[n['note_id']]);assert old['disposition']=='SUCCEEDED'
    g2=a.share(n,1);fresh,_,_=b.answer('Fresh newly authorized release',[n['note_id']])
    consumed=b.fresh_payload(old);assert 'LAPIS' in consumed['payload']['text']
    write(Path(os.environ['QA_RUN_DIR'])/'CE-F05.json',{'g1':g1['grant_id'],'g2':g2['grant_id'],'fresh_disposition':fresh['disposition'],'fresh_error':fresh.get('error'),'old_slot_consumed_at_zero':True,'ledger':db_rows(s.path,'quota_ledger'),'claims':db_rows(s.path,'grant_use_claims')})
    assert fresh['disposition']=='SUCCEEDED','CE-F05: exhausted G1 shadows fresh G2: '+str(fresh.get('error'))
    assert b.fresh_payload(fresh)['status']=='FRESH_CONSUMPTION'
    exhausted,_,_=b.answer('Both grants exhausted',[n['note_id']]);assert exhausted['disposition']=='FAILED'
    assert sorted(x['charged_units'] for x in db_rows(s.path,'quota_ledger'))==[1,1]
