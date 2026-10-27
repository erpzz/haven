"""Run candidate/skill.py on dev_cases/ with the same judgement Haven's admission harness uses."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent


def norm(s):
    parts = [p for p in s.replace("::", ".").replace("/", ".").replace(" ", "").split(".") if p and p != "py"]
    return ".".join(parts[-2:]).lower()


def check(result, expect):
    if not isinstance(result, dict):
        return "no JSON result"
    problems = []
    if result.get("framework") != expect["framework"]:
        problems.append("framework %r != %r" % (result.get("framework"), expect["framework"]))
    got = sorted(norm(f.get("id", "")) for f in result.get("failing") or [])
    want = sorted(norm(x) for x in expect["failing"])
    if got != want:
        problems.append("failing %s != %s" % (got, want))
    if result.get("passed") != expect["passed"]:
        problems.append("passed %r != %r" % (result.get("passed"), expect["passed"]))
    if expect["failing"] and not all(f.get("message") for f in result.get("failing") or []):
        problems.append("a failure has no message")
    return "; ".join(problems)


ok = True
for case in sorted((HERE / "dev_cases").iterdir()):
    expect = json.loads((case / "expect.json").read_text())
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as t:
        repo = pathlib.Path(t) / "repo"
        shutil.copytree(case / "repo", repo)
        r = subprocess.run([sys.executable, str(HERE / "candidate" / "skill.py"), "{}"], cwd=repo,
                           capture_output=True, text=True, timeout=120)
        try:
            result = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            result = None
        why = check(result, expect)
        ok = ok and not why
        print(("PASS " if not why else "FAIL ") + case.name + ("" if not why else ": " + why + "\n  stderr: " + r.stderr[-300:]))
sys.exit(0 if ok else 1)
