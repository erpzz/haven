"""Repeatable private preparation only. No generate/chat/embed/load endpoints.

Run with the campaign venv, -B, and PYTHONPATH=labs/ip01. Preserves each attempt.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import urllib.request

from haven.model_adapter import ModelAdapter, MODEL, ENVELOPE, PROMPT_PREFIX, PROMPT_VERSION, sha_file, request_json
from haven.supervisor import OwnedJob, canonical


def fetch(url, limit=1024*1024):
    with urllib.request.urlopen(url, timeout=30) as response:
        data=response.read(limit+1)
    if len(data)>limit: raise RuntimeError("preparation metadata bound")
    return data


async def main(phase, root):
    adapter=ModelAdapter(root)
    directory=adapter.directory
    attempt=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+'-'+phase
    evidence=directory/"preparation"/attempt
    evidence.mkdir(parents=True,exist_ok=False)
    record={"phase":phase,"model_calls":0,"started_utc":datetime.now(timezone.utc).isoformat()}
    owned=OwnedJob()
    server=None
    try:
        server=await adapter.launch_owned_server(owned,time.monotonic()+20)
        record.update(backend=server["identity"],version=server["version"],url=server["url"],
                      before_stop=owned.observation())
        if phase=='acquire':
            probes=list((directory/'preparation').glob('*-probe/receipt.json'))
            if not any(json.loads(p.read_text()).get('cleanup',{}).get('confirmed') and
                       json.loads(p.read_text()).get('status') == 'PREPARED_NO_INFERENCE' for p in probes):
                raise RuntimeError('demonstrated own backend stop required before acquisition')
            manifest_raw=(directory/'remote-manifest.json').read_bytes()
            manifest=json.loads(manifest_raw)
            blobs=[manifest['config']]+manifest['layers']
            total=sum(x['size'] for x in blobs)
            existing=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
            if total+1024**3>12*1024**3 or existing+total>20*1024**3:
                raise RuntimeError('acquisition/storage ceiling')
            if shutil.disk_usage(root).free-total<10*1024**3:
                raise RuntimeError('retained free disk ceiling')
            upstream='https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct'
            metadata=json.loads(await asyncio.to_thread(fetch,'https://huggingface.co/api/models/Qwen/Qwen2.5-VL-3B-Instruct'))
            revision=metadata['sha']
            license_bytes=await asyncio.to_thread(fetch,upstream+'/raw/'+revision+'/LICENSE')
            if b'Qwen RESEARCH LICENSE AGREEMENT' not in license_bytes or b'NON-COMMERCIAL' not in license_bytes:
                raise RuntimeError('unexpected upstream rights; stop acquisition')
            (evidence/'upstream-LICENSE.txt').write_bytes(license_bytes)
            configs={}
            for name in ('preprocessor_config.json','config.json','tokenizer_config.json'):
                raw=await asyncio.to_thread(fetch,upstream+'/raw/'+revision+'/'+name)
                (evidence/name).write_bytes(raw)
                configs[name]=hashlib.sha256(raw).hexdigest()
            record['rights']={'upstream_revision':revision,'upstream_license_sha256':hashlib.sha256(license_bytes).hexdigest(),
                              'registry_license_sha256':next(x['digest'].split(':')[1] for x in blobs if x['mediaType'].endswith('.license')),
                              'scope':'private noncommercial synthetic research/evaluation only',
                              'mismatch':'Registry packages Apache-2.0; upstream 3B Research License retained as restrictive constraint. No redistribution.'}
            def pull():
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                req=urllib.request.Request(server['url']+'/api/pull',data=json.dumps({'model':MODEL,'stream':True}).encode(),
                                           headers={'Content-Type':'application/json'})
                latest=0;success=False;start=time.monotonic()
                with opener.open(req,timeout=45) as response,open(evidence/'pull.jsonl','ab',buffering=0) as log:
                    while True:
                        if time.monotonic()-start>900:raise TimeoutError('fixed acquisition wall cap')
                        line=response.readline(65537)
                        if not line:break
                        if len(line)>65536:raise RuntimeError('pull frame limit')
                        entry=json.loads(line);log.write(canonical(entry)+b'\n')
                        if 'error' in entry:raise RuntimeError('official pull returned error')
                        if entry.get('completed',0)-latest>256*1024**2:
                            latest=entry['completed'];print(json.dumps({'download_completed_bytes':latest}),flush=True)
                        if entry.get('status')=='success':success=True
                if not success:raise RuntimeError('pull incomplete')
            await asyncio.to_thread(pull)
            local=directory/'models/manifests/registry.ollama.ai/library/qwen2.5vl/3b'
            if sha_file(local)!=hashlib.sha256(manifest_raw).hexdigest():
                raise RuntimeError('mutable tag changed during acquisition; no inference')
            for blob in blobs:
                path=directory/'models/blobs'/blob['digest'].replace(':','-')
                if path.stat().st_size!=blob['size'] or sha_file(path)!=blob['digest'].split(':')[1]:
                    raise RuntimeError('downloaded blob verification failed')
            show=await asyncio.to_thread(request_json,server['url']+'/api/show',{'model':MODEL,'verbose':False})
            (evidence/'show.json').write_bytes(canonical(show))
            runtime_hash=sha_file(adapter.installed_binary())
            runtime_root=adapter.installed_binary().parent
            runtime_files=[{'path':f.relative_to(runtime_root).as_posix(),'bytes':f.stat().st_size,'sha256':sha_file(f)}
                           for f in sorted((runtime_root/'lib'/'ollama').rglob('*')) if f.is_file()]
            runtime_files_hash=hashlib.sha256(canonical(runtime_files)).hexdigest()
            (evidence/'runtime-files.json').write_bytes(canonical(runtime_files))
            processor={'profile':'ip01.ollama-native-qwen25vl.v1','upstream_revision':revision,
                       'upstream_reference_configs':configs,'runtime_sha256':runtime_hash,
                       'runtime_files_sha256':runtime_files_hash,
                       'model_blob_sha256':next(x['digest'] for x in blobs if x['mediaType'].endswith('.model')),
                       'application_input':'APP-reviewed normalized PNG/JPEG bytes; actual derivative SHA256 on each context',
                       'effective_runtime_transform':'compiled Ollama native qwen25vl; identity pinned, empirical image admission untested'}
            (evidence/'preprocessor.json').write_bytes(canonical(processor))
            identity={'model':MODEL,'manifest_sha256':sha_file(local),'blobs':blobs,
                      'runtime_version':server['version'],'runtime_sha256':runtime_hash,
                      'runtime_files':runtime_files,'runtime_files_sha256':runtime_files_hash,
                      'template_sha256':next(x['digest'].split(':')[1] for x in blobs if x['mediaType'].endswith('.template')),
                      'license_sha256':record['rights']['registry_license_sha256'],
                      'upstream_license_sha256':record['rights']['upstream_license_sha256'],
                      'preprocessor_sha256':hashlib.sha256(canonical(processor)).hexdigest(),
                      'prompt_version':PROMPT_VERSION,'prompt_sha256':hashlib.sha256(PROMPT_PREFIX.encode()).hexdigest(),
                      'envelope':ENVELOPE,'rights':record['rights'],'cleanup_readiness':'PENDING_STOP',
                      'generation_calls':0,'show_sha256':sha_file(evidence/'show.json'),
                      'model_bytes':total,'quantization':show.get('details',{}).get('quantization_level')}
            record['identity']=identity
        record['status']='PREPARED_NO_INFERENCE'
    except BaseException as exc:
        record.update(status='FAILED_RETAINED',exception_type=type(exc).__name__,error=str(exc))
        raise
    finally:
        record['owned_processes']=[p.identity for p in owned.processes]
        cleanup=await owned.stop()
        record['cleanup']=cleanup
        if server:
            await asyncio.gather(server['drain_task'],return_exceptions=True)
        for process in owned.processes:process.close()
        owned.close()
        if record.get('identity') and cleanup['confirmed']:
            record['identity']['cleanup_readiness']='BENIGN_OWNED_BACKEND_STOP_CONFIRMED'
            (directory/'identity.json').write_bytes(canonical(record['identity']))
        record['finished_utc']=datetime.now(timezone.utc).isoformat()
        (evidence/'receipt.json').write_bytes(canonical(record))
        print(json.dumps({'phase':phase,'status':record.get('status'),'cleanup':cleanup,'evidence':str(evidence),'model_calls':0}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['probe','acquire'])
    parser.add_argument('--runtime-dir',type=Path,required=True)
    args=parser.parse_args()
    asyncio.run(main(args.phase,args.runtime_dir.resolve()))
