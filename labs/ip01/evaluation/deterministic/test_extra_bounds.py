import io,os,random,copy
from pathlib import Path
from PIL import Image
import pytest
from common import key,db_rows,write
from test_functional import hold

def png(size):
    b=io.BytesIO();Image.new('RGB',size,'#346152').save(b,'PNG');return b.getvalue()
@pytest.mark.parametrize('extra',[0,1])
def test_raw_image_exact_2MiB(lab,extra):
    raw=png((12,12));raw+=b'\0'*(2*1024**2+extra-len(raw));r=lab['a'].request('POST','/api/images',content=raw,headers={'Content-Type':'image/png'});assert r.status_code==(201 if extra==0 else 413),r.text
@pytest.mark.parametrize('size',[(2000,4000),(1,8000001)])
def test_image_pixel_bound(lab,size):
    raw=png(size);r=lab['a'].request('POST','/api/images',content=raw,headers={'Content-Type':'image/png'});assert r.status_code==(201 if size[0]*size[1]==8000000 else 413),r.text
@pytest.mark.parametrize('extra',[0,1])
def test_derivative_guard_exact_8MiB(lab,monkeypatch,extra):
    raw=png((12,12));original=Image.Image.save
    def save(image,fp,format=None,**kw):
        original(image,fp,format,**kw)
        if isinstance(fp,io.BytesIO) and format=='PNG':fp.write(b'\0'*(8*1024**2+extra-fp.tell()))
    monkeypatch.setattr(Image.Image,'save',save)
    r=lab['a'].request('POST','/api/images',content=raw,headers={'Content-Type':'image/png'});assert r.status_code==(201 if extra==0 else 413),r.text
    write(Path(os.environ['QA_RUN_DIR'])/('derivative-'+str(extra)+'.json'),{'bytes':8*1024**2+extra,'status':r.status_code,'scope':'Private serializer-boundary fault injection after actual decode, exact guard exercise; not claim of a naturally normalized PNG at this byte size'})

def test_actual_encoded_derivative_below_and_above(lab):
    results=[]
    for side in (1000,2200):
        im=Image.frombytes('RGB',(side,side),random.Random(91).randbytes(side*side*3));encoded=io.BytesIO();im.save(encoded,'JPEG',quality=25)
        assert len(encoded.getvalue())<2*1024**2
        decoded=Image.open(io.BytesIO(encoded.getvalue())).convert('RGB');derivative=io.BytesIO();decoded.save(derivative,'PNG');size=len(derivative.getvalue())
        r=lab['a'].request('POST','/api/images',content=encoded.getvalue(),headers={'Content-Type':'image/jpeg'});assert r.status_code==(201 if size<=8*1024**2 else 413),r.text
        results.append({'encoded_bytes':len(encoded.getvalue()),'pixels':side*side,'independently_normalized_bytes':size,'http':r.status_code})
    assert results[0]['http']==201 and results[1]['http']==413,results
    write(Path(os.environ['QA_RUN_DIR'])/'natural-derivative.json',results)

@pytest.mark.parametrize('corruption',['cycle','missing_parent','corrupt_image'])
def test_corrupt_closure_and_image(lab,corruption):
    a,s=lab['a'],lab['store']
    if corruption=='corrupt_image':
        r=a.request('POST','/api/images',content=png((40,30)),headers={'Content-Type':'image/png'});assert r.status_code==201;sid=r.json()['source_id']
        (s.runtime_dir/'media'/(sid+'.png')).write_bytes(b'corrupt evaluator-owned derivative')
        assert a.request('GET','/api/images/'+sid+'/content').status_code==409
        r=a.request('POST','/api/answers',json={'question':'Image','route':'deterministic','image_source_id':sid,'source_ids':[],'destination_ref':a.destination,'idempotency_key':key()});assert r.status_code==409
    else:
        n=a.note('Synthetic corrupt closure');sid=n['note_id']
        with s.transaction(operation='qa-corrupt-source-fixture') as tx:
            row=tx.get('sources',sid);row['parents']=[{'id':sid if corruption=='cycle' else 'missing-source','revision':1}];tx.put('sources',sid,row)
        r,_=a.submit('Use source',[sid]);assert r.status_code in (404,409)
    assert not db_rows(s.path,'release_receipts')
