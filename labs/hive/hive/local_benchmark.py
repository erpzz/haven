"""Real two-worker vs monolithic CPU benchmark; no Qwythos or WAN assertions.

Run: python -m hive.local_benchmark --samples 5 --delay-ms 0 --output /tmp/hive-receipt.json
--delay-ms injects *synthetic* latency on the network operation, separately labelled.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import secrets
import socket
import statistics
import subprocess
import sys
import tempfile
import time

import torch
from .model import Spec, Endpoints, Segment
from .cluster import Cluster
from .wire import load_secret, request


def _port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _baseline(ends, segment, prompt, count):
    ids=list(prompt)
    output=[]
    with torch.inference_mode():
        for _ in range(count):
            token=ends.predict(segment(ends.embed(ids)))
            ids.append(token)
            output.append(token)
    return output


def execute(samples=5, delay_ms=0.0):
    """Measures actual local processes and optionally a *labelled synthetic* link delay."""
    if not 2 <= samples <= 50 or not 0 <= delay_ms <= 500:
        raise ValueError('Bounded 2..50 samples and 0..500ms synthetic delay')
    torch.set_num_threads(1)
    spec=Spec(layers=4, dim=32, heads=4, context=32)
    prompt=b'HIVE'
    count=4
    ends=Endpoints(spec)
    segment=Segment(spec, 0, spec.layers)
    with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
        keyfile=Path(temp)/'secret'
        fd=os.open(keyfile, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd,'w') as f: f.write(secrets.token_urlsafe(48)+'\n')
        key=load_secret(str(keyfile))
        peers=[]
        processes=[]
        for start,stop in [(0,2),(2,4)]:
            port=_port()
            process=subprocess.Popen([sys.executable,'-m','hive','worker','--port',str(port),
                '--start',str(start),'--stop',str(stop),'--secret-file',str(keyfile),
                '--layers','4','--dim','32','--heads','4','--context','32'],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL)
            processes.append(process)
            peers.append(f'127.0.0.1:{port}')
        def terminate():
            for p in processes:
                if p.poll() is None:p.terminate()
            for p in processes:
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill();p.wait()
        stack.callback(terminate)
        for peer,p in zip(peers,processes):
            for _ in range(100):
                if p.poll() is not None:raise RuntimeError('Worker exited prematurely')
                try:
                    request(peer,key,'/meta',timeout=.2)
                    break
                except Exception:
                    time.sleep(.05)
            else:raise RuntimeError('Worker did not start')
        cluster=Cluster(spec, peers, key)
        # Delay is synthetic and applies to each of 2 stage forwards for every token.
        import hive.cluster as cluster_module
        original=cluster_module.request
        if delay_ms:
            def delayed(*args,**kwargs):
                if len(args)>=3 and args[2]=='/forward':time.sleep(delay_ms/1000)
                return original(*args,**kwargs)
            cluster_module.request=delayed
            stack.callback(lambda: setattr(cluster_module,'request',original))
        # Warm both paths, then measure each path in alternating order.
        truth=_baseline(ends,segment,prompt,count)
        if cluster.generate(prompt,count)['tokens'] != truth:
            raise AssertionError('Cross-process output does not match baseline')
        monolith=[]; distributed=[]
        for i in range(samples):
            if i%2:
                t=time.perf_counter();r=cluster.generate(prompt,count);distributed.append((time.perf_counter()-t)*1000)
                t=time.perf_counter();m=_baseline(ends,segment,prompt,count);monolith.append((time.perf_counter()-t)*1000)
            else:
                t=time.perf_counter();m=_baseline(ends,segment,prompt,count);monolith.append((time.perf_counter()-t)*1000)
                t=time.perf_counter();r=cluster.generate(prompt,count);distributed.append((time.perf_counter()-t)*1000)
            if m != r['tokens'] or m != truth:
                raise AssertionError('Mismatch during benchmark')
        return {
            'status':'MEASURED_REAL_LOCAL_EXECUTION',
            'model_kind':'random_initialized_toy_transformer_NOT_QWYTHOS',
            'network_kind':'LOCAL_LOOPBACK_WITH_SYNTHETIC_DELAY' if delay_ms else 'LOCAL_LOOPBACK',
            'distinct_physical_hosts':1,'physical_gpus':0,'worker_processes':2,
            'samples':samples,'new_tokens_per_request':count,
            'injected_ms_per_forward':delay_ms,'forwards_per_token':2,
            'monolithic_ms_samples':[round(x,3) for x in monolith],
            'distributed_ms_samples':[round(x,3) for x in distributed],
            'monolithic_median_ms':round(statistics.median(monolith),3),
            'distributed_median_ms':round(statistics.median(distributed),3),
            'median_slowdown':round(statistics.median(distributed)/statistics.median(monolith),3),
            'tokens_equal':True,
            'weights_type':'random_untrained',
            'future_qwythos_status':'NOT_EXECUTED',
        }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--samples',type=int,default=5)
    p.add_argument('--delay-ms',type=float,default=0.0)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    report=execute(a.samples,a.delay_ms)
    data=json.dumps(report,indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(data+'\n',encoding='utf8')
    print(data)

if __name__=='__main__':main()
