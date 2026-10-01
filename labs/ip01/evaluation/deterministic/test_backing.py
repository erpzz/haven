"""Actual private backing-state/config changes; sealed vectors remain unchanged.
These are storage-bound authority-adapter trials, not 104 captured-vector edits.
"""
import copy,os
from pathlib import Path
import pytest
from common import db_rows,key,write
from test_functional import hold
from haven import authority as auth
from haven.contracts import Denied,AuthorityVector

ADAPTERS=['authority_instance_epoch','restore_epoch','policy_ref','purpose_definition_ref','rights_policy_refs','principal_ref','session_revision','device_binding_revision','device_epoch','tool_catalog_digest','grant_dependencies','source_dependencies','job_ref','lease_fence','cancel_scope_epochs','destination_ref','destination_epoch','audience_revision','dependency_closure_digest']
GAPS=['vector_version','service_capability_revision','subject_scope_revision','participant_area_scope_revision','route_profile_revision','provider_data_policy_revision','canonicalization_version']

@pytest.mark.parametrize('component',ADAPTERS)
@pytest.mark.parametrize('phase',['retrieval','admission','release','consume'])
def test_changed_backing_fences_sealed_vector(lab,monkeypatch,component,phase):
    a,b,s=lab['a'],lab['b'],lab['store'];n=a.note('Independent backing-state synthetic fact.');parent=a.note('Independent backing-state second root.')
    g=a.share(n,5);a.share(parent,5);hold(lab)
    response,_=b.submit('Use synthetic sources',[n['note_id'],parent['note_id']]);assert response.status_code==202
    jid=response.json()['job_id'];context=db_rows(s.path,'contexts')[0];vector=context['authority_vector'];sealed=copy.deepcopy(vector)
    with s.transaction(write=False) as tx:assert auth.check_current(tx,vector,phase=phase)['decision']=='ELIGIBLE_AT_CHECK'
    constants={'policy_ref':('POLICY','ip01.synthetic-local.v2'),'purpose_definition_ref':('PURPOSE','answer.v2'),'rights_policy_refs':('RIGHTS',['SYNTHETIC_DEMO_CONTENT_ONLY.v2']),'tool_catalog_digest':('TOOL_DIGEST','f'*64)}
    with s.transaction(operation='qa-backing-fault-'+component) as tx:
        if component in constants:
            field,value=constants[component];monkeypatch.setattr(auth,field,value)
        elif component in ('authority_instance_epoch','restore_epoch'):
            value=tx.meta(component);tx.meta(component,value+1 if isinstance(value,int) else value+'-new')
        elif component=='grant_dependencies':
            row=tx.get('grants',g['grant_id']);row['authorization_revision']+=1;tx.put('grants',g['grant_id'],row)
        elif component in ('source_dependencies','dependency_closure_digest'):
            row=tx.get('sources',n['note_id'])
            if component=='source_dependencies':row['sha256']='e'*64
            else:row['parents']=[{'id':parent['note_id'],'revision':1}]
            tx.put('sources',n['note_id'],row)
        elif component in ('job_ref','lease_fence','cancel_scope_epochs'):
            row=tx.get('jobs',jid)
            if component=='job_ref':row['owner']='A'
            else:row['lease_fence' if component=='lease_fence' else 'cancel_epoch']+=1
            tx.put('jobs',jid,row)
        else:
            row=tx.get('sessions',vector['session_revision'])
            fields={'principal_ref':'person','audience_revision':'person','session_revision':'active','device_binding_revision':'device_ref','device_epoch':'device_epoch','destination_ref':'destination_ref','destination_epoch':'destination_epoch'}
            field=fields[component]
            row[field]=False if field=='active' else 'A' if field=='person' else row[field]+1 if isinstance(row[field],int) else row[field]+'-changed'
            tx.put('sessions',vector['session_revision'],row)
    with s.transaction(write=False) as tx:
        with pytest.raises(Denied) as denied:auth.check_current(tx,vector,phase=phase)
    assert vector==sealed and db_rows(s.path,'contexts')[0]['authority_vector']==sealed
    assert not db_rows(s.path,'release_receipts') and not db_rows(s.path,'consumption_receipts')
    write(Path(os.environ['QA_RUN_DIR'])/(component+'-'+phase+'.json'),{'component':component,'phase':phase,'kind':'CURRENT_BACKING_OR_PROCESS_CONFIGURATION_MUTATION','denial':denied.value.code,'sealed_vector_unchanged':True,'coupling':{'principal_ref':['audience_revision'],'audience_revision':['principal_ref'],'job_ref':['job ownership invalidation'],'session_revision':['session active state invalidation']}.get(component,[]),'status':'PASS'})

def test_full_vector_denominator():
    assert set(ADAPTERS+GAPS)==set(AuthorityVector.model_fields)
    assert len(ADAPTERS)+len(GAPS)==26
    write(Path(os.environ['QA_RUN_DIR'])/'vector-coverage.json',{'required_components':26,'required_phases':4,'backing_adapter_cases':76,'static_constant_cases_separately_defined':28,'static_domains':GAPS,'note':'These phase calls directly execute authoritative check_current using changed private DB/config, not full route execution. principal/audience are coupled; job/session cases invalidate availability. Static literal domains have no supported live reconfiguration seam.'})
