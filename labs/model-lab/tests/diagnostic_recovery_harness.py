"""Browser regression harness for #71 (Investigate host must never leave Send disabled).

Serves the real Lab UI on loopback with a TEST DOUBLE backend and a diagnostic that
never finishes. `--stall` additionally makes every diagnostic status request hang,
reproducing a stalled SSH tunnel. Open the printed URL, click Investigate host and
check that Send is enabled again within the bounded watch (about 95 s when stalled).
Nothing here touches a model, GPU or the live Lab.
"""
import argparse
from pathlib import Path
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from labcore import Lab
from server import Server
from fake_backend import FakeBackend


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8899)
    ap.add_argument('--stall', action='store_true', help='Hang diagnostic status requests.')
    ap.add_argument('--context', type=int, default=32768)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='haven-diag-ui-') as tmp:
        lab = Lab(Path(tmp))
        backend = FakeBackend()
        lab.connection = {'base': backend.base, 'key': '', 'model': 'haven-local', 'kind': 'llama',
                          'ownership': 'OWNED', 'display_model': 'TEST_DOUBLE diagnostic harness',
                          'profile': {'context': args.context}, 'compute': 'gpu', 'connected_at': time.time()}
        lab.engine.record = {'state': 'READY', 'ownership': 'OWNED'}

        def diagnose(request):
            job = lab.new_job('diagnostic')
            job.update(message='TEST DOUBLE diagnostic that never finishes.', trace=[])
            return job.id

        def snapshot(jid):
            if args.stall:
                time.sleep(3600)
            job = lab.jobs.get(jid)
            return job.snapshot() if job else None

        lab.diagnose = diagnose
        lab.diagnostic_snapshot = snapshot
        server = Server(('127.0.0.1', args.port), lab)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        # The UI only shows Investigate host on Linux.
        hw = lab.get_hardware
        lab.get_hardware = lambda: {**hw(), 'platform': 'linux'}
        print(f'http://127.0.0.1:{server.server_port}/#token={lab.token}', flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown(); backend.close()


if __name__ == '__main__':
    main()
