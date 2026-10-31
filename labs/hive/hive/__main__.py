"""Run ``python -m hive --help`` within labs/hive."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys

import torch

from .model import Spec, baseline
from .wire import load_secret


def main(argv=None):
    p = argparse.ArgumentParser(description='HIVE experimental real neural layer sharding (not trained language inference).')
    commands = p.add_subparsers(dest='command', required=True)
    secret = commands.add_parser('secret', help='Create a private token file, refuse overwrite')
    secret.add_argument('--output', required=True)
    worker = commands.add_parser('worker', help='Serve a contiguous decoder-layer segment on loopback')
    run = commands.add_parser('run', help='Generate byte tokens using real remote segments')
    base = commands.add_parser('baseline', help='Generate tokens with all layers locally for correctness comparison')
    for sub in (worker, run, base):
        sub.add_argument('--layers', type=int, default=4)
        sub.add_argument('--dim', type=int, default=64)
        sub.add_argument('--heads', type=int, default=4)
        sub.add_argument('--context', type=int, default=64)
        sub.add_argument('--seed', type=int, default=20261031)
    for sub in (worker, run):
        sub.add_argument('--secret-file', required=True)
    worker.add_argument('--port', type=int, required=True)
    worker.add_argument('--start', type=int, required=True)
    worker.add_argument('--stop', type=int, required=True)
    worker.add_argument('--device', default='cpu', choices=['cpu', 'cuda'])
    for sub in (run, base):
        sub.add_argument('--prompt', required=True)
        sub.add_argument('--new-tokens', type=int, default=4)
    run.add_argument('--peer', action='append', required=True)
    run.add_argument('--timeout', type=float, default=4.0)
    args = p.parse_args(argv)
    torch.set_num_threads(1)
    if args.command == 'secret':
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_urlsafe(48) + '\n')
        print('Private HIVE secret created; keep it off Git and command lines.')
        return 0
    spec = Spec(layers=args.layers, dim=args.dim, heads=args.heads, context=args.context, seed=args.seed)
    spec.validate()
    if args.command == 'worker':
        from .node import HiveServer
        key = load_secret(args.secret_file)
        server = HiveServer(('127.0.0.1', args.port), spec, args.start, args.stop, key, args.device)
        print(json.dumps({'status': 'LISTENING', 'bind': '127.0.0.1', 'port': server.server_port,
                          'range': [args.start, args.stop], 'model_id': spec.identity}), flush=True)
        try:
            server.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    prompt = args.prompt.encode('utf-8')
    if args.command == 'baseline':
        new = baseline(spec, prompt, args.new_tokens)
        print(json.dumps({'status': 'COMPLETED', 'tokens': new, 'output_hex': bytes(new).hex(),
                          'model_id': spec.identity, 'model_kind': 'random_initialized_transformer_not_a_trained_llm'}))
        return 0
    from .cluster import Cluster
    outcome = Cluster(spec, args.peer, load_secret(args.secret_file), timeout=args.timeout).generate(prompt, args.new_tokens)
    print(json.dumps(outcome, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError) as exc:
        print(f'HIVE FAILED: {type(exc).__name__}: {str(exc)[:160]}', file=sys.stderr)
        sys.exit(1)
