"""Private launcher helper. Not a shell and not an HTTP endpoint."""
import json
import os
import subprocess
import sys

def main():
    # Parent writes one JSON frame only after OS process containment is established.
    frame = sys.stdin.readline(65536)
    if not frame:
        return 2
    msg = json.loads(frame)
    if msg.get('go') is not True or not isinstance(msg.get('argv'), list):
        return 2
    if os.name == 'nt':
        proc = subprocess.Popen(msg['argv'], stdin=subprocess.DEVNULL, close_fds=True)
        return proc.wait()
    os.execv(msg['argv'][0], msg['argv'])

if __name__ == '__main__':
    raise SystemExit(main())
