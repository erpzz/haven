"""Independent QA support. Synthetic data only; never sends a model request."""
import hashlib,json,os,sqlite3,time,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path

BASE=Path(__file__).resolve().parent
CONFIG=json.loads((BASE/'selected.json').read_text())
SNAP=Path(CONFIG['snapshot']);SOURCE=Path(CONFIG['source'])
PUBLIC=BASE/'reports'

def key():return 'qa-'+uuid.uuid4().hex
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def write(p,x):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def source_fingerprint():
    return {p:sha((SOURCE/p).read_bytes()) for p in CONFIG['files']}
def db_rows(path,table):
    assert table in ('meta','sessions','sources','source_revisions','grants','quota_ledger','grant_use_claims','drafts','jobs','contexts','attempts','events','outputs','release_receipts','consumption_receipts','delivery_observations','eligibility_decisions','operations','changes','recovery')
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=2) as db:
        db.execute('PRAGMA query_only=ON')
        if table=='meta':return {k:json.loads(v) for k,v in db.execute('SELECT key,value FROM meta')}
        return [json.loads(row[0]) for row in db.execute('SELECT body FROM '+table+' ORDER BY rowid')]
def no_payload(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k in ('payload','answer_text','generated_text','usable_permit'):assert v in (None,False,''),k
            no_payload(v)
    if isinstance(x,list):
        for v in x:no_payload(v)

class Actor:
    def __init__(self,client,person,base='http://127.0.0.1:8766'):
        self.client=client;self.base=base;self.person=person
        r=client.get('/api/session');assert r.status_code==200,r.text
        self.csrf=r.json()['csrf_token']
        r=self.request('POST','/api/session',json={'person':person});assert r.status_code==200,r.text
        session=r.json();self.csrf=session['csrf_token'];self.destination=session['destination_ref']
    def request(self,method,path,**kw):
        headers={'Origin':self.base,'X-CSRF-Token':self.csrf};headers.update(kw.pop('headers',{}))
        return self.client.request(method,path,headers=headers,**kw)
    def note(self,text,title='Independent synthetic note',parents=None):
        r=self.request('POST','/api/notes',json={'text':text,'title':title,'parents':parents or [],'idempotency_key':key()});assert r.status_code==201,r.text
        return r.json()
    def edit(self,note,text):
        r=self.request('PATCH','/api/notes/'+note['note_id'],json={'title':'Independent edited note','text':text,'expected_revision':note['revision']});assert r.status_code==200,r.text
        return r.json()
    def share(self,note,uses=1):
        r=self.request('POST','/api/notes/'+note['note_id']+'/grants',json={'recipient':'B','purpose':'answer','expires_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'max_uses':uses,'idempotency_key':key()});assert r.status_code==201,r.text
        return r.json()
    def revoke(self,g):
        r=self.request('POST','/api/grants/'+g['grant_id']+'/revoke',json={'expected_revision':g['authorization_revision']});assert r.status_code==200,r.text
        return r.json()
    def submit(self,question,sources=None,operation=None):
        request={'question':question,'route':'deterministic','source_ids':sources,'idempotency_key':operation or key(),'destination_ref':self.destination}
        r=self.request('POST','/api/answers',json=request);return r,request
    def wait(self,job):
        end=time.monotonic()+5
        while time.monotonic()<end:
            r=self.request('GET',job['status_url']);assert r.status_code==200,r.text
            value=r.json();no_payload(value)
            if value['disposition'] in ('SUCCEEDED','FAILED','CANCELLED','INCONCLUSIVE'):return value
            time.sleep(.01)
        raise AssertionError('deterministic job remained queued')
    def answer(self,question,sources=None,operation=None):
        r,req=self.submit(question,sources,operation);assert r.status_code==202,r.text
        return self.wait(r.json()),r.json(),req
    def consume(self,state,operation=None,**overrides):
        o=state['output'];body={k:o[k] for k in ('release_id','output_digest','destination_ref','nonce')};body['idempotency_key']=operation or key();body.update(overrides)
        return self.request('POST','/api/outputs/'+o['output_id']+'/consume',json=body),body
    def fresh_payload(self,state):
        r,_=self.consume(state);assert r.status_code==200 and r.json()['status']=='FRESH_CONSUMPTION',r.text
        return r.json()
