import argparse
import json
import sqlite3

from ..local import now
from .formats import parse
from .vault import SECTIONS, bounded, correlate, ingest, report


def main():
    parser = argparse.ArgumentParser(
        description="Import offline evidence or review a historical correlation"
    )
    commands = parser.add_subparsers(dest="cmd", required=True)
    importer = commands.add_parser("import")
    importer.add_argument("manifest")
    importer.add_argument("artifact")
    for cmd in ("link", "show"):
        p = commands.add_parser(cmd)
        p.add_argument("run", type=int)
        p.add_argument("fingerprint")
        if cmd == "link":
            p.add_argument("artifact_id")
        else:
            p.add_argument("--as-of", default=None)
            p.add_argument("--section", choices=SECTIONS)
    a = parser.parse_args()
    try:
        if a.cmd == "import":
            print(*ingest(bounded(a.artifact), parse(bounded(a.manifest))))
        elif a.cmd == "link":
            correlate(a.run, a.fingerprint, a.artifact_id)
        else:
            view = report(a.run, a.fingerprint, a.as_of or now())
            print(json.dumps(view[a.section] if a.section else view, indent=2))
    except (ValueError, KeyError, OSError, sqlite3.Error) as err:
        parser.exit(2, f"Offline evidence error: {err}\n")


if __name__ == "__main__":
    main()
