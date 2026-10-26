#!/usr/bin/env python3
"""Owner-enabled cloud lane: official Claude Code / Codex CLIs behind a loopback OpenAI contract.

Each request runs one finite CLI turn as the owner, on the owner's own plan, with
every tool, MCP server, plugin, skill and user setting disabled, in an empty
private directory. No API key, credential file, browser session or undocumented
endpoint is read. The process fails closed on any tool, API-key auth or paid
overage it observes. Haven reaches it only through a dedicated reverse SSH tunnel
that terminates in a private Unix socket per lane on Slink, never a TCP port.
"""
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import plistlib
import secrets
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid

STATE = Path.home() / '.local/state/haven-cloud-worker'
PORT = 8891
LABEL = 'com.haven.cloud-worker'
PLIST = Path.home() / 'Library/LaunchAgents/com.haven.cloud-worker.plist'
SOCKET = Path.home() / '.ssh/haven-cloud.sock'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8']
TIMEOUT = 200            # Below the Lab's 240 s watchdog, so the Lab sees our error, not its own.
MAX_MESSAGES, MAX_CHARS = 40, 120000
SYSTEM = ("You are Haven's cloud lane: a careful general assistant answering one turn of a private "
          "conversation that the owner relayed from their home server. In this lane you have no tools, "
          "files, memory or internet access. Answer directly, and say plainly when you are unsure.")
LANES = {
    'haven-claude-code': {'cli': 'claude', 'route_class': 'CLAUDE_CODE_PLAN', 'vendor': 'Anthropic',
                          'label': 'Cloud · Claude Code', 'model': 'sonnet'},
    'haven-codex-cli': {'cli': 'codex', 'route_class': 'CHATGPT_PLAN', 'vendor': 'OpenAI',
                        'label': 'Cloud · Codex', 'model': ''},
}
# Never inherited: any of these could switch a CLI to metered API billing or another account.
SCRUB = ('ANTHROPIC_', 'OPENAI_', 'CLAUDE_CODE_USE_', 'AWS_', 'GOOGLE_', 'VERTEX', 'AZURE_', 'CODEX_API', 'DYLD_')


class LaneError(Exception):
    def __init__(self, status, message):
        super().__init__(message); self.status = status


def private_file(path, value):
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f: f.write(value + '\n')
    meta = path.lstat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_mode & 0o077:
        raise ValueError(f'{path.name} must be a private owned regular file.')
    return path.read_text().strip()


def prepare():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    meta = STATE.lstat()
    if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_mode & 0o077:
        raise ValueError('The cloud lane state directory must be private and owned.')
    private_file(STATE / 'api-key', secrets.token_urlsafe(48))
    private_file(STATE / 'node-id', str(uuid.uuid4()))
    path = STATE / 'config.json'
    if not path.exists():
        raise ValueError('Run `cloud-worker.py configure` first; nothing was started.')
    return json.loads(path.read_text())


def configure(args):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    lanes = {}
    for ident, lane in LANES.items():
        if ident.split('-')[1] not in args.lanes: continue
        exe = shutil.which(lane['cli'])
        if not exe:
            print(f'{lane["cli"]} is not installed; {ident} stays disabled.'); continue
        # The package manager's stable link, so an upgrade does not leave a dangling versioned path.
        lanes[ident] = {'exe': os.path.abspath(exe), 'model': lane['model']}
    if 'haven-codex-cli' in lanes:
        # --ignore-user-config also drops the account's model; record only that one key from it.
        lanes['haven-codex-cli']['model'] = args.codex_model or codex_model()
        if not lanes['haven-codex-cli']['model']:
            raise ValueError('Name the Codex model with --codex-model; the built-in default may not exist for this plan.')
    if 'haven-claude-code' in lanes:
        if not args.claude_config_dir or not Path(args.claude_config_dir).is_dir():
            raise ValueError('Name the signed-in Claude profile with --claude-config-dir; the default profile is never assumed.')
        lanes['haven-claude-code']['config_dir'] = str(Path(args.claude_config_dir).resolve())
    config = {'lanes': lanes, 'daily_cap': args.daily_cap}
    fd, tmp = tempfile.mkstemp(dir=STATE); os.write(fd, (json.dumps(config, indent=1) + '\n').encode()); os.close(fd)
    os.replace(tmp, STATE / 'config.json')
    print('Cloud lanes configured:', ', '.join(lanes) or 'none', f'(daily cap {args.daily_cap} requests).')


def codex_model():
    import re
    path = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'config.toml'
    try: text = path.read_text()
    except OSError: return ''
    top = text.split('\n[', 1)[0]  # Top-level table only; profiles are not inferred.
    match = re.search(r'^\s*model\s*=\s*"([A-Za-z0-9._:-]{1,80})"\s*$', top, re.M)
    return match[1] if match else ''


def child_env(lane, cwd):
    env = {k: v for k, v in os.environ.items() if k in ('HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL')}
    env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:' + str(Path.home() / '.local/bin'),
               TMPDIR=str(cwd), DISABLE_AUTOUPDATER='1', NO_COLOR='1')
    if lane.get('config_dir'): env['CLAUDE_CONFIG_DIR'] = lane['config_dir']
    if os.environ.get('CODEX_HOME'): env['CODEX_HOME'] = os.environ['CODEX_HOME']
    assert not any(k.startswith(SCRUB) for k in env)
    return env


def render(messages):
    """System text and one prompt. Prior turns are quoted as data, never re-issued as instructions."""
    system = '\n\n'.join(m['content'] for m in messages if m['role'] == 'system') or SYSTEM
    turns = [m for m in messages if m['role'] != 'system']
    if len(turns) == 1:
        return system, turns[0]['content']
    body = '\n\n'.join(('User: ' if m['role'] == 'user' else 'Assistant: ') + m['content'] for m in turns)
    return system, 'Conversation so far:\n\n' + body + '\n\nReply to the last User message.'


def claude_argv(lane, cwd, system_file):
    argv = [lane['exe'], '-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages',
            '--tools', '', '--restricted', '--strict-mcp-config', '--disable-slash-commands',
            '--no-session-persistence', '--no-chrome', '--system-prompt-file', str(system_file)]
    return argv + (['--model', lane['model']] if lane.get('model') else [])


def codex_argv(lane, cwd, system_file):
    argv = [lane['exe'], 'exec', '--json', '--ephemeral', '--skip-git-repo-check', '--ignore-user-config',
            '--ignore-rules', '-s', 'read-only', '-C', str(cwd), '-c', 'web_search="disabled"']
    for feature in ('shell_tool', 'unified_exec', 'apps', 'plugins', 'memories', 'hooks', 'browser_use',
                    'browser_use_external', 'computer_use', 'in_app_browser', 'image_generation'):
        argv += ['--disable', feature]
    return argv + (['-m', lane['model']] if lane.get('model') else []) + ['-']


class ClaudeParser:
    """Claude Code stream-json. Verifies the no-tool, subscription-only contract as it arrives."""
    def __init__(self): self.usage, self.done, self.text = {}, False, ''
    def feed(self, o):
        kind = o.get('type')
        if kind == 'system' and o.get('subtype') == 'init':
            if o.get('tools') or o.get('mcp_servers'):
                raise LaneError(502, 'Claude Code reported tools or MCP servers; the turn was stopped.')
            if o.get('apiKeySource') not in (None, 'none'):
                raise LaneError(402, 'Claude Code would use an API key, not the plan; the turn was stopped.')
        elif kind == 'rate_limit_event':
            info = o.get('rate_limit_info') or {}
            if info.get('isUsingOverage') or info.get('status') not in (None, 'allowed', 'allowed_warning'):
                raise LaneError(429, 'Claude plan limit reached (no paid overage is used); try later or stay local.')
        elif kind == 'stream_event':
            e = o.get('event') or {}
            if e.get('type') == 'content_block_start' and (e.get('content_block') or {}).get('type') not in ('text', 'thinking', 'redacted_thinking'):
                raise LaneError(502, 'Claude Code attempted a tool call; the turn was stopped.')
            if e.get('type') == 'content_block_delta' and (e.get('delta') or {}).get('type') == 'text_delta':
                return e['delta'].get('text') or ''
        elif kind == 'result':
            if o.get('is_error') or o.get('subtype') != 'success':
                raise LaneError(429 if 'limit' in str(o.get('result', '')).lower() else 502, 'Claude Code reported an error; nothing was retried.')
            u = o.get('usage') or {}
            self.usage = {'prompt_tokens': sum(u.get(k) or 0 for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')),
                          'completion_tokens': u.get('output_tokens')}
            self.done = True
        return ''


class CodexParser:
    """Codex exec --json. Only agent messages, reasoning and CLI notices are acceptable items."""
    def __init__(self): self.usage, self.done, self.text = {}, False, ''
    def feed(self, o):
        kind = o.get('type', '')
        item = o.get('item') or {}
        # An `error` item is a CLI notice (e.g. fallback model metadata), not a tool call.
        if kind.startswith('item.') and item.get('type') not in (None, 'agent_message', 'reasoning', 'error'):
            raise LaneError(502, 'Codex attempted a tool or command; the turn was stopped.')
        if kind in ('error', 'turn.failed'):
            text = json.dumps(o).lower()
            if 'newer version of codex' in text:
                raise LaneError(502, 'The installed Codex CLI is too old for this model; upgrade it (brew upgrade codex).')
            if 'model_not_found' in text or 'not supported' in text:
                raise LaneError(502, 'Codex rejected the configured model; rerun configure with --codex-model.')
            raise LaneError(429 if ('limit' in text or 'quota' in text or 'usage' in text) else 502,
                            'Codex reported an error or plan limit; nothing was retried.')
        if kind == 'item.completed' and item.get('type') == 'agent_message':
            return item.get('text') or ''
        if kind == 'turn.completed':
            u = o.get('usage') or {}
            self.usage = {'prompt_tokens': u.get('input_tokens'), 'completion_tokens': u.get('output_tokens')}
            self.done = True
        return ''


class Usage:
    def __init__(self, cap):
        self.cap, self.lock, self.path = cap, threading.Lock(), STATE / 'usage.json'
    def take(self):
        day = time.strftime('%Y-%m-%d', time.gmtime())
        with self.lock:
            try: seen = json.loads(self.path.read_text())
            except (OSError, ValueError): seen = {}
            count = seen.get(day, 0)
            if count >= self.cap:
                raise LaneError(429, f'Daily cloud cap of {self.cap} requests reached; nothing was sent.')
            seen = {day: count + 1}
            fd, tmp = tempfile.mkstemp(dir=STATE); os.write(fd, json.dumps(seen).encode()); os.close(fd)
            os.replace(tmp, self.path)


def receipt(row):
    with (STATE / 'requests.jsonl').open('a') as f: f.write(json.dumps(row) + '\n')


def stop(proc):
    if proc.poll() is None:
        try: os.killpg(proc.pid, signal.SIGKILL)
        except OSError: pass  # Already exited; macOS reports EPERM for a reaped group.


def watch_client(conn, proc, closed):
    # The request body is fully read, so a readable socket means the Lab hung up (Stop or watchdog).
    while proc.poll() is None:
        try:
            ready, _, _ = select.select([conn], [], [], .5)
            if ready and conn.recv(1, socket.MSG_PEEK) == b'':
                closed.set(); return stop(proc)
        except (OSError, ValueError):
            closed.set(); return stop(proc)


def make_handler(config, key, usage, busy):
    lanes = {i: {**LANES[i], **v} for i, v in config['lanes'].items() if i in LANES}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def log_message(self, *args): pass  # Prompts and answers stay out of logs.

        def authorized(self):
            given = self.headers.get('Authorization', '')
            return hmac.compare_digest(given.encode(), ('Bearer ' + key).encode())

        def reply(self, status, obj):
            data = json.dumps(obj).encode()
            self.send_response(status); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data))); self.send_header('Connection', 'close')
            self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            if not self.authorized(): return self.reply(401, {'error': {'message': 'unauthorized'}})
            if self.path != '/v1/models': return self.reply(404, {'error': {'message': 'not found'}})
            self.reply(200, {'object': 'list', 'data': [{'id': i, 'object': 'model', 'owned_by': l['vendor'],
                             'route_class': l['route_class']} for i, l in lanes.items() if os.access(l['exe'], os.X_OK)]})

        def do_POST(self):
            if not self.authorized(): return self.reply(401, {'error': {'message': 'unauthorized'}})
            if self.path != '/v1/chat/completions': return self.reply(404, {'error': {'message': 'not found'}})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 1024 * 1024: raise LaneError(413, 'Request too large.')
                req = json.loads(self.rfile.read(size))
                lane = lanes.get(req.get('model'))
                if not lane: raise LaneError(404, 'Unknown or disabled cloud lane.')
                if req.get('stream') is not True: raise LaneError(400, 'Only streaming requests are supported.')
                messages = req.get('messages')
                if (not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES or
                        any(not isinstance(m, dict) or m.get('role') not in ('system', 'user', 'assistant') or
                            not isinstance(m.get('content'), str) for m in messages) or
                        sum(len(m['content']) for m in messages) > MAX_CHARS or messages[-1]['role'] != 'user'):
                    raise LaneError(400, f'Send 1-{MAX_MESSAGES} text messages ending with a user turn.')
            except LaneError as e:
                return self.reply(e.status, {'error': {'message': str(e)}})
            except (ValueError, TypeError):
                return self.reply(400, {'error': {'message': 'Invalid JSON request.'}})
            if not busy.acquire(False):
                return self.reply(429, {'error': {'message': 'The cloud lane runs one turn at a time.'}})
            try:
                self.run_turn(req['model'], lane, messages)
            finally:
                busy.release()

        def run_turn(self, ident, lane, messages):
            began = time.monotonic(); sent_headers = False; proc = None; outcome = 'FAILED'; closed = threading.Event()
            parser = ClaudeParser() if lane['cli'] == 'claude' else CodexParser()
            row = {'at': time.time(), 'lane': ident, 'route_class': lane['route_class'],
                   'prompt_sha256': hashlib.sha256(json.dumps(messages).encode()).hexdigest()}
            cid = 'chatcmpl-' + secrets.token_hex(8)
            def chunk(delta, finish=None, extra=None):
                obj = {'id': cid, 'object': 'chat.completion.chunk', 'model': ident,
                       'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                if extra: obj.update(extra)
                self.wfile.write(b'data: ' + json.dumps(obj).encode() + b'\n\n'); self.wfile.flush()
            def start_stream():
                nonlocal sent_headers
                if not sent_headers:
                    self.send_response(200); self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-store'); self.send_header('Connection', 'close')
                    self.end_headers(); sent_headers = True
            with tempfile.TemporaryDirectory(prefix='turn-', dir=STATE) as cwd:
                try:
                    usage.take()
                    system, prompt = render(messages)
                    system_file = Path(cwd) / '.system'; system_file.write_text(system)
                    if lane['cli'] == 'codex':
                        prompt = system + '\n\n' + prompt
                    argv = (claude_argv if lane['cli'] == 'claude' else codex_argv)(lane, Path(cwd), system_file)
                    proc = subprocess.Popen(argv, cwd=cwd, env=child_env(lane, Path(cwd)), stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
                    timer = threading.Timer(TIMEOUT, lambda: stop(proc))
                    timer.daemon = True; timer.start()
                    threading.Thread(target=watch_client, args=(self.connection, proc, closed), daemon=True).start()
                    try:
                        proc.stdin.write(prompt.encode()); proc.stdin.close()
                        for raw in proc.stdout:
                            try: obj = json.loads(raw)
                            except ValueError: continue
                            text = parser.feed(obj)
                            if text:
                                start_stream(); chunk({'role': 'assistant', 'content': text})
                        proc.wait(5)
                    finally:
                        timer.cancel()
                    if closed.is_set():
                        raise BrokenPipeError
                    if not parser.done:
                        raise LaneError(504 if time.monotonic() - began >= TIMEOUT else 502,
                                        'The cloud CLI ended without a completed turn; nothing was retried.')
                    start_stream()
                    chunk({}, 'stop')
                    chunk({}, None, {'choices': [], 'usage': parser.usage})
                    self.wfile.write(b'data: [DONE]\n\n'); self.wfile.flush()
                    outcome = 'COMPLETED'; row['usage'] = parser.usage
                except LaneError as e:
                    outcome = f'REFUSED_{e.status}'; row['reason'] = str(e)
                    if sent_headers:
                        self.wfile.write(b'data: ' + json.dumps({'error': {'message': str(e)}}).encode() + b'\n\n')
                    else:
                        self.reply(e.status, {'error': {'message': str(e)}})
                except (BrokenPipeError, ConnectionResetError):
                    outcome = 'CLIENT_CLOSED'
                finally:
                    if proc:
                        stop(proc); proc.wait()
                    row.update(outcome=outcome, seconds=round(time.monotonic() - began, 3))
                    receipt(row)
    return Handler


def serve():
    config = prepare()
    key = (STATE / 'api-key').read_text().strip()
    server = ThreadingHTTPServer(('127.0.0.1', PORT), make_handler(config, key, Usage(config['daily_cap']), threading.Lock()))
    print(f'Cloud lane on 127.0.0.1:{PORT}: {", ".join(config["lanes"]) or "no lanes"}.', flush=True)
    server.serve_forever()


def launchctl(*argv, check=True):
    return subprocess.run(['launchctl', *argv], check=check, capture_output=True, text=True)


def enable():
    prepare()
    # LaunchAgents cannot read Documents; run a private copy, never request Full Disk Access.
    library = Path.home() / '.local/lib/haven-cloud-worker'
    library.mkdir(parents=True, exist_ok=True, mode=0o700)
    helper = library / 'cloud-worker.py'
    if helper.resolve() != Path(__file__).resolve():
        helper.write_bytes(Path(__file__).read_bytes()); helper.chmod(0o700)
    target = f'gui/{os.getuid()}/{LABEL}'
    content = plistlib.dumps({'Label': LABEL, 'ProgramArguments': [sys.executable, str(helper), 'serve'],
                              'RunAtLoad': True, 'KeepAlive': {'SuccessfulExit': False}, 'ProcessType': 'Background',
                              'StandardOutPath': str(STATE / 'worker.log'), 'StandardErrorPath': str(STATE / 'worker.log')})
    if PLIST.exists() and PLIST.read_bytes() != content:
        launchctl('bootout', target, check=False); PLIST.unlink()
    launchctl('enable', target)
    if launchctl('print', target, check=False).returncode == 0:
        launchctl('kickstart', '-k', target); print('Cloud lane LaunchAgent restarted with the current helper.'); return
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', PORT)) == 0:
            raise ValueError(f'Mac loopback port {PORT} is occupied; nothing was stopped.')
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(content); PLIST.chmod(0o600)
    launchctl('bootstrap', f'gui/{os.getuid()}', str(PLIST))
    print('Cloud lane LaunchAgent registered on loopback only.')


# Runs on Slink. Finds the Lab code that will read the enrollment and refuses if it predates cloud lanes:
# an older registry rejects unknown kinds, and a Lab that cannot load its registry cannot start.
REMOTE_PREFLIGHT = '''
import os, pathlib, re, subprocess, sys
os.umask(0o077)
data, lab = sys.argv[1], sys.argv[2]
if not lab:
    unit = subprocess.run(['systemctl', '--user', 'show', 'haven-model-lab', '-p', 'ExecStart'], capture_output=True, text=True).stdout
    found = re.search(r'(\\S+)/server\\.py', unit)
    lab = found[1] if found else ''
code = pathlib.Path(lab) / 'providers.py'
if not code.is_file() or 'HOSTED_SUBSCRIPTION' not in code.read_text():
    sys.exit('REFUSED: the Lab at %s predates cloud lanes; deploy this branch first.' % (lab or 'unknown'))
p = pathlib.Path(data).expanduser() / 'providers'
p.mkdir(parents=True, exist_ok=True, mode=0o700)
print(p)
'''


def enroll(args):
    config = prepare()
    import shlex
    run = lambda *a, **k: subprocess.run(a, check=True, capture_output=True, text=True, **k)
    idents = [ident.replace('haven-', 'cloud-') for ident in config['lanes']]
    check = subprocess.run([*SSH, 'haven', 'python3 -c ' + shlex.quote(REMOTE_PREFLIGHT) + ' ' +
                            shlex.quote(args.data_dir) + ' ' + shlex.quote(args.lab_dir)], capture_output=True, text=True)
    providers = check.stdout.strip()
    if check.returncode or not providers.startswith('/') or '\n' in providers:
        raise ValueError((check.stderr.strip() or 'Invalid private remote enrollment directory.') + ' Nothing was enrolled.')
    # Replace only our own tunnel so its forwards always match the configured lanes.
    if subprocess.run([*SSH, '-S', str(SOCKET), '-O', 'check', 'haven'], capture_output=True).returncode == 0:
        run(*SSH, '-S', str(SOCKET), '-O', 'exit', 'haven')
    elif SOCKET.exists():
        raise ValueError('The dedicated SSH socket exists but is not live; inspect it rather than replacing it.')
    forwards = [arg for ident in idents for arg in ('-R', f'{providers}/{ident}.sock:127.0.0.1:{PORT}')]
    if forwards:
        run(*SSH, '-fNT', '-M', '-S', str(SOCKET), '-o', 'ControlPersist=no', '-o', 'ExitOnForwardFailure=yes',
            '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3', '-o', 'StreamLocalBindUnlink=yes',
            *forwards, 'haven')
    node, key = (STATE / 'node-id').read_text().strip(), (STATE / 'api-key').read_text().strip()
    entries = [{'id': ident.replace('haven-', 'cloud-'), 'label': LANES[ident]['label'], 'node_id': node,
                'base': f'http://127.0.0.1:{PORT}/v1', 'socket_path': f"{providers}/{ident.replace('haven-', 'cloud-')}.sock",
                'key': key, 'model': ident,
                'display_model': LANES[ident]['label'].split(' · ')[1] + ' (' + LANES[ident]['vendor'] + ')',
                'kind': 'cloud', 'compute': 'hosted', 'route_class': LANES[ident]['route_class'],
                'vendor': LANES[ident]['vendor'], 'egress': 'HOSTED_SUBSCRIPTION', 'max_context_tokens': 32768,
                'trust': 'OWNER_ENROLLED_SSH', 'allowed_roles': ['admin'], 'enrolled_at': time.time(),
                'capabilities': {'source': 'OWNER_DECLARED', 'tools': 'DISABLED', 'daily_cap': config['daily_cap']}}
               for ident in config['lanes']]
    # Secrets travel over host-verified SSH stdin, never argv or a printed link. Only our own files are replaced.
    remote = ("import sys,json,os,pathlib,tempfile; os.umask(0o077); rows=json.load(sys.stdin); "
              "p=pathlib.Path(sys.argv[1])\n"
              "for name in ('cloud-claude-code','cloud-codex-cli'):\n"
              "    f=p/(name+'.json')\n"
              "    if f.exists() and name not in [r['id'] for r in rows]: f.unlink()\n"
              "for d in rows:\n"
              "    fd,n=tempfile.mkstemp(prefix='.enroll-',dir=p); f=os.fdopen(fd,'w'); json.dump(d,f); f.close(); os.replace(n,p/(d['id']+'.json'))")
    run(*SSH, 'haven', 'python3 -c ' + shlex.quote(remote) + ' ' + shlex.quote(providers), input=json.dumps(entries))
    print('Enrolled on Slink:', ', '.join(e['id'] for e in entries) or 'no lanes',
          '- refresh workers in Haven. Nothing was sent to a cloud model.')


def disable():
    target = f'gui/{os.getuid()}/{LABEL}'
    launchctl('disable', target); launchctl('bootout', target, check=False)
    if subprocess.run([*SSH, '-S', str(SOCKET), '-O', 'check', 'haven'], capture_output=True).returncode == 0:
        subprocess.run([*SSH, '-S', str(SOCKET), '-O', 'exit', 'haven'], capture_output=True)
    print('Cloud lane stopped and its reverse tunnel closed. Haven shows it offline; nothing else changed.')


def status():
    config = prepare()
    try: today = json.loads((STATE / 'usage.json').read_text())
    except (OSError, ValueError): today = {}
    tunnel = subprocess.run([*SSH, '-S', str(SOCKET), '-O', 'check', 'haven'], capture_output=True).returncode == 0
    print(json.dumps({'lanes': list(config['lanes']), 'daily_cap': config['daily_cap'], 'usage': today,
                      'service': launchctl('print', f'gui/{os.getuid()}/{LABEL}', check=False).returncode == 0,
                      'tunnel': tunnel}, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    c = sub.add_parser('configure', help='record which official CLIs and Claude profile to use')
    c.add_argument('--lanes', nargs='+', choices=('claude', 'codex'), default=['claude', 'codex'])
    c.add_argument('--claude-config-dir', default=os.environ.get('CLAUDE_CONFIG_DIR', ''))
    c.add_argument('--codex-model', default='', help='default: the top-level model in ~/.codex/config.toml')
    c.add_argument('--daily-cap', type=int, default=50, choices=range(1, 501), metavar='1-500')
    e = sub.add_parser('enroll', help='tunnel and enroll the lanes in a Haven Lab on Slink')
    e.add_argument('--data-dir', default='~/.local/share/haven-model-lab', help='that Lab\'s --data-dir on Slink')
    e.add_argument('--lab-dir', default='', help='that Lab\'s labs/model-lab on Slink; default: the haven-model-lab unit')
    for name in ('serve', 'enable', 'disable', 'status'): sub.add_parser(name)
    args = parser.parse_args()
    if os.getuid() == 0: parser.error('Run as the ordinary owner account.')
    os.umask(0o077)
    if args.action == 'configure': return configure(args)
    if args.action == 'enroll': return enroll(args)
    {'serve': serve, 'enable': enable, 'disable': disable, 'status': status}[args.action]()


if __name__ == '__main__':
    main()
