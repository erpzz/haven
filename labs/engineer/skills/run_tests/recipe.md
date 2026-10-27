# run_tests — by hand

Goal: run a repository's tests in this sandbox and report
`{"framework", "command", "exit_code", "passed", "failed", "failing": [{"id", "file", "line", "message"}], "summary"}`.
Work from the repository root. `PATH` (below) is the subdirectory or file to test (default `.`),
`FILTER` an optional substring of test ids.

Environment facts that save the usual wasted commands:

- There is **no `python`**, only `python3` (3.9, standard library only).
- **pytest is not installed and cannot be installed.** Do not try `python3 -m pytest` or `pip`.
- `node` has the built-in runner: `node --test --test-reporter=tap`.
- Do not create files in the repository; use `$TMPDIR`. Set `PYTHONDONTWRITEBYTECODE=1`.

## 1. Detect the framework

```sh
find PATH -name node_modules -prune -o -name '.*' -prune -o \( -name 'test*.py' -o -name '*_test.py' \) -print
grep -rlE "['\"]node:test['\"]" PATH --include='*.js' --include='*.mjs' --include='*.cjs' --include='*.ts' --exclude-dir=node_modules
grep '"test"' package.json     # nearest package.json from PATH up to the root
```

1. If `package.json`'s `scripts.test` is `node --test ...` → **node-test** (step 3).
2. Else if there are Python test files → Python (step 2).
3. Else if some JS file imports `node:test` → **node-test**.
4. Else → **other**: report that no supported tests were found.

Python flavour: **pytest-style** if any test file has `import pytest` / `from pytest`, a top-level
`def test...`, or a `class Test...` that is not a `unittest.TestCase`. Otherwise **unittest**.

## 2. Python

Work out `sys.path` the way pytest would:

- Config: walk from PATH up to the root and take the first of `pytest.ini`, `pyproject.toml` with
  `[tool.pytest.ini_options]`, `tox.ini` `[pytest]`, `setup.cfg` `[tool:pytest]`. Its directory
  is the *rootdir* (otherwise the repo root). Run from the rootdir.
- Path entries: each `pythonpath` entry from that config, `src/` if it exists, the rootdir, and
  the repo root.
- Each test file is imported from its *basedir*. That is the first ancestor directory without
  `__init__.py`. Its module name is the dotted path from there. Examples: `tests/test_x.py`
  without `__init__.py` gives basedir `tests/` and module `test_x`. `tests/unit/test_x.py` with
  `__init__.py` in both dirs gives basedir `.` and module `tests.unit.test_x`.
- If config sets `testpaths` and PATH is `.`, look for tests only under those directories.

**unittest only** (no pytest-style files): run each test directory with the stdlib runner:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 -m unittest discover -s TESTDIR -t TOPDIR -p 'test*.py' -v 2>&1
# a single file:  PYTHONPATH=src:. python3 -m unittest -v tests.test_cart   (from TOPDIR)
```

`TOPDIR` is the basedir above. Read the verbose lines: `test_add (test_calc.CalcTest) ... ok | FAIL | ERROR | skipped`.
Each `FAIL:`/`ERROR:` block that follows gives a traceback. Errors count as failing.
If a whole class shows as `ERROR: setUpClass (mod.Class)`, every test in that class is failing
with that message. For a subtest, the failure is reported once for its test.

**pytest-style** (pytest is absent): import each file and call its tests yourself with a short
driver script written to `$TMPDIR` (never into the repo). It should do the following:

1. Insert the path entries above into `sys.path`. Put a stub `pytest` module in
   `sys.modules['pytest']` that provides what the tests use. Usually that is `raises`
   (a context manager that fails with `DID NOT RAISE` when nothing is raised), `approx`,
   `fixture`, `mark.parametrize/skip/skipif/xfail` and `skip`/`fail`.
2. Import `conftest.py` files from the root down to the test's directory, then the test module.
   Use the module name from the basedir.
3. Collect top-level functions named `test*` and classes named `Test*`. Skip classes that have an
   `__init__`, and skip `unittest.TestCase` subclasses (run those with unittest). In a collected
   class, call each `test*` method on a fresh instance. Call `setup_method`/`teardown_method`
   and `setup_class`/`teardown_class` around them.
4. Pass fixtures by argument name. Look up `@pytest.fixture` functions in the class, then the
   module, then the nearest conftest. A `yield` fixture resumes after the test. Built-ins:
   `tmp_path`, `monkeypatch`, `capsys`, `caplog`, `request`.
   `@pytest.mark.parametrize` (and `params=` on a fixture) makes one test per value, with the id
   `name[v1-v2]`.
5. Outcome: returns normally → passed. Raises `AssertionError` → failed. Raises anything else
   (including `SystemExit` or a missing fixture) → failed, with the exception as the message.
   Skip → not counted. xfail that fails → not counted.
6. Message: `ExceptionType: text`. A bare `assert` has an empty text, so show the assert line
   and the values of the two sides, e.g. `AssertionError: assert 'abc' == 'cba'`.
   Line: the last traceback frame inside the test file.
   A file that fails to import is one failing entry, with id = the file's stem and message =
   the import error.

Ids: `Class.test_method` for any class (unittest or pytest-style). For a pytest-style function
it is `<module stem>.test_name`, e.g. `test_strutil.test_reverse`. FILTER keeps the tests whose
id (or `stem.id`) contains it.

The executable skill does all of this with `python3 skill.py --run-python '{"path": "PATH", "filter": "FILTER"}'`.
That is the `command` it reports, and it prints one `PASSED/FAILED <id>` line per test.

## 3. node:test

```sh
cd PKGDIR && node --test --test-reporter=tap [--test-name-pattern=ESCAPED_FILTER] [FILES...]
```

- If `scripts.test` is `node --test ARGS`, reuse ARGS. Drop any `--test-reporter`/`--watch`
  options. Node rejects a directory argument, so replace it with the test files inside it.
- Otherwise pass no files when every file that imports `node:test` matches node's default
  patterns (`*.test.js`, `*-test.js`, `*_test.js`, `test-*.js`, `test.js`, anything under a
  `test/` directory; also `.mjs`/`.cjs`/`.ts`). If some don't match, list all test files
  explicitly.
- FILTER is a substring: escape regex characters before `--test-name-pattern`.

Reading the TAP:

- Each `ok N - name` / `not ok N - name` line is followed by a YAML block (`---` … `...`).
  Count only entries with `type: 'test'`, never `type: 'suite'` (`describe` blocks).
- `# SKIP` / `# TODO` entries are not counted.
- A top-level passing entry whose name is a file path is a file with no matching tests, not a test.
- id = the name, with `\#` → `#` and `\\` → `\`.
- message = `name: error` from the YAML. If the error is `test failed`, the file failed to load;
  use the `# Error ...` diagnostic line printed above the entry instead.
- file/line = the first `stack:` frame in the test file (else `location:`). Make paths relative
  to the repo root.
- A `t.test` parent whose subtest failed is itself `not ok` (`N subtests failed`). Node counts it,
  and so does this skill.

## 4. Report

`passed` = passing tests; `failed` = number of failing entries; `exit_code` = the runner's exit
code (python: 0 all pass, 1 failures, 5 no tests; node: its own). If the run timed out, the
test that was running is a failing entry ("test did not finish"). `summary` is one line, e.g.
`pytest-style: 1 passed, 1 failed; first: test_strutil.test_reverse (tests/test_strutil.py:4) AssertionError: assert 'abc' == 'cba'`.
