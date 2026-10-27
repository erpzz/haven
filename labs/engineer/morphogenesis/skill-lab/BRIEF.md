# Skill brief: run_tests

## Observed limitation (from Haven executor ledgers, not opinion)

In every local-model engineering run so far (Qwen3.5-4B, 3 of 3 runs), the agent spent its first
three commands discovering how to run the test suite: `python -m pytest` (exit 127: no `python`
on PATH), `python3 -m pytest` (pytest is not installed), then `python3 -m unittest`. That is ~30%
of the tool calls on a small task, plus a model turn each (5–50 s on this Mac). Failures then
arrive as raw tracebacks that a 4B model must parse.

## Hypothesis

An executable `run_tests` skill — detect the test framework, run it correctly in this environment,
and return structured failures — removes those steps and helps agents that never saw it being
written. The same procedure given only as prose (`recipe.md`) is the control: if prose works as
well as code, the executable form adds nothing.

## Contract

`skill.py` is run as `python3 skill.py '<json>'` with the repository root as the working directory.
The JSON argument may contain `"path"` (subdirectory to test, default ".") and `"filter"` (substring
of test ids to run, default all). The last line of stdout must be one JSON object:

```json
{"framework": "unittest | pytest-style | node-test | other",
 "command": "the exact command(s) a person could rerun",
 "exit_code": 0, "passed": 3, "failed": 1,
 "failing": [{"id": "CalcTest.test_add", "file": "test_calc.py", "line": 7, "message": "AssertionError: -1 != 5"}],
 "summary": "one short line"}
```

Test ids: unittest → `Class.test_method`; pytest-style functions → `<module stem>.test_name`,
pytest-style classes → `Class.test_method`; node:test → the test's name string.
Errors (exceptions) count as failing, with the exception as the message.

## Environment facts

- `python3` is CPython 3.9 with the standard library only. **pytest is not installed and cannot be
  installed** (sandbox: no network, no writes outside the repo and `$TMPDIR`). Tests written for
  pytest may still `import pytest` (e.g. `pytest.raises`) and may rely on `pyproject.toml`
  `[tool.pytest.ini_options] pythonpath = ['src']`.
- Python repos may use a `src/` layout and tests in `tests/` (with or without `__init__.py`).
- `node` v26 is available with the built-in `node:test` runner (`node --test`), which supports
  `--test-reporter=tap` and `--test-reporter=spec`.
- Do not modify the repository's tracked files; temporary files go in `$TMPDIR`.

## Admission

Haven admits the skill only if it passes **held-out cases you cannot see**: the same frameworks in
different layouts (src packages, nested test directories, errors versus failures, suites that all
pass, test classes). Hardcoding the dev cases will fail admission. `python3 validate_dev.py` checks
your candidate against the dev cases in `dev_cases/` with the same comparison the harness uses.

## Deliverables (in `candidate/`)

- `skill.json`: `{"name": "run_tests", "description": "...", "parameters": {JSON schema}}`
- `skill.py`: standard library only, Python 3.9 compatible, no network.
- `recipe.md`: the same procedure as step-by-step instructions a person or model could follow by
  hand with ordinary shell commands. Keep it equivalent to the code: it is the control arm.

Commit when `python3 validate_dev.py` passes.
