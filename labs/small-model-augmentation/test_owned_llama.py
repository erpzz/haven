import hashlib
import os
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import owned_llama


FAKE_SERVER = r'''#!/usr/bin/env python3
import http.server, json, os, sys, time
args=sys.argv[1:]
port=int(args[args.index("--port")+1])
alias=args[args.index("--alias")+1]
ctx=int(args[args.index("-c")+1])
if os.environ.get("FAKE_DELAY"):
    time.sleep(float(os.environ["FAKE_DELAY"]))
alias=os.environ.get("FAKE_ALIAS", alias)
ctx=int(os.environ.get("FAKE_CTX", ctx))
class H(http.server.BaseHTTPRequestHandler):
    protocol_version="HTTP/1.0"
    def log_message(self,*a): pass
    def sendj(self,obj):
        raw=json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path=="/v1/models":
            return self.sendj({"object":"list","data":[{"id":alias,"object":"model"}]})
        if self.path=="/props":
            return self.sendj({"default_generation_settings":{"n_ctx":ctx}})
        self.send_response(404); self.end_headers()
http.server.ThreadingHTTPServer(("127.0.0.1",port),H).serve_forever()
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def free_port():
    s=socket.socket()
    s.bind(("127.0.0.1",0))
    port=s.getsockname()[1]
    s.close()
    return port


class OwnerProbe:
    def __init__(self, mode="right"):
        self.mode=mode
        self.pid=None
    def __call__(self, port, pid):
        self.pid=pid
        if self.mode=="right": return {pid}
        if self.mode=="wrong": return {pid+1}
        if self.mode=="none": return set()
        return {pid}


class OwnedLlamaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.server=root/"fake-llama-server"
        self.server.write_text(FAKE_SERVER)
        self.server.chmod(self.server.stat().st_mode | stat.S_IXUSR)
        self.model=root/"model.gguf"
        self.model.write_bytes(b"fixture-model-bytes")
        self.server_sha=sha(self.server)
        self.model_sha=sha(self.model)

    def tearDown(self):
        self.tmp.cleanup()

    def launch(self, **kw):
        opts=dict(alias="fixture-model",port=free_port(),context_tokens=65536,
                  owner_probe=OwnerProbe(),start_timeout=3)
        opts.update(kw)
        return owned_llama.launch(str(self.server),self.server_sha,str(self.model),self.model_sha,**opts)

    def test_launch_binds_owned_child_hashes_and_runtime(self):
        lease=self.launch()
        try:
            self.assertTrue(lease.guard())
            self.assertIsNone(lease.process.poll())
            self.assertTrue(lease.endpoint_verified)
            self.assertTrue(lease.owner_verified)
        finally:
            lease.stop()
        self.assertIsNotNone(lease.process.poll())

    def test_wrong_model_hash_fails_before_launch(self):
        with self.assertRaises(owned_llama.LeaseError) as cm:
            owned_llama.launch(str(self.server),self.server_sha,str(self.model),"0"*64,
                               alias="fixture-model",port=free_port(),owner_probe=OwnerProbe())
        self.assertEqual(cm.exception.code,"FILE_HASH_MISMATCH")

    def test_wrong_server_hash_fails_before_launch(self):
        with self.assertRaises(owned_llama.LeaseError) as cm:
            owned_llama.launch(str(self.server),"1"*64,str(self.model),self.model_sha,
                               alias="fixture-model",port=free_port(),owner_probe=OwnerProbe())
        self.assertEqual(cm.exception.code,"FILE_HASH_MISMATCH")

    def test_preexisting_listener_blocks_without_reuse(self):
        s=socket.socket();s.bind(("127.0.0.1",0));s.listen(1)
        port=s.getsockname()[1]
        try:
            with self.assertRaises(owned_llama.LeaseError) as cm:
                self.launch(port=port)
            self.assertEqual(cm.exception.code,"PORT_ALREADY_IN_USE")
        finally:
            s.close()

    def test_wrong_listener_owner_blocks(self):
        probe=OwnerProbe("wrong")
        with self.assertRaises(owned_llama.LeaseError) as cm:
            self.launch(owner_probe=probe)
        self.assertEqual(cm.exception.code,"LISTENER_OWNER_MISMATCH")
        self.assertIsNotNone(probe.pid)

    def test_wrong_runtime_alias_blocks_and_stops_server(self):
        probe=OwnerProbe()
        with mock.patch.dict(os.environ,{"FAKE_ALIAS":"other-model"}):
            with self.assertRaises(owned_llama.LeaseError) as cm:
                self.launch(owner_probe=probe)
        self.assertEqual(cm.exception.code,"RUNTIME_ADMISSION_FAILED")

    def test_small_context_blocks(self):
        with mock.patch.dict(os.environ,{"FAKE_CTX":"8192"}):
            with self.assertRaises(owned_llama.LeaseError) as cm:
                self.launch()
        self.assertEqual(cm.exception.code,"RUNTIME_ADMISSION_FAILED")

    def test_start_timeout(self):
        with mock.patch.dict(os.environ,{"FAKE_DELAY":"2"}):
            with self.assertRaises(owned_llama.LeaseError) as cm:
                self.launch(start_timeout=.2)
        self.assertEqual(cm.exception.code,"SERVER_START_TIMEOUT")

    def test_server_file_change_invalidates_lease(self):
        lease=self.launch()
        try:
            self.server.write_text(FAKE_SERVER+"\n# changed\n")
            with self.assertRaises(owned_llama.LeaseError) as cm:
                lease.guard()
            self.assertEqual(cm.exception.code,"SERVER_FILE_CHANGED")
        finally:
            lease.stop()

    def test_model_file_change_invalidates_lease(self):
        lease=self.launch()
        try:
            self.model.write_bytes(b"changed")
            with self.assertRaises(owned_llama.LeaseError) as cm:
                lease.guard()
            self.assertEqual(cm.exception.code,"MODEL_FILE_CHANGED")
        finally:
            lease.stop()

    def test_run_guarded_success_and_cleanup(self):
        lease=self.launch()
        rc,error=owned_llama.run_guarded(
            lease,[sys.executable,"-c","raise SystemExit(0)"],guard_interval=.05)
        self.assertEqual((rc,error),(0,None))
        self.assertIsNotNone(lease.process.poll())

    def test_run_guarded_server_death_blocks(self):
        lease=self.launch()
        env=dict(os.environ,LEASE_SERVER_PID=str(lease.process.pid))
        cmd=[sys.executable,"-c",
             "import os,signal,time; os.kill(int(os.environ['LEASE_SERVER_PID']),signal.SIGTERM); time.sleep(10)"]
        started=time.monotonic()
        rc,error=owned_llama.run_guarded(lease,cmd,env=env,guard_interval=.05)
        self.assertEqual(error,"SERVER_EXITED")
        self.assertLess(time.monotonic()-started,4)
        self.assertIsNotNone(rc)

    def test_invalid_command_fails_closed_and_stops_lease(self):
        lease=self.launch()
        rc,error=owned_llama.run_guarded(lease,[],guard_interval=.05)
        self.assertEqual((rc,error),(None,"INVALID_COMMAND"))
        self.assertIsNotNone(lease.process.poll())

    def test_invalid_context_and_port_fail_closed(self):
        for kwargs,code in [
            ({"context_tokens":8192},"INVALID_CONTEXT"),
            ({"port":0},"INVALID_PORT"),
            ({"alias":"<MODEL>"},"INVALID_ALIAS"),
        ]:
            opts=dict(alias="fixture-model",port=free_port(),context_tokens=65536,owner_probe=OwnerProbe())
            opts.update(kwargs)
            with self.assertRaises(owned_llama.LeaseError) as cm:
                owned_llama.launch(str(self.server),self.server_sha,str(self.model),self.model_sha,**opts)
            self.assertEqual(cm.exception.code,code)

    def test_arbitrary_server_extra_args_are_rejected(self):
        marker=Path(self.tmp.name,"SHOULD_NOT_EXIST")
        with self.assertRaises(owned_llama.LeaseError) as cm:
            self.launch(extra_args=["--fake-unused",f";touch {marker}"])
        self.assertEqual(cm.exception.code,"SERVER_EXTRA_ARGS_NOT_ALLOWED")
        self.assertFalse(marker.exists())

    def test_security_critical_override_args_are_rejected(self):
        for args in (["-m","other.gguf"],["--host","0.0.0.0"],["--port","9999"],
                     ["-c","8192"],["--alias","same-looking-alias"]):
            with self.assertRaises(owned_llama.LeaseError) as cm:
                self.launch(extra_args=args)
            self.assertEqual(cm.exception.code,"SERVER_EXTRA_ARGS_NOT_ALLOWED")

    def test_invalid_guard_configuration_stops_lease(self):
        lease=self.launch()
        rc,error=owned_llama.run_guarded(
            lease,[sys.executable,"-c","pass"],guard_interval=.001)
        self.assertEqual((rc,error),(None,"INVALID_GUARD_INTERVAL"))
        self.assertIsNotNone(lease.process.poll())

        lease=self.launch()
        rc,error=owned_llama.run_guarded(
            lease,[sys.executable,"-c","pass"],cwd=Path(self.tmp.name,"missing"),
            guard_interval=.05)
        self.assertEqual((rc,error),(None,"INVALID_WORKING_DIRECTORY"))
        self.assertIsNotNone(lease.process.poll())

    def test_lsof_missing_is_fail_closed(self):
        with mock.patch.object(owned_llama.shutil,"which",return_value=None):
            with self.assertRaises(owned_llama.LeaseError) as cm:
                owned_llama.listener_pids_lsof(12345)
        self.assertEqual(cm.exception.code,"PORT_OWNER_TOOL_MISSING")

    def test_receipt_does_not_echo_paths_or_hashes(self):
        marker="PRIVATE_PATH_MARKER"
        r=owned_llama.receipt(["FILE_HASH_MISMATCH"])
        text=str(r)
        self.assertNotIn(marker,text)
        self.assertNotIn(self.model_sha,text)
        self.assertEqual(r["status"],"block")


if __name__=="__main__":
    unittest.main()
