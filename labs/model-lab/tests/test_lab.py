import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from labcore import Lab,Job,OwnedEngine,endpoint,parse_smi,llama_command,estimate_fit,download_verified,safe_extract,atomic_json,finite_float,GIB
from server import Server
from fake_backend import FakeBackend

def done(lab,jid):
    end=time.monotonic()+8
    while time.monotonic()<end:
        j=lab.jobs[jid].snapshot()
        if j['state']!='RUNNING' and not lab.generation.locked():return j
        time.sleep(.03)
    raise AssertionError('Job failed to settle in test bound')
class UtilityTests(unittest.TestCase):
    def test_local_endpoint(self):self.assertEqual(endpoint('http://127.0.0.1:8080/v1'),('127.0.0.1',8080))
    def test_reject_remote(self):
        for v in ['http://localhost:8080','http://127.0.0.1.evil.com:8080','https://example.com','http://0.0.0.0:8080','http://127.0.0.1:8080/v1?x=1','http://user@127.0.0.1:8080','http://127.0.0.1:8080/admin','http://[::1]:8080']:
            with self.subTest(url=v),self.assertRaises(ValueError):endpoint(v)
    def test_numeric_nan_rejected(self):
        for v in [float('nan'),float('inf'),True,'0.7']:
            with self.subTest(v=v),self.assertRaises(ValueError):finite_float(v,0,2,'test')
    def test_smi(self):
        r=parse_smi('0, NVIDIA GeForce RTX 2070 SUPER, 8192, 1024, 7168, 55, 60, 120.3, 580.01\n')[0]
        self.assertEqual(r['memory_free_mib'],7168);self.assertEqual(r['utilization_pct'],55)
    def test_smi_unknown_not_zero(self):self.assertIsNone(parse_smi('0, GPU, 8192, N/A, N/A, N/A, N/A, N/A, 580\n')[0]['memory_used_mib'])
    def test_command_cuda(self):
        a=llama_command(Path('engine'),Path('model with spaces.gguf'),9000,Path('key'),{},0)
        self.assertEqual(a[a.index('--n-gpu-layers')+1],'999');self.assertIn('CUDA0',a);self.assertNotIn('--host 0.0.0.0',a)
    def test_command_injection_rejected(self):
        with self.assertRaises(ValueError):llama_command(Path('a'),Path('b'),9000,Path('key'),{'context':'4096 & calc'})
    def test_bad_cache_combo(self):
        with self.assertRaises(ValueError):llama_command(Path('a'),Path('b'),9000,Path('key'),{'kv':'q8_0','flash':'off'})
    def test_fit_is_heuristic(self):self.assertIn('Heuristic',estimate_fit(3*GIB,7000,4096)['basis'])
    def test_fit_unknown(self):self.assertEqual(estimate_fit(3*GIB,None,4096)['status'],'UNKNOWN')
    def test_atomic_unicode(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';atomic_json(p,{'x':'café'});self.assertEqual(json.loads(p.read_text(encoding='utf-8'))['x'],'café')
    def test_archive_zip_slip(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../outside.exe','bad')
            with self.assertRaises(ValueError):safe_extract(p,Path(t)/'out')
            self.assertFalse((Path(t)/'outside.exe').exists())
    def test_archive_size_guard(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('a','abc')
            with self.assertRaises(ValueError):safe_extract(p,Path(t)/'out',2)
class Response(io.BytesIO):
    def __init__(self,data,status=200,headers=None):super().__init__(data);self.status=status;self.headers=headers or {'Content-Length':str(len(data))}
class Opener:
    def __init__(self,data,status=200,headers=None):self.data=data;self.status=status;self.headers=headers;self.req=None
    def open(self,req,timeout):self.req=req;return Response(self.data,self.status,self.headers)
class DownloadTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'model.gguf';self.data=b'GGUFabcdef';self.h=hashlib.sha256(self.data).hexdigest()
    def tearDown(self):self.tmp.cleanup()
    def test_download_verified(self):
        download_verified('https://huggingface.co/x/y',self.p,self.h,len(self.data),Job('test'),opener=Opener(self.data),free_bytes=5*GIB)
        self.assertEqual(self.p.read_bytes(),self.data)
    def test_bad_hash_not_installed(self):
        with self.assertRaises(ValueError):download_verified('https://huggingface.co/x/y',self.p,'0'*64,len(self.data),Job('test'),opener=Opener(self.data),free_bytes=5*GIB)
        self.assertFalse(self.p.exists())
    def test_resume(self):
        self.p.with_suffix('.gguf.part').write_bytes(self.data[:4]);op=Opener(self.data[4:],206,{'Content-Range':f'bytes 4-{len(self.data)-1}/{len(self.data)}','Content-Length':str(len(self.data)-4)})
        download_verified('https://huggingface.co/x/y',self.p,self.h,len(self.data),Job('test'),opener=op,free_bytes=5*GIB)
        self.assertEqual(op.req.headers['Range'],'bytes=4-');self.assertEqual(self.p.read_bytes(),self.data)
    def test_server_ignores_range(self):
        self.p.with_suffix('.gguf.part').write_bytes(b'GGUF')
        download_verified('https://huggingface.co/x/y',self.p,self.h,len(self.data),Job('test'),opener=Opener(self.data),free_bytes=5*GIB)
        self.assertEqual(self.p.read_bytes(),self.data)
    def test_disk_guard(self):
        with self.assertRaises(ValueError):download_verified('https://huggingface.co/x/y',self.p,self.h,len(self.data),Job('test'),opener=Opener(self.data),free_bytes=10)
    def test_cancel_keeps_partial(self):
        j=Job('test');j.cancel()
        with self.assertRaises(InterruptedError):download_verified('https://huggingface.co/x/y',self.p,self.h,len(self.data),j,opener=Opener(self.data),free_bytes=5*GIB)
    def test_never_overwrite_wrong_existing(self):
        self.p.write_bytes(b'old')
        with self.assertRaises(ValueError):download_verified('https://huggingface.co/x/y',self.p,self.h,len(self.data),Job('test'),opener=Opener(self.data),free_bytes=5*GIB)
        self.assertEqual(self.p.read_bytes(),b'old')
class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.lab=Lab(Path(self.tmp.name));self.backend=FakeBackend();self.lab.connect(self.backend.base,kind='strata')
    def tearDown(self):self.lab.shutdown();self.backend.close();self.tmp.cleanup()
    def test_real_http_stream_fixture(self):
        j=done(self.lab,self.lab.generate({'messages':[{'role':'user','content':'Test'}]}))
        self.assertEqual(j['state'],'COMPLETED');self.assertIn('café ✓',j['text']);self.assertEqual(j['metrics']['completion_tokens'],12);self.assertEqual(j['metrics']['stream_chunks'],5)
        self.assertEqual(j['metrics']['backend_prompt_seconds'], .125)
        self.assertEqual(j['metrics']['backend_decode_seconds'], .44)
    def test_strata_reasoning_mapping(self):
        done(self.lab,self.lab.generate({'messages':[{'role':'user','content':'Test'}],'reasoning':'low'}));self.assertEqual(self.backend.requests[-1]['reasoning_effort'],'low')
    def test_llama_reasoning_mapping(self):
        self.lab.connection['kind']='llama';done(self.lab,self.lab.generate({'messages':[{'role':'user','content':'Test'}],'reasoning':'none'}));self.assertEqual(self.backend.requests[-1]['chat_template_kwargs'],{'enable_thinking':False})
    def test_benchmark_no_prompt_saved(self):
        done(self.lab,self.lab.generate({'messages':[{'role':'user','content':'DO_NOT_PERSIST_THIS_TEXT'}],'benchmark':True}))
        raw=(Path(self.tmp.name)/'benchmarks.jsonl').read_text();self.assertNotIn('DO_NOT_PERSIST_THIS_TEXT',raw);self.assertIn('prompt_sha256',raw);self.assertTrue(json.loads(raw)['test_double'])
    def test_benchmark_rejects_changed_connection_before_send(self):
        identity = self.lab.connection['connected_at']
        self.lab.connect(self.backend.base, kind='strata')
        request = {'messages':[{'role':'user','content':'Test'}], 'benchmark':True,
                   'expected_connected_at':identity}
        with self.assertRaisesRegex(ValueError, 'backend changed'):
            self.lab.generate(request)
        self.assertEqual(self.backend.requests, [])
        request['expected_connected_at'] = self.lab.connection['connected_at']
        result = done(self.lab, self.lab.generate(request))
        self.assertEqual(result['state'], 'COMPLETED')
        self.assertEqual(len(self.backend.requests), 1)
    def test_failure_no_retry(self):
        self.backend.fail_status=503;j=done(self.lab,self.lab.generate({'messages':[{'role':'user','content':'Test'}]}));self.assertEqual(j['state'],'FAILED');self.assertEqual(len(self.backend.requests),1)
    def test_truncated_retains_partial(self):
        self.backend.drop=True;j=done(self.lab,self.lab.generate({'messages':[{'role':'user','content':'Test'}]}));self.assertEqual(j['state'],'FAILED');self.assertTrue(j['text'])
    def test_cancel(self):
        self.backend.slow=True;jid=self.lab.generate({'messages':[{'role':'user','content':'Test'}]});time.sleep(.12);self.lab.jobs[jid].cancel();j=done(self.lab,jid);self.assertEqual(j['state'],'CANCELLED');self.assertEqual(len(self.backend.requests),1)
    def test_one_request_slot(self):
        self.backend.slow=True;j=self.lab.generate({'messages':[{'role':'user','content':'Test'}]})
        with self.assertRaises(ValueError):self.lab.generate({'messages':[{'role':'user','content':'Another'}]})
        self.lab.jobs[j].cancel();done(self.lab,j)
    def test_reconnect_rejects_active_request(self):
        self.backend.slow=True;j=self.lab.generate({'messages':[{'role':'user','content':'Test'}]})
        try:
            with self.assertRaises(ValueError):self.lab.connect(self.backend.base)
        finally:self.lab.jobs[j].cancel();done(self.lab,j)
    def test_connect_commit_rechecks_request_started_during_probe(self):
        entered = threading.Event(); release = threading.Event(); failures = []
        identity = self.lab.connection['connected_at']
        def probe(*args, **kwargs):
            entered.set()
            if not release.wait(3): raise TimeoutError('Fixture probe not released')
            return {'data':[{'id':'TEST_DOUBLE'}]}
        def reconnect():
            try: self.lab.connect(self.backend.base, kind='strata')
            except Exception as error: failures.append(error)
        self.backend.slow = True
        with patch('labcore.local_json', side_effect=probe):
            thread = threading.Thread(target=reconnect); thread.start()
            self.assertTrue(entered.wait(3))
            jid = self.lab.generate({'messages':[{'role':'user','content':'Test'}]})
            try:
                release.set(); thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(len(failures), 1)
                self.assertIn('ownership changed', str(failures[0]))
                self.assertEqual(self.lab.connection['connected_at'], identity)
            finally:
                release.set(); self.lab.jobs[jid].cancel(); done(self.lab,jid); thread.join(3)
    def test_terminal_status_includes_metrics(self):
        jid=self.lab.generate({'messages':[{'role':'user','content':'Test'}]})
        deadline=time.monotonic()+5
        while self.lab.jobs[jid].snapshot()['state']=='RUNNING' and time.monotonic()<deadline:time.sleep(.005)
        self.assertIn('metrics',self.lab.jobs[jid].snapshot());self.assertFalse(self.lab.generation.locked())
    def test_output_limit_preserves_backend_finish_reason_and_default_limit(self):
        self.backend.finish_reason='length'
        jid=self.lab.generate({'messages':[{'role':'user','content':'Test'}]})
        j=done(self.lab,jid)
        self.assertEqual(j['state'],'OUTPUT_LIMIT')
        self.assertEqual(j['finish_reason'],'length')
        self.assertEqual(self.backend.requests[-1]['max_tokens'],2048)
        self.assertFalse(self.lab.generation.locked())
    def test_unload_serializes_replacement_load_and_preserves_new_connection(self):
        # No child is launched: only the public ownership transitions execute.
        stopped = threading.Event(); release = threading.Event()
        load_attempted = threading.Event(); launched = threading.Event()
        failures, jobs = [], []
        class BenignProcess:
            def poll(self): return None
        old, replacement = BenignProcess(), BenignProcess()
        self.lab.engine.proc = old
        self.lab.connection['ownership'] = 'OWNED'
        model = Path(self.tmp.name) / 'replacement.gguf'; model.write_bytes(b'GGUFtest')
        self.lab.settings['models']['replacement'] = {
            'path':str(model), 'name':'BENIGN REPLACEMENT', 'size_bytes':model.stat().st_size}

        def stop(expected=None):
            self.assertIs(self.lab.engine.proc, old)
            stopped.set()
            if not release.wait(3): raise TimeoutError('Fixture unload was not released')
            self.lab.engine.proc = None
            return {'state':'STOPPED'}

        def launch(*args, **kwargs):
            self.lab.engine.proc = replacement
            launched.set()

        def unload():
            try: self.lab.stop_engine()
            except Exception as error: failures.append(error)

        def load():
            load_attempted.set()
            try: jobs.append(self.lab.start_llama('replacement', 'balanced'))
            except Exception as error: failures.append(error)

        threads = [threading.Thread(target=unload), threading.Thread(target=load)]
        with patch.object(self.lab.engine, 'stop', side_effect=stop), \
                patch.object(self.lab.engine, 'launch', side_effect=launch), \
                patch.object(self.lab, 'llama_exe', return_value=Path('benign-unused.exe')), \
                patch.object(self.lab, 'get_hardware', return_value={
                    'gpus':[{'index':0,'memory_free_mib':8192}]}), \
                patch('labcore.local_json', return_value={'data':[{'id':'haven-local'}]}):
            try:
                threads[0].start(); self.assertTrue(stopped.wait(3))
                # Deterministic regression: the old implementation leaves this
                # lock free during engine.stop, allowing a later load to race it.
                acquired = self.lab.lock.acquire(blocking=False)
                if acquired: self.lab.lock.release()
                self.assertFalse(acquired, 'Unload must serialize the ownership transition')
                threads[1].start(); self.assertTrue(load_attempted.wait(3))
                self.assertFalse(launched.is_set())
                release.set()
                for thread in threads:
                    thread.join(3); self.assertFalse(thread.is_alive())
                self.assertFalse(failures)
                self.assertEqual(len(jobs), 1)
                self.assertEqual(done(self.lab, jobs[0])['state'], 'COMPLETED')
                self.assertIs(self.lab.engine.proc, replacement)
                connection = dict(self.lab.connection)
                self.assertEqual(connection['display_model'], 'BENIGN REPLACEMENT')
                with self.assertRaisesRegex(ValueError, 'Use Unload'):
                    self.lab.disconnect()
                self.assertEqual(self.lab.connection, connection)
            finally:
                release.set()
                for thread in threads:
                    if thread.ident is not None: thread.join(3)
                self.lab.engine.proc = None
                self.lab.connection = None
    def test_no_backend_key_in_state(self):
        self.lab.connection['key']='private-test-secret';self.assertNotIn('private-test-secret',json.dumps(self.lab.public_state()))
    def test_no_image_unsupported(self):
        with self.assertRaises(ValueError):self.lab.generate({'messages':[{'role':'user','content':[{'type':'image_url'}]}]})
    def test_external_survives_shutdown(self):
        self.lab.shutdown();conn=http.client.HTTPConnection('127.0.0.1',self.backend.server_port,timeout=1);conn.request('GET','/v1/models');r=conn.getresponse();self.assertEqual(r.status,200);r.read();conn.close()
    def test_import_is_explicit_and_no_copy(self):
        p=Path(self.tmp.name)/'x.gguf';p.write_bytes(b'GGUFtest');r=self.lab.import_model(str(p));self.assertEqual(Path(self.lab.settings['models'][r['id']]['path']),p.resolve());self.assertFalse((Path(self.tmp.name)/'models/x.gguf').exists())
class HttpSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.lab=Lab(Path(self.tmp.name));self.server=Server(('127.0.0.1',0),self.lab);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join(2);self.lab.shutdown();self.tmp.cleanup()
    def request(self,path,method='GET',body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3);c.request(method,path,body=body,headers=headers or {});r=c.getresponse();out=(r.status,r.read(),r.getheaders());c.close();return out
    def test_requires_token(self):self.assertEqual(self.request('/api/state')[0],401)
    def test_static_loads(self):self.assertEqual(self.request('/')[0],200)
    def test_no_directory_read(self):self.assertEqual(self.request('/../labcore.py')[0],404)
    def test_host_denied(self):self.assertEqual(self.request('/',headers={'Host':'evil.example'})[0],403)
    def test_origin_denied(self):self.assertEqual(self.request('/api/state',headers={'X-Lab-Token':self.lab.token,'Origin':'https://evil.example'})[0],403)
    def test_token_allows(self):self.assertEqual(self.request('/api/state',headers={'X-Lab-Token':self.lab.token})[0],200)
    def test_no_cors(self):self.assertEqual(self.request('/api/state','OPTIONS')[0],403)
    def test_bad_json(self):self.assertEqual(self.request('/api/connect','POST','[]',{'X-Lab-Token':self.lab.token,'Content-Type':'application/json'})[0],400)
    def test_download_requires_confirmation(self):self.assertEqual(self.request('/api/model/download','POST','{"id":"qwen35-4b"}',{'X-Lab-Token':self.lab.token,'Content-Type':'application/json'})[0],400)
class ProcessTests(unittest.TestCase):
    def test_owned_start_stop_and_double_start_rejection(self):
        with tempfile.TemporaryDirectory() as t:
            e=OwnedEngine(Path(t));e.launch([sys.executable,'-c','import time; time.sleep(30)'],Path(t),label='BENIGN TEST')
            p=e.proc
            with self.assertRaises(ValueError):e.launch([sys.executable,'-c','pass'],Path(t),label='duplicate')
            r=e.stop();self.assertEqual(r['state'],'STOPPED');self.assertIsNotNone(p.poll())
    def test_old_owner_cannot_stop_new_engine(self):
        with tempfile.TemporaryDirectory() as t:
            e=OwnedEngine(Path(t));e.launch([sys.executable,'-c','import time; time.sleep(20)'],Path(t),label='BENIGN A')
            old=e.proc;e.stop()
            try:
                e.launch([sys.executable,'-c','import time; time.sleep(20)'],Path(t),label='BENIGN B')
                self.assertEqual(e.stop(expected=old)['state'],'NOT_CURRENT_OWNER')
                self.assertIsNone(e.proc.poll())
            finally:e.stop()
    def test_exited_gate_still_requires_stop(self):
        with tempfile.TemporaryDirectory() as t:
            e=OwnedEngine(Path(t));e.launch([sys.executable,'-c','pass'],Path(t),label='BENIGN TEST')
            try:
                deadline=time.monotonic()+3
                while e.status()['state']!='PROCESS_EXITED' and time.monotonic()<deadline: time.sleep(.02)
                self.assertEqual(e.status()['state'],'PROCESS_EXITED')
            finally:
                self.assertEqual(e.stop()['state'],'STOPPED')
if __name__=='__main__':unittest.main()
