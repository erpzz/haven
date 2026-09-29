"""Static-constant fault adapters, not fictitious HTTP live reconfiguration."""
import copy,types,os
from pathlib import Path
import pytest
from pydantic import ValidationError
from common import db_rows,write
from test_functional import hold
from haven import authority as auth
from haven.contracts import Denied
CONSTANTS={'vector_version':'ip01.authority.v1','service_capability_revision':'LOCAL_ASSISTANT.v1','subject_scope_revision':'SYNTHETIC_A_B.v1','participant_area_scope_revision':'NOT_APPLICABLE.v1','route_profile_revision':'LOCAL_BROWSER_WHOLE_OUTPUT.v1','provider_data_policy_revision':'NOT_APPLICABLE_LOCAL_ONLY','canonicalization_version':'ip01.json.sorted-utf8.v1'}
@pytest.mark.parametrize('component',list(CONSTANTS))
@pytest.mark.parametrize('phase',['retrieval','admission','release','consume'])
def test_static_binding_fault_fences_current_vector(lab,monkeypatch,component,phase):
    a,s=lab['a'],lab['store'];n=a.note('Static binding synthetic evidence');hold(lab);r,_=a.submit('Static dependency',[n['note_id']]);assert r.status_code==202
    vector=db_rows(s.path,'contexts')[0]['authority_vector'];before=copy.deepcopy(vector)
    with s.transaction(write=False) as tx:assert auth.check_current(tx,vector,phase=phase)['decision']=='ELIGIBLE_AT_CHECK'
    old=CONSTANTS[component];new=old+'.QA_FAULT'
    if component=='canonicalization_version':monkeypatch.setattr(auth,'CANONICALIZATION',new)
    else:
        fn=auth.make_vector;assert old in fn.__code__.co_consts
        code=fn.__code__.replace(co_consts=tuple(new if x==old else x for x in fn.__code__.co_consts));fault=types.FunctionType(code,fn.__globals__,fn.__name__,fn.__defaults__,fn.__closure__);monkeypatch.setattr(auth,'make_vector',fault)
    with s.transaction(write=False) as tx:
        with pytest.raises((Denied,ValidationError)) as outcome:auth.check_current(tx,vector,phase=phase)
    assert vector==before and not db_rows(s.path,'release_receipts')
    write(Path(os.environ['QA_RUN_DIR'])/(component+'-'+phase+'.json'),{'kind':'IN_MEMORY_STATIC_CONSTANT_FAULT','phase':phase,'component':component,'result_type':type(outcome.value).__name__,'denial':getattr(outcome.value,'code',None),'sealed_vector_unchanged':True,'candidate_file_modified':False,'live_HTTP_reconfiguration':False,'scope':'Direct actual current-vector computation with one literal/global changed in evaluator process; unsupported schema versions fail closed via ValidationError; not full route integration'})
