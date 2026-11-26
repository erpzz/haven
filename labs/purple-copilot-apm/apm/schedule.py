"""Periodic sample-graph snapshots, independent of inference and CE ingestion."""
import argparse
import signal
from threading import Event

from .collect import collect
from .path_history import scan
from .tier_zero import scan as tier_zero_scan


def schedule(interval, stop):
    while not stop.is_set():
        collect()
        scan()
        tier_zero_scan()
        stop.wait(interval)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seconds", type=int, default=3600)
    args = p.parse_args()
    if args.seconds < 60:
        p.error("Minimum interval is 60 seconds")
    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    schedule(args.seconds, stop)
