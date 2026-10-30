#!/usr/bin/env python3
"""Check that each task's judge fails on the fixture and passes once its reference fix (fix.json) is applied.

  validate_tasks.py e5a-invoice-pytest-src e5b-lru-node ...
"""
import json
import pathlib
import shutil
import sys
import tempfile

from run_bench import TASKS, verify


def check(task):
    spec = json.loads((TASKS / task / "task.json").read_text())
    fixes = json.loads((TASKS / task / "fix.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp) / task
        shutil.copytree(TASKS / task / "repo", repo)
        broken, _ = verify(repo, spec)
        for f in fixes:
            p = repo / f["path"]
            text = p.read_text()
            if text.count(f["old"]) != 1:
                return f"{task}: fix text not found once in {f['path']}"
            p.write_text(text.replace(f["old"], f["new"]))
        fixed, tail = verify(repo, spec)
    if broken or not fixed:
        return f"{task}: broken passes={broken} fixed passes={fixed}\n{tail}"
    return None


if __name__ == "__main__":
    problems = [p for p in map(check, sys.argv[1:]) if p]
    print("\n".join(problems) or f"{len(sys.argv) - 1} tasks: fixture fails, reference fix passes")
    sys.exit(1 if problems else 0)
