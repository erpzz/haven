#!/usr/bin/env python3
"""Owner-enabled Mac Metal worker and reversible private SSH enrollment.

No cloud, LAN listener, model download, remote shell tools, or model-selected
commands. A user LaunchAgent supervises only the fixed prepared local runtime.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import secrets
import socket
import stat
import subprocess
import sys
import time
import uuid

STATE = Path.home() / '.local/state/haven-worker'
MODEL = Path.home() / '.local/share/haven-worker/models/SmolLM2-1.7B-Instruct-Q4_K_M.gguf'
EXE = Path('/opt/homebrew/Cellar/llama.cpp/0.7.0/bin/llama-server')
DIGEST = '77665ea4815999596525c636fbeb56ba8b080b46ae85efef4f0d986a139834d7'
LABEL = 'com.haven.mac-worker'
PLIST = Path.home() / 'Library/LaunchAgents/com.haven.mac-worker.plist'
SOCKET = Path.home() / '.ssh/haven-worker.sock'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8']


def run(*argv, check=True, **kwargs):
    return subprocess.run(argv, check=check, capture_output=True, text=True, **kwargs)


def prepare():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    meta = STATE.lstat()
    if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_mode & 0o077:
        raise ValueError('The worker state directory must be private and owned.')
    if not EXE.is_file() or not MODEL.is_file() or MODEL.stat().st_size != 1055609824:
        raise ValueError('The explicitly prepared pinned runtime/model is missing; no download was attempted.')
    receipt = STATE / 'artifact.json'
    current = {'model_sha256': DIGEST, 'size': MODEL.stat().st_size, 'mtime_ns': MODEL.stat().st_mtime_ns}
    if not receipt.exists() or json.loads(receipt.read_text()) != current:
        digest = hashlib.sha256()
        with MODEL.open('rb') as f:
            for block in iter(lambda: f.read(4 * 1024**2), b''): digest.update(block)
        if digest.hexdigest() != DIGEST:
            raise ValueError('Prepared model checksum mismatch; nothing started.')
        receipt.write_text(json.dumps(current) + '\n')
    for name, value in [('api-key', secrets.token_urlsafe(48)), ('node-id', str(uuid.uuid4()))]:
        path = STATE / name
        if not path.exists():
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'w') as f: f.write(value + '\n')
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_mode & 0o077:
            raise ValueError('Worker identity/credential must be private owned regular files.')


def serve():
    prepare()
    # Conservative short-context worker, never an automatic 16-GB model load.
    pressure = run('/usr/bin/memory_pressure', '-Q').stdout
    import re
    match = re.search(r'memory free percentage: (\d+)%', pressure)
    if not match or int(match[1]) < 25:
        raise ValueError('Mac memory headroom is low/unknown. Worker remains stopped.')
    argv = [str(EXE), '--model', str(MODEL), '--host', '127.0.0.1', '--port', '8890',
            '--api-key-file', str(STATE / 'api-key'), '--alias', 'haven-mac-smollm2',
            '--n-gpu-layers', '999', '--device', 'MTL0', '--ctx-size', '2048', '--parallel', '1', '--threads', '4',
            '--batch-size', '128', '--ubatch-size', '64', '--jinja', '--metrics', '--offline',
            '--no-webui', '--no-webui-mcp-proxy', '--no-context-shift', '--log-verbosity', '4']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('LLAMA_', 'OPENAI_', 'ANTHROPIC_', 'HF_', 'HUGGING_FACE_', 'DYLD_'))}
    os.execve(EXE, argv, env)


def enable():
    prepare()
    # LaunchAgents cannot read Documents under macOS privacy policy. Install
    # our own service program under the private application directory; it never
    # requests Documents access or a Full Disk Access grant.
    library = Path.home() / '.local/lib/haven-worker'
    library.mkdir(parents=True, exist_ok=True, mode=0o700)
    helper = library / 'mac-worker.py'
    if helper.resolve() != Path(__file__).resolve():
        helper.write_bytes(Path(__file__).read_bytes()); helper.chmod(0o700)
    # Refuse an existing service definition unless it is exactly ours.
    config = {'Label': LABEL, 'ProgramArguments': [sys.executable, str(helper), 'serve'],
              'RunAtLoad': True, 'KeepAlive': False, 'ProcessType': 'Background',
              'StandardOutPath': str(STATE / 'worker.log'), 'StandardErrorPath': str(STATE / 'worker.log')}
    content = plistlib.dumps(config)
    if PLIST.exists() and PLIST.read_bytes() != content:
        raise ValueError('An existing worker LaunchAgent differs; it was preserved.')
    run('launchctl', 'enable', 'gui/' + str(os.getuid()) + '/' + LABEL)
    active = run('launchctl', 'print', 'gui/' + str(os.getuid()) + '/' + LABEL, check=False)
    if active.returncode == 0:
        if 'state = running' not in active.stdout:
            run('launchctl', 'kickstart', 'gui/' + str(os.getuid()) + '/' + LABEL)
        print('Worker LaunchAgent already registered; no duplicate was started.'); return
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', 8890)) == 0:
            raise ValueError('Mac loopback port 8890 is occupied; nothing was stopped.')
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(content); PLIST.chmod(0o600)
    run('launchctl', 'bootstrap', 'gui/' + str(os.getuid()), str(PLIST))
    print('Owner-enabled worker LaunchAgent registered on loopback only.')


def enroll():
    prepare()
    import shlex
    remote_dir = "import os,pathlib; os.umask(0o077); p=pathlib.Path.home()/'.local/state/haven-model-lab/providers'; p.mkdir(parents=True,exist_ok=True,mode=0o700); print(p/'macbook-owner.sock')"
    remote_socket = run(*SSH, 'haven', 'python3 -c ' + shlex.quote(remote_dir)).stdout.strip()
    if not remote_socket.startswith('/') or '\n' in remote_socket:
        raise ValueError('Invalid private remote socket path.')
    check = run(*SSH, '-S', str(SOCKET), '-O', 'check', 'haven', check=False)
    if check.returncode:
        if SOCKET.exists():
            raise ValueError('The dedicated SSH socket exists but is not live; inspect it rather than replacing it.')
        run(*SSH, '-fNT', '-M', '-S', str(SOCKET), '-o', 'ControlPersist=no',
            '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
            '-o', 'StreamLocalBindUnlink=yes', '-R', remote_socket + ':127.0.0.1:8890', 'haven')
    entry = {'id': 'macbook-owner', 'label': 'MacBook worker', 'node_id': (STATE / 'node-id').read_text().strip(),
             'base': 'http://127.0.0.1:8890/v1', 'socket_path': remote_socket, 'key': (STATE / 'api-key').read_text().strip(),
             'model': 'haven-mac-smollm2', 'display_model': 'SmolLM2 1.7B Instruct · Q4_K_M',
             'kind': 'llama', 'compute': 'metal', 'model_sha256': DIGEST, 'max_context_tokens': 2048,
             'trust': 'OWNER_ENROLLED_SSH', 'allowed_roles': ['admin'], 'enrolled_at': time.time(),
             'capabilities': {'source': 'HOST_OBSERVED', 'architecture': __import__('platform').machine(),
                              'ram_total_gib': int(run('/usr/sbin/sysctl', '-n', 'hw.memsize').stdout) / 1024**3,
                              'accelerator': 'Apple Metal', 'runtime': 'llama.cpp 0.7.0 / 620d2225c'}}
    # Secret travels over host-verified SSH stdin, never argv or a printed link.
    remote = "import sys,json,os,pathlib,tempfile; os.umask(0o077); d=json.load(sys.stdin); p=pathlib.Path.home()/'.local/state/haven-model-lab/providers'; p.mkdir(parents=True,exist_ok=True,mode=0o700); fd,n=tempfile.mkstemp(prefix='.enroll-',dir=p); f=os.fdopen(fd,'w'); json.dump(d,f); f.close(); os.replace(n,p/'macbook-owner.json')"
    import shlex
    run(*SSH, 'haven', 'python3 -c ' + shlex.quote(remote), input=json.dumps(entry))
    print('Private Mac worker enrollment saved on Slink; reload/probe the registry from Haven. No inference started.')


def disable():
    run('launchctl', 'disable', 'gui/' + str(os.getuid()) + '/' + LABEL)
    run('launchctl', 'bootout', 'gui/' + str(os.getuid()) + '/' + LABEL, check=False)
    deadline = time.monotonic() + 5
    while run('launchctl', 'print', 'gui/' + str(os.getuid()) + '/' + LABEL, check=False).returncode == 0:
        if time.monotonic() > deadline:
            raise ValueError('Owned worker unload is not confirmed. No duplicate was started.')
        time.sleep(.1)
    if run(*SSH, '-S', str(SOCKET), '-O', 'check', 'haven', check=False).returncode == 0:
        run(*SSH, '-S', str(SOCKET), '-O', 'exit', 'haven')
    print('Owned worker LaunchAgent unloaded and owned reverse tunnel closed. Artifacts and enrollment preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('enable', 'serve', 'enroll', 'disable'))
    args = parser.parse_args()
    if sys.platform != 'darwin' or os.getuid() == 0:
        parser.error('Use the ordinary owner account on the prepared Apple Silicon Mac.')
    os.umask(0o077)
    {'enable': enable, 'serve': serve, 'enroll': enroll, 'disable': disable}[args.action]()


if __name__ == '__main__':
    main()
