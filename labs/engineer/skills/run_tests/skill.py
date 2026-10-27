#!/usr/bin/env python3
"""run_tests skill: detect a repository's test framework, run it, return structured failures.

Usage (cwd = repository root):
    python3 skill.py '{"path": ".", "filter": ""}'

The last line of stdout is one JSON object:
    {"framework", "command", "exit_code", "passed", "failed", "failing": [...], "summary"}

pytest cannot be installed here, so Python suites (unittest and pytest-style) are run by the
runner built into this file (`skill.py --run-python '<json>'`): it provides a small `pytest`
shim (raises, approx, fixture, mark.parametrize/skip/skipif/xfail, ...), pytest-style
assertion messages, fixtures (conftest.py, yield fixtures, tmp_path, monkeypatch, capsys,
caplog) and runs unittest.TestCase classes with unittest itself.  node:test suites run with
`node --test --test-reporter=tap` and the TAP is parsed.

Standard library only, Python 3.9 compatible, no network.  Writes only to $TMPDIR.
"""
import ast
import asyncio
import builtins
import collections
import configparser
import contextlib
import fnmatch
import importlib
import importlib.machinery
import importlib.util
import inspect
import io
import itertools
import json
import logging
import operator
import os
import pathlib
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import traceback
import types
import unittest
import warnings

SELF = os.path.abspath(__file__)
SKIP_DIRS = {"node_modules", "__pycache__", "venv", "env", "build", "dist", "site-packages",
             "CVS", "_darcs", "{arch}", "htmlcov"}
MAX_FAILING = 100
MAX_MESSAGE = 600
DEFAULT_TIMEOUT = 600


# ------------------------------------------------------------------------------- helpers

def _tmpdir():
    d = os.environ.get("TMPDIR") or tempfile.gettempdir()
    return d if os.path.isdir(d) else tempfile.gettempdir()


def _trim(text, limit=MAX_MESSAGE):
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit - 3] + "..."


def _short_repr(value, limit=120):
    try:
        r = repr(value)
    except Exception as e:  # a broken __repr__ must not hide the real failure
        r = "<repr failed: %s>" % type(e).__name__
    return r if len(r) <= limit else r[:limit - 3] + "..."


def _walk_files(top):
    """Yield files under top (or top itself), skipping hidden, vendored and build dirs."""
    if os.path.isfile(top):
        yield top
        return
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith(".") and d not in SKIP_DIRS
                             and not d.endswith((".egg-info", ".egg")))
        for name in sorted(filenames):
            yield os.path.join(dirpath, name)


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _rel(path, root):
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return path
    return path if rel.startswith("..") else rel


# ---------------------------------------------------------------------------- detection

JS_EXTS = (".js", ".mjs", ".cjs", ".ts", ".mts", ".cts")
NODE_TEST_IMPORT = re.compile(r"""['"]node:test['"]""")


def _is_py_test_file(name, patterns):
    return name.endswith(".py") and any(fnmatch.fnmatch(name, p) for p in patterns)


def _node_default_match(path, base):
    """node --test's default patterns (node >= 21), plus TypeScript via type stripping."""
    name = os.path.basename(path)
    if not name.endswith(JS_EXTS):
        return False
    stem = name.rsplit(".", 1)[0]
    if stem == "test" or stem.startswith("test-") or re.search(r"[.\-_]test$", stem):
        return True
    return "test" in _rel(os.path.dirname(path), base).split(os.sep)


def _package_json(root, target):
    """Nearest package.json from target up to root: (dir, parsed) or (None, None)."""
    d = target if os.path.isdir(target) else os.path.dirname(target)
    while True:
        p = os.path.join(d, "package.json")
        if os.path.isfile(p):
            try:
                return d, json.loads(_read(p) or "{}")
            except ValueError:
                return d, {}
        if os.path.samefile(d, root) or os.path.dirname(d) == d:
            return None, None
        d = os.path.dirname(d)


def _node_script_args(pkg):
    """If scripts.test is `node --test ...`, return its arguments after `node`."""
    script = ((pkg or {}).get("scripts") or {}).get("test") or ""
    script = re.split(r"&&|\|\||;|\|", script)[0].strip()
    try:
        tokens = shlex.split(script)
    except ValueError:
        return None
    if not tokens or os.path.basename(tokens[0]) != "node" or "--test" not in tokens:
        return None
    args, skip = [], False
    for tok in tokens[1:]:
        if skip:
            skip = False
            continue
        if tok in ("--test-reporter", "--test-reporter-destination"):
            skip = True
            continue
        if tok.startswith(("--test-reporter=", "--test-reporter-destination=", "--watch")):
            continue
        args.append(tok)
    return args


def detect(root, target):
    """Return "python", "node" or None for the tests under target."""
    py_patterns = _python_file_patterns(root, target)
    py_files, node_imports = [], []
    for f in _walk_files(target):
        name = os.path.basename(f)
        if _is_py_test_file(name, py_patterns):
            py_files.append(f)
        elif name.endswith(JS_EXTS) and NODE_TEST_IMPORT.search(_read(f)):
            node_imports.append(f)
    _, pkg = _package_json(root, target)
    if _node_script_args(pkg) is not None:
        return "node"
    if py_files:
        return "python"
    if node_imports:
        return "node"
    return None


# ------------------------------------------------------------------------- node runner

TAP_RESULT = re.compile(r"^(\s*)(ok|not ok)\s+\d+(?:\s+-\s+(.*))?$")
TAP_DIRECTIVE = re.compile(r"\s+#\s+(SKIP|TODO)\b.*$", re.I)
STACK_LOC = re.compile(r"(?:file://)?(/[^()]*?):(\d+):(\d+)\)?\s*$")


def _js_regex_escape(text):
    return re.sub(r"([.*+?^${}()|\[\]\\/])", r"\\\1", text)


def _yaml_scalar(val):
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] == "'":
        return val[1:-1].replace("''", "'")
    if len(val) >= 2 and val[0] == val[-1] == '"':
        try:
            return json.loads(val)
        except ValueError:
            return val[1:-1]
    return None if val == "~" else val


def _parse_yaml_block(lines):
    """Parse the flat YAML diagnostic block node writes under each TAP result."""
    out, i = {}, 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z_][\w-]*):\s?(.*)$", lines[i])
        i += 1
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        if val.strip() in ("", "|", "|-", "|+", ">", ">-"):
            block = []
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                block.append(lines[i][2:])
                i += 1
            out[key] = "\n".join(block).strip("\n")
            out.setdefault("__blocks__", set()).add(key)
        else:
            out[key] = _yaml_scalar(val)
    return out


def _node_message(d, diagnostics):
    err = d.get("error") or ""
    text = " ".join(l.strip() for l in str(err).splitlines() if l.strip())
    name = d.get("name") or ""
    if text == "test failed" and diagnostics:
        # a file that failed to load: the cause is in the '#' lines node printed before it
        hits = [l for l in diagnostics if re.search(r"\b\w*(Error|Exception)\b", l)]
        cause = hits[0] if hits else diagnostics[-1]
        return "test file failed to load: " + cause.strip()
    if name and name not in text:
        text = "%s: %s" % (name, text) if text else name
    blocks = d.get("__blocks__") or set()
    if "actual" in d and "expected" in d and not blocks & {"actual", "expected"} and \
            not str(err).startswith("Expected values") and str(d.get("actual")) not in text:
        text += " (expected: %s, actual: %s)" % (d.get("expected"), d.get("actual"))
    return text or d.get("failureType") or "failed"


def _node_location(d, root):
    file_, line = None, None
    loc = d.get("location") or ""
    m = STACK_LOC.search(loc)
    if m:
        file_, line = m.group(1), int(m.group(2))
    for frame in str(d.get("stack") or "").splitlines():
        sm = STACK_LOC.search(frame)
        if sm and (file_ is None or sm.group(1) == file_):
            file_, line = sm.group(1), int(sm.group(2))
            break
    return (_rel(file_, root) if file_ else None), line


def parse_tap(text, root, cwd=None):
    """Return (passed, failing, skipped) from node's TAP output, counting tests not suites."""
    lines = text.splitlines()
    passed, skipped, failing = 0, 0, []
    child_seen = collections.defaultdict(bool)  # indent -> a deeper result appeared since
    diagnostics = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = TAP_RESULT.match(line)
        if not m:
            stripped = line.strip()
            if stripped.startswith("#") and not re.match(r"#\s*(Subtest:|tests|suites|pass|fail|"
                                                         r"cancelled|skipped|todo|duration_ms)\b",
                                                         stripped):
                diagnostics.append(stripped[1:].strip())
            i += 1
            continue
        indent, status, rest = len(m.group(1)), m.group(2), m.group(3) or ""
        is_parent = child_seen[indent]
        child_seen[indent] = False
        for k in list(child_seen):
            if k < indent:
                child_seen[k] = True
        directive = TAP_DIRECTIVE.search(rest)
        name = re.sub(r"\\(.)", r"\1", TAP_DIRECTIVE.sub("", rest))
        block = []
        i += 1
        if i < len(lines) and lines[i].strip() == "---":
            pad = len(lines[i]) - len(lines[i].lstrip())
            i += 1
            while i < len(lines) and lines[i].strip() != "...":
                block.append(lines[i][pad:])
                i += 1
            i += 1
        d = _parse_yaml_block(block)
        kind = d.get("type")
        if kind == "suite" or (kind is None and is_parent):
            diagnostics = []
            continue
        if directive:
            skipped += 1
        elif status == "ok":
            # a file with no (matching) tests is reported as a passing "test" named by its path
            if not (indent == 0 and cwd and name.endswith(JS_EXTS) and
                    os.path.isfile(os.path.join(cwd, name))):
                passed += 1
        else:
            file_, line_no = _node_location(d, root)
            failing.append({"id": name, "file": file_, "line": line_no,
                            "message": _trim(_node_message(d, diagnostics))})
        diagnostics = []
    return passed, failing, skipped


def run_node(root, target, path, filt, timeout):
    pkg_dir, pkg = _package_json(root, target)
    cwd = target if os.path.isdir(target) else os.path.dirname(target)
    script_args = _node_script_args(pkg) if os.path.isdir(target) else None
    if script_args is not None:
        cwd = pkg_dir
        args = ["node"]
        for a in script_args:
            d = os.path.join(cwd, a)
            if not a.startswith("-") and os.path.isdir(d):
                # node --test does not accept directories; run the test files inside it
                args += sorted(_rel(f, cwd) for f in _walk_files(d) if f.endswith(JS_EXTS) and
                               (_node_default_match(f, d) or NODE_TEST_IMPORT.search(_read(f))))
            else:
                args.append(a)
    else:
        importers, defaults = set(), set()
        for f in _walk_files(target):
            if f.endswith(JS_EXTS):
                if NODE_TEST_IMPORT.search(_read(f)):
                    importers.add(f)
                if _node_default_match(f, cwd):
                    defaults.add(f)
        args = ["node", "--test"]
        if os.path.isfile(target) or not importers <= defaults:
            args += sorted(_rel(f, cwd) for f in importers | defaults)
    args.insert(args.index("--test") + 1, "--test-reporter=tap")
    if filt:
        args.insert(args.index("--test") + 1, "--test-name-pattern=" + _js_regex_escape(filt))
    rel_cwd = _rel(cwd, root)
    command = ("" if rel_cwd in (".", "") else "cd %s && " % shlex.quote(rel_cwd)) + \
        " ".join(shlex.quote(a) for a in args)
    try:
        proc = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, timeout=timeout)
        out, err, code = proc.stdout, proc.stderr, proc.returncode
    except FileNotFoundError:
        return _result("node-test", command, 127, 0, [], 0, "node is not on PATH")
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err, code = "timed out after %ss" % timeout, None
    passed, failing, skipped = parse_tap(out, root, cwd)
    note = ""
    if code is None:
        note = "timed out after %ss" % timeout
    elif code != 0 and not failing:
        note = "node exited %s: %s" % (code, _trim(err or out, 200))
    return _result("node-test", command, code, passed, failing, skipped, note)


# ------------------------------------------------------------------------ python runner
# Everything below runs inside `python3 skill.py --run-python '<json>'` (a child process), so
# test code never shares an interpreter with the skill's own bookkeeping.

def _ini_section(path, sections):
    cp = configparser.ConfigParser(interpolation=None)
    try:
        cp.read(path, encoding="utf-8")
    except configparser.Error:
        return None
    for s in sections:
        if cp.has_section(s):
            return {k: v.split() for k, v in cp.items(s)}
    return None


def _pyproject_section(path):
    text = _read(path)
    m = re.search(r"^\[tool\.pytest\.ini_options\][ \t]*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    if not m:
        return None
    out = {}
    for key in ("pythonpath", "testpaths", "python_files", "python_classes", "python_functions"):
        km = re.search(r"^%s\s*=\s*(\[.*?\]|\"[^\"]*\"|'[^']*')" % key, m.group(1), re.M | re.S)
        if km:
            vals = ["".join(t) for t in re.findall(r"\"([^\"]*)\"|'([^']*)'", km.group(1))]
            out[key] = [w for v in vals for w in v.split()]
    return out


def find_pytest_config(root, target):
    """Nearest pytest config from target up to root: (rootdir, options)."""
    d = target if os.path.isdir(target) else os.path.dirname(target)
    while True:
        for name, reader in (("pytest.ini", lambda p: _ini_section(p, ["pytest"]) or {}),
                             ("pyproject.toml", _pyproject_section),
                             ("tox.ini", lambda p: _ini_section(p, ["pytest"])),
                             ("setup.cfg", lambda p: _ini_section(p, ["tool:pytest"]))):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                cfg = reader(p)
                if cfg is not None:
                    return d, cfg
        if os.path.samefile(d, root) or os.path.dirname(d) == d:
            return root, {}
        d = os.path.dirname(d)


def _python_file_patterns(root, target):
    _, cfg = find_pytest_config(root, target)
    return cfg.get("python_files") or ["test*.py", "*_test.py"]


# --- assertion rewriting: `assert a == b` reports the values, like pytest -----------------

_CMP_OPS = {"Eq": ("==", operator.eq), "NotEq": ("!=", operator.ne), "Lt": ("<", operator.lt),
            "LtE": ("<=", operator.le), "Gt": (">", operator.gt), "GtE": (">=", operator.ge),
            "Is": ("is", operator.is_), "IsNot": ("is not", operator.is_not),
            "In": ("in", lambda a, b: a in b), "NotIn": ("not in", lambda a, b: a not in b)}


def _first_difference(left, right):
    if isinstance(left, (str, list, tuple)) and type(left) is type(right):
        for i, (a, b) in enumerate(zip(left, right)):
            if a != b:
                return "first difference at index %d: %s != %s" % (i, _short_repr(a, 60),
                                                                   _short_repr(b, 60))
        if len(left) != len(right):
            return "lengths differ: %d != %d" % (len(left), len(right))
    if isinstance(left, dict) and isinstance(right, dict):
        diff = sorted((set(left) ^ set(right)) | {k for k in set(left) & set(right)
                                                   if left[k] != right[k]}, key=repr)
        if diff:
            return "differing keys: " + _short_repr(diff, 100)
    return ""


def _rt_cmp(left, right, op, src, msg):
    sym, fn = _CMP_OPS[op]
    if fn(left, right):
        return
    text = "assert %s %s %s" % (_short_repr(left), sym, _short_repr(right))
    if src and src.replace(" ", "") != text[7:].replace(" ", ""):
        text += "  (from: assert %s)" % src
    if op == "Eq":
        hint = _first_difference(left, right)
        if hint:
            text += "; " + hint
    if msg is not None:
        text = "%s\n%s" % (msg(), text)
    raise AssertionError(text)


def _rt_val(value, src, msg):
    if value:
        return
    text = "assert %s" % src
    r = _short_repr(value)
    if r != src:
        text += "  (got %s)" % r
    if msg is not None:
        text = "%s\n%s" % (msg(), text)
    raise AssertionError(text)


class _AssertRewriter(ast.NodeTransformer):
    def __init__(self, source):
        self.source = source

    def visit_Assert(self, node):
        self.generic_visit(node)
        try:
            src = ast.get_source_segment(self.source, node.test) or ""
        except Exception:
            src = ""
        src = " ".join(src.split())
        if node.msg is not None:
            msg = ast.Lambda(args=ast.arguments(posonlyargs=[], args=[], vararg=None,
                                                kwonlyargs=[], kw_defaults=[], kwarg=None,
                                                defaults=[]), body=node.msg)
        else:
            msg = ast.Constant(None)
        t = node.test
        if isinstance(t, ast.Compare) and len(t.ops) == 1:
            call = ast.Call(ast.Name("__rt_cmp__", ast.Load()),
                            [t.left, t.comparators[0], ast.Constant(type(t.ops[0]).__name__),
                             ast.Constant(src), msg], [])
        else:
            call = ast.Call(ast.Name("__rt_val__", ast.Load()), [t, ast.Constant(src), msg], [])
        return ast.copy_location(ast.Expr(call), node)


_REWRITE = {}  # module name -> file path of test modules / conftests to rewrite


class _RewriteLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):  # never use (or write) cached bytecode
        path = self.get_filename(fullname)
        return self.source_to_code(self.get_data(path), path)

    def source_to_code(self, data, path, *, _optimize=-1):
        source = data.decode("utf-8") if isinstance(data, bytes) else data
        try:
            tree = _AssertRewriter(source).visit(ast.parse(source, filename=path))
            ast.fix_missing_locations(tree)
        except SyntaxError:
            return compile(data, path, "exec", dont_inherit=True)  # raises the real error
        return compile(tree, path, "exec", dont_inherit=True)


class _RewriteFinder:
    def find_spec(self, fullname, path=None, target=None):
        fp = _REWRITE.get(fullname)
        if fp is None:
            return None
        return importlib.util.spec_from_file_location(fullname, fp,
                                                      loader=_RewriteLoader(fullname, fp))


# --- the pytest shim ----------------------------------------------------------------------

class _OutcomeException(BaseException):
    def __init__(self, msg=""):
        BaseException.__init__(self, msg)
        self.msg = msg


class Skipped(_OutcomeException):
    pass


class Failed(_OutcomeException):
    pass


class XFailed(_OutcomeException):
    pass


class _FixtureLookupError(Exception):
    pass


_NOTSET = object()


def _fixture(fixture_function=None, *args, scope="function", params=None, autouse=False,
             ids=None, name=None):
    if isinstance(fixture_function, str):  # @pytest.fixture("module")
        scope, fixture_function = fixture_function, None

    def deco(fn):
        fn._rt_fixture = {"scope": scope if isinstance(scope, str) else "function",
                          "params": list(params) if params is not None else None,
                          "autouse": autouse, "ids": ids, "name": name or fn.__name__}
        return fn
    return deco(fixture_function) if callable(fixture_function) else deco


class Mark:
    def __init__(self, name, args, kwargs):
        self.name, self.args, self.kwargs = name, tuple(args), dict(kwargs)

    def __repr__(self):
        return "Mark(%r, %r, %r)" % (self.name, self.args, self.kwargs)


def _store_mark(obj, mark):
    current = obj.__dict__.get("pytestmark", []) if inspect.isclass(obj) else \
        getattr(obj, "pytestmark", [])
    current = list(current) if isinstance(current, (list, tuple)) else [current]
    obj.pytestmark = current + [mark]


class MarkDecorator:
    def __init__(self, mark):
        self.mark = mark
        self.name, self.args, self.kwargs = mark.name, mark.args, mark.kwargs

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and not kwargs and (inspect.isfunction(args[0]) or
                                              inspect.isclass(args[0])):
            _store_mark(args[0], self.mark)
            return args[0]
        return self.with_args(*args, **kwargs)

    def with_args(self, *args, **kwargs):
        kw = dict(self.mark.kwargs)
        kw.update(kwargs)
        return MarkDecorator(Mark(self.mark.name, self.mark.args + args, kw))


class MarkGenerator:
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return MarkDecorator(Mark(name, (), {}))


def _get_marks(obj):
    marks = getattr(obj, "pytestmark", [])
    if not isinstance(marks, (list, tuple)):
        marks = [marks]
    return [m.mark if isinstance(m, MarkDecorator) else m for m in marks if
            isinstance(m, (Mark, MarkDecorator))]


class ParameterSet:
    def __init__(self, values, id=None, marks=()):
        self.values, self.id = values, id
        self.marks = [m.mark if isinstance(m, MarkDecorator) else m for m in
                      (marks if isinstance(marks, (list, tuple)) else [marks])]


def _param(*values, id=None, marks=()):
    return ParameterSet(values, id, marks)


class ExceptionInfo:
    def __init__(self):
        self.type = self.value = self.tb = None

    @property
    def typename(self):
        return self.type.__name__ if self.type else None

    def match(self, regexp):
        if not re.search(regexp, str(self.value)):
            raise AssertionError("Regex pattern %r does not match %r." % (regexp, str(self.value)))
        return True

    def errisinstance(self, exc):
        return isinstance(self.value, exc)

    def __repr__(self):
        return "<ExceptionInfo %s>" % _short_repr(self.value)


def _exc_names(expected):
    if isinstance(expected, tuple):
        return " or ".join(e.__name__ for e in expected)
    return getattr(expected, "__name__", str(expected))


class _RaisesContext:
    def __init__(self, expected, match):
        self.expected, self.match, self.excinfo = expected, match, ExceptionInfo()

    def __enter__(self):
        return self.excinfo

    def __exit__(self, et, ev, tb):
        if et is None:
            raise Failed("DID NOT RAISE %s" % _exc_names(self.expected))
        if not issubclass(et, self.expected):
            return False
        self.excinfo.type, self.excinfo.value, self.excinfo.tb = et, ev, tb
        if self.match is not None and not re.search(self.match, str(ev)):
            raise AssertionError("Regex pattern did not match.\n Regex: %r\n Input: %r"
                                 % (self.match, str(ev)))
        return True


def _raises(expected, *args, match=None, **kwargs):
    if args:
        ctx = _RaisesContext(expected, None)
        with ctx:
            args[0](*args[1:], **kwargs)
        return ctx.excinfo
    return _RaisesContext(expected, match)


class _WarnsContext(list):
    def __init__(self, expected, match):
        list.__init__(self)
        self.expected, self.match = expected or Warning, match

    def __enter__(self):
        self._cm = warnings.catch_warnings(record=True)
        self._log = self._cm.__enter__()  # catch_warnings appends to the list it returns
        warnings.simplefilter("always")
        return self

    def __exit__(self, et, ev, tb):
        self._cm.__exit__(et, ev, tb)
        self[:] = self._log
        if et is not None:
            return False
        if not any(issubclass(w.category, self.expected) and
                   (self.match is None or re.search(self.match, str(w.message))) for w in self):
            raise Failed("DID NOT WARN. No warnings of type %s were emitted."
                         % _exc_names(self.expected))
        return False

    def pop(self, cls=Warning):
        for i, w in enumerate(self):
            if issubclass(w.category, cls):
                return list.pop(self, i)
        raise AssertionError("%r not found in warning list" % cls)


def _warns(expected=Warning, *args, match=None, **kwargs):
    ctx = _WarnsContext(expected, match)
    if args:
        with ctx:
            return args[0](*args[1:], **kwargs)
    return ctx


def _deprecated_call(*args, **kwargs):
    return _warns((DeprecationWarning, PendingDeprecationWarning), *args, **kwargs)


class _Approx:
    def __init__(self, expected, rel=None, abs=None, nan_ok=False):
        self.expected, self.rel, self.abs, self.nan_ok = expected, rel, abs, nan_ok

    def _tolerance(self, e):
        if self.rel is None and self.abs is None:
            return max(1e-6 * builtins.abs(e), 1e-12)
        return max((self.rel or 0) * builtins.abs(e), self.abs or 0)

    def _scalar_eq(self, a, e):
        if isinstance(e, _Approx):
            return e == a
        try:
            if a == e:
                return True
            if self.nan_ok and a != a and e != e:
                return True
            return builtins.abs(a - e) <= self._tolerance(e)
        except TypeError:
            return False

    def __eq__(self, actual):
        e = self.expected
        if isinstance(e, dict):
            return isinstance(actual, dict) and set(actual) == set(e) and \
                all(self._scalar_eq(actual[k], e[k]) for k in e)
        if isinstance(e, (list, tuple)):
            try:
                return len(actual) == len(e) and \
                    all(self._scalar_eq(a, x) for a, x in zip(actual, e))
            except TypeError:
                return False
        return self._scalar_eq(actual, e)

    def __ne__(self, actual):
        return not self == actual

    __hash__ = None

    def __repr__(self):
        return "approx(%r)" % (self.expected,)


def _skip(reason="", allow_module_level=False, msg=None):
    raise Skipped(msg or reason)


def _fail(reason="", pytrace=True, msg=None):
    raise Failed(msg or reason)


def _xfail(reason=""):
    raise XFailed(reason)


def _importorskip(modname, minversion=None, reason=None):
    try:
        mod = importlib.import_module(modname)
    except ImportError:
        raise Skipped(reason or "could not import %r" % modname)
    return mod


def _build_pytest_module():
    m = types.ModuleType("pytest")
    m.__doc__ = "run_tests skill shim: pytest is not installed in this environment."
    m.__version__ = "0.0-run_tests-shim"
    m.fixture = _fixture
    m.yield_fixture = _fixture
    m.mark = MarkGenerator()
    m.param = _param
    m.raises = _raises
    m.warns = _warns
    m.deprecated_call = _deprecated_call
    m.approx = _Approx
    m.skip = _skip
    m.fail = _fail
    m.xfail = _xfail
    m.importorskip = _importorskip
    m.MonkeyPatch = MonkeyPatch
    m.ExceptionInfo = ExceptionInfo
    m.Mark = Mark
    m.MarkDecorator = MarkDecorator
    m.skip.Exception = Skipped
    m.fail.Exception = Failed
    m.xfail.Exception = XFailed
    m.UsageError = type("UsageError", (Exception,), {})
    return m


# --- built-in fixtures ----------------------------------------------------------------------

class MonkeyPatch:
    def __init__(self):
        self._attrs, self._items, self._env = [], [], []
        self._cwd, self._syspath = None, None

    @classmethod
    @contextlib.contextmanager
    def context(cls):
        mp = cls()
        try:
            yield mp
        finally:
            mp.undo()

    @staticmethod
    def _resolve(dotted):
        parts = dotted.split(".")
        for i in range(len(parts), 0, -1):
            try:
                obj = importlib.import_module(".".join(parts[:i]))
            except ImportError:
                continue
            for p in parts[i:]:
                obj = getattr(obj, p)
            return obj
        raise ImportError("could not import %r" % dotted)

    def setattr(self, target, name, value=_NOTSET, raising=True):
        if value is _NOTSET:
            if not isinstance(target, str):
                raise TypeError("use setattr(target, name, value) or setattr('mod.attr', value)")
            value = name
            target, name = target.rsplit(".", 1)
            target = self._resolve(target)
        elif isinstance(target, str):
            target = self._resolve(target)
        old = getattr(target, name, _NOTSET)
        if raising and old is _NOTSET:
            raise AttributeError("%r has no attribute %r" % (target, name))
        if inspect.isclass(target):
            old = target.__dict__.get(name, _NOTSET)
        self._attrs.append((target, name, old))
        setattr(target, name, value)

    def delattr(self, target, name=_NOTSET, raising=True):
        if name is _NOTSET:
            target, name = target.rsplit(".", 1)
            target = self._resolve(target)
        if not hasattr(target, name):
            if raising:
                raise AttributeError(name)
            return
        old = target.__dict__.get(name, _NOTSET) if inspect.isclass(target) else \
            getattr(target, name)
        self._attrs.append((target, name, old))
        delattr(target, name)

    def setitem(self, dic, name, value):
        self._items.append((dic, name, dic.get(name, _NOTSET)))
        dic[name] = value

    def delitem(self, dic, name, raising=True):
        if name not in dic:
            if raising:
                raise KeyError(name)
            return
        self._items.append((dic, name, dic[name]))
        del dic[name]

    def setenv(self, name, value, prepend=None):
        value = str(value)
        if prepend and name in os.environ:
            value = value + prepend + os.environ[name]
        self._env.append((name, os.environ.get(name)))
        os.environ[name] = value

    def delenv(self, name, raising=True):
        if name not in os.environ:
            if raising:
                raise KeyError(name)
            return
        self._env.append((name, os.environ.get(name)))
        del os.environ[name]

    def syspath_prepend(self, path):
        if self._syspath is None:
            self._syspath = list(sys.path)
        sys.path.insert(0, str(path))
        importlib.invalidate_caches()

    def chdir(self, path):
        if self._cwd is None:
            self._cwd = os.getcwd()
        os.chdir(str(path))

    def undo(self):
        for target, name, old in reversed(self._attrs):
            if old is _NOTSET:
                try:
                    delattr(target, name)
                except AttributeError:
                    pass
            else:
                setattr(target, name, old)
        for dic, name, old in reversed(self._items):
            if old is _NOTSET:
                dic.pop(name, None)
            else:
                dic[name] = old
        for name, old in reversed(self._env):
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old
        self._attrs, self._items, self._env = [], [], []
        if self._syspath is not None:
            sys.path[:] = self._syspath
            self._syspath = None
        if self._cwd is not None:
            os.chdir(self._cwd)
            self._cwd = None


CaptureResult = collections.namedtuple("CaptureResult", "out err")


class _Capsys:
    def __init__(self):
        self._old = (sys.stdout, sys.stderr)
        self._out, self._err = io.StringIO(), io.StringIO()
        sys.stdout, sys.stderr = self._out, self._err

    def readouterr(self):
        out, err = self._out.getvalue(), self._err.getvalue()
        for buf in (self._out, self._err):
            buf.seek(0)
            buf.truncate()
        return CaptureResult(out, err)

    @contextlib.contextmanager
    def disabled(self):
        sys.stdout, sys.stderr = self._old
        try:
            yield
        finally:
            sys.stdout, sys.stderr = self._out, self._err

    def _close(self):
        sys.stdout, sys.stderr = self._old


class _LogHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self, 0)
        self.records = []
        self.setFormatter(logging.Formatter("%(levelname)-8s %(name)s:%(filename)s:%(lineno)d "
                                            "%(message)s"))

    def emit(self, record):
        self.records.append(record)


class _Caplog:
    def __init__(self, handler):
        self.handler, self._levels = handler, []

    records = property(lambda self: self.handler.records)
    messages = property(lambda self: [r.getMessage() for r in self.records])
    record_tuples = property(lambda self: [(r.name, r.levelno, r.getMessage())
                                           for r in self.records])
    text = property(lambda self: "\n".join(self.handler.format(r) for r in self.records))

    def clear(self):
        del self.handler.records[:]

    def set_level(self, level, logger=None):
        lg = logging.getLogger(logger)
        self._levels.append((lg, lg.level))
        lg.setLevel(level)
        self.handler.setLevel(level)

    @contextlib.contextmanager
    def at_level(self, level, logger=None):
        lg = logging.getLogger(logger)
        old = lg.level
        lg.setLevel(level)
        try:
            yield
        finally:
            lg.setLevel(old)

    def _close(self):
        for lg, level in reversed(self._levels):
            lg.setLevel(level)


class _TmpPathFactory:
    def __init__(self):
        self._base = None

    def getbasetemp(self):
        if self._base is None:
            self._base = pathlib.Path(tempfile.mkdtemp(prefix="run_tests-", dir=_tmpdir()))
        return self._base

    def mktemp(self, basename, numbered=True):
        base = self.getbasetemp()
        if numbered:
            return pathlib.Path(tempfile.mkdtemp(prefix=basename, dir=str(base)))
        p = base / basename
        p.mkdir()
        return p


_TMP_FACTORY = _TmpPathFactory()


def _fx_tmp_path(request):
    name = re.sub(r"[^\w]", "_", request.node.name)[:30]
    return _TMP_FACTORY.mktemp(name)


def _fx_tmp_path_factory():
    return _TMP_FACTORY


def _fx_monkeypatch():
    mp = MonkeyPatch()
    yield mp
    mp.undo()


def _fx_capsys():
    cap = _Capsys()
    yield cap
    cap._close()


def _fx_caplog():
    handler = _LogHandler()
    logging.getLogger().addHandler(handler)
    cap = _Caplog(handler)
    yield cap
    logging.getLogger().removeHandler(handler)
    cap._close()


_BUILTIN_FIXTURES = {"tmp_path": (_fx_tmp_path, "function"),
                     "tmpdir": (_fx_tmp_path, "function"),
                     "tmp_path_factory": (_fx_tmp_path_factory, "session"),
                     "tmpdir_factory": (_fx_tmp_path_factory, "session"),
                     "monkeypatch": (_fx_monkeypatch, "function"),
                     "capsys": (_fx_capsys, "function"),
                     "capfd": (_fx_capsys, "function"),
                     "caplog": (_fx_caplog, "function")}


# --- collection ---------------------------------------------------------------------------

class _FixtureDef:
    def __init__(self, name, func, scope, params=None, ids=None, autouse=False, owner=None):
        self.name, self.func, self.scope = name, func, scope
        self.params, self.ids, self.autouse, self.owner = params, ids, autouse, owner
        self.argnames = _argnames(func, skip_first=owner is not None and
                                  not isinstance(inspect.getattr_static(owner, func.__name__,
                                                                        None), staticmethod))


def _argnames(func, skip_first=False):
    """Names a test/fixture requests: positional params without defaults (minus mock args)."""
    try:
        params = list(inspect.signature(func).parameters.values())
    except (TypeError, ValueError):
        return []
    if skip_first and params:
        params = params[1:]
    patchings = getattr(func, "patchings", None) or []
    n_mock = len([p for p in patchings if not getattr(p, "attribute_name", None) and
                  getattr(p, "new", None) is getattr(sys.modules.get("unittest.mock"),
                                                     "DEFAULT", object())])
    params = params[n_mock:]
    return [p.name for p in params
            if p.default is p.empty and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]


def _fixtures_in(namespace, owner=None):
    out = []
    for value in namespace.values():
        raw = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value
        info = getattr(raw, "_rt_fixture", None)
        if isinstance(info, dict) and callable(raw):
            out.append(_FixtureDef(info["name"], raw, info["scope"], info["params"], info["ids"],
                                   info["autouse"], owner))
    return out


def _idval(value, argname, idx):
    if isinstance(value, str):
        return value.encode("unicode_escape").decode("ascii")
    if value is None or isinstance(value, (int, float, bool, complex)):
        return str(value)
    if isinstance(value, type) or inspect.isroutine(value):
        return getattr(value, "__name__", "%s%d" % (argname, idx))
    return "%s%d" % (argname, idx)


def _param_sets(mark):
    """[(values dict, id, marks, indirect names)] for one parametrize mark."""
    args, kw = mark.args, mark.kwargs
    argnames = args[0] if args else kw.get("argnames")
    argvalues = args[1] if len(args) > 1 else kw.get("argvalues", [])
    names = [n.strip() for n in argnames.split(",") if n.strip()] if isinstance(argnames, str) \
        else list(argnames)
    ids = args[3] if len(args) > 3 else kw.get("ids")
    indirect = args[2] if len(args) > 2 else kw.get("indirect", False)
    indirect = set(names) if indirect is True else set(indirect or ())
    argvalues = list(argvalues)
    if not argvalues:
        return [({n: None for n in names}, "NOTSET",
                 [Mark("skip", (), {"reason": "got empty parameter set"})], indirect)]
    out = []
    for i, v in enumerate(argvalues):
        pid, pmarks = None, []
        if isinstance(v, ParameterSet):
            vals, pid, pmarks = v.values, v.id, v.marks
        else:
            vals = (v,) if len(names) == 1 else tuple(v)
        if pid is None and ids is not None:
            if callable(ids):
                parts = [ids(x) for x in vals]
                if all(p is not None for p in parts):
                    pid = "-".join(str(p) for p in parts)
            elif i < len(ids) and ids[i] is not None:
                pid = ids[i]
        if pid is None:
            pid = "-".join(_idval(x, n, i) for x, n in zip(vals, names))
        out.append((dict(zip(names, vals)), str(pid), list(pmarks), indirect))
    return out


class _Item:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.instance = None

    @property
    def name(self):
        return self.id.rsplit(".", 1)[-1] if "[" not in self.id else \
            self.id[:self.id.index("[")].rsplit(".", 1)[-1] + self.id[self.id.index("["):]

    def get_closest_marker(self, name):
        for m in reversed(self.marks):
            if m.name == name:
                return m
        return None

    def iter_markers(self, name=None):
        return [m for m in self.marks if name is None or m.name == name]

    def add_marker(self, marker):
        self.marks.append(marker.mark if isinstance(marker, MarkDecorator) else marker)


class _Config:
    def __init__(self, rootdir):
        self.rootdir = self.rootpath = pathlib.Path(rootdir)

    def getoption(self, name, default=None, skip=False):
        return default

    def getini(self, name):
        return []


class _Request:
    def __init__(self, run, fixturedef=None, param=_NOTSET):
        self._run, self._fd = run, fixturedef
        item = run.item
        self.node = item
        self.function = item.func
        self.cls = item.cls
        self.instance = item.instance
        self.module = item.module
        self.config = run.sess.config
        self.fixturename = fixturedef.name if fixturedef else None
        self.scope = fixturedef.scope if fixturedef else "function"
        self.keywords = {m.name: m for m in item.marks}
        if param is not _NOTSET:
            self.param = param

    def addfinalizer(self, fn):
        self._run.sess.add_finalizer(self._run.sess.scope_key(self.scope, self._run.item), fn)

    def getfixturevalue(self, name):
        return self._run.get(name)

    def applymarker(self, marker):
        self.node.add_marker(marker)


def _finish_gen(gen, name):
    try:
        next(gen)
    except StopIteration:
        return
    raise RuntimeError("fixture %r yielded more than once" % name)


class _Run:
    """Fixture resolution for one test item."""

    def __init__(self, sess, item):
        self.sess, self.item, self.values = sess, item, {}

    def get(self, name, level=None, stack=()):
        item = self.item
        if name == "request":
            return _Request(self)
        if level is None and name in item.direct:
            return item.direct[name]
        defs = item.fixtures.get(name) or []
        lvl = len(defs) - 1 if level is None else level
        if lvl < 0:
            raise _FixtureLookupError("fixture %r not found" % name)
        if (name, lvl) in self.values:
            return self.values[(name, lvl)]
        if (name, lvl) in stack:
            raise _FixtureLookupError("recursive dependency involving fixture %r" % name)
        fd = defs[lvl]
        param, pkey = _NOTSET, None
        if name in item.indirect:
            param, pkey = item.indirect[name], ("indirect", item.id)
        elif fd.params is not None:
            pkey, param = item.fparams.get(name, (0, fd.params[0] if fd.params else None))
        skey = self.sess.scope_key(fd.scope, item)
        ckey = (id(fd), skey, repr(pkey))
        if fd.scope != "function" and ckey in self.sess.cache:
            value = self.sess.cache[ckey]
        else:
            kwargs = {}
            for a in fd.argnames:
                if a == "request":
                    kwargs[a] = _Request(self, fd, param)
                else:
                    kwargs[a] = self.get(a, lvl - 1 if a == name else None,
                                         stack + ((name, lvl),))
            func = fd.func
            if fd.owner is not None and item.instance is not None and \
                    not isinstance(inspect.getattr_static(fd.owner, func.__name__, None),
                                   staticmethod):
                func = func.__get__(item.instance)
            if inspect.isgeneratorfunction(fd.func):
                gen = func(**kwargs)
                value = next(gen)
                self.sess.add_finalizer(skey, lambda gen=gen: _finish_gen(gen, name))
            else:
                value = func(**kwargs)
            if fd.scope != "function":
                self.sess.cache[ckey] = value
        self.values[(name, lvl)] = value
        return value


def _exc_message(e):
    if isinstance(e, _OutcomeException):
        return "%s: %s" % (type(e).__name__, e.msg) if e.msg else type(e).__name__
    if isinstance(e, _FixtureLookupError):
        return str(e)
    text = str(e)
    return "%s: %s" % (type(e).__name__, text) if text else type(e).__name__


class _Recorder:
    def __init__(self, result_path, root):
        self.f = open(result_path, "a", encoding="utf-8") if result_path else None
        self.out = sys.stdout
        self.root = root
        self.counts = collections.Counter()

    def write(self, **rec):
        if self.f:
            self.f.write(json.dumps(rec) + "\n")
            self.f.flush()

    def start(self, tid):
        self.write(t="start", id=tid)

    def test(self, tid, outcome, file_=None, line=None, message=None, kind="pytest"):
        self.counts[outcome] += 1
        rel = _rel(file_, self.root) if file_ else None
        self.write(t="test", id=tid, outcome=outcome, file=rel, line=line,
                   message=_trim(message) if message else None, kind=kind)
        text = "%-8s %s" % (outcome.upper(), tid)
        if outcome == "failed":
            text += "\n    %s:%s\n    %s" % (rel, line, (message or "").replace("\n", "\n    "))
        self.out.write(text + "\n")
        self.out.flush()


class _Session:
    def __init__(self, root, rootdir, cfg, filt, rec):
        self.root, self.rootdir, self.cfg, self.filt, self.rec = root, rootdir, cfg, filt, rec
        self.config = _Config(rootdir)
        self.cache, self.finalizers = {}, collections.OrderedDict()
        self.conftests = {}
        self.kinds = set()
        self.func_patterns = cfg.get("python_functions") or ["test"]
        self.class_patterns = cfg.get("python_classes") or ["Test"]
        self.builtins = [_FixtureDef(n, f, s) for n, (f, s) in _BUILTIN_FIXTURES.items()]

    # -- naming / matching
    @staticmethod
    def _match(name, patterns):
        return any(fnmatch.fnmatch(name, p) if any(c in p for c in "*?[") else
                   name.startswith(p) for p in patterns)

    def selected(self, tid, stem, relfile):
        if not self.filt:
            return True
        return any(self.filt in s for s in (tid, stem + "." + tid,
                                            relfile + "::" + tid.replace(".", "::")))

    # -- scopes and finalizers
    def scope_key(self, scope, item):
        if scope == "function":
            return ("function", item.uid)
        if scope == "class":
            return ("class", item.file, item.clsqual)
        if scope == "module":
            return ("module", item.file)
        return ("session",)

    def add_finalizer(self, key, fn):
        self.finalizers.setdefault(key, []).append(fn)

    def finalize(self, match):
        """Run finalizers whose scope key satisfies match(key); return the first error."""
        first = None
        for key in [k for k in reversed(self.finalizers) if match(k)]:
            for fn in reversed(self.finalizers.pop(key)):
                try:
                    fn()
                except BaseException as e:  # noqa: B902 - report, don't crash the runner
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    first = first or e
            for ck in [c for c in self.cache if c[1] == key]:
                del self.cache[ck]
        return first

    # -- importing
    def import_file(self, path):
        d, parts = os.path.dirname(path), [os.path.splitext(os.path.basename(path))[0]]
        while os.path.isfile(os.path.join(d, "__init__.py")) and os.path.dirname(d) != d:
            parts.insert(0, os.path.basename(d))
            d = os.path.dirname(d)
        if d not in sys.path:
            sys.path.insert(0, d)
        name = ".".join(parts)
        old = sys.modules.get(name)
        if old is not None:
            old_file = getattr(old, "__file__", None)
            if old_file and os.path.abspath(old_file) == os.path.abspath(path):
                return old
            del sys.modules[name]  # same module name in another directory
        _REWRITE[name] = path
        importlib.invalidate_caches()
        return importlib.import_module(name)

    def conftest_layers(self, path):
        """Fixtures from conftest.py files between the repo root and the test file."""
        dirs, d = [], os.path.dirname(path)
        while True:
            dirs.insert(0, d)
            if d == self.root or os.path.dirname(d) == d or \
                    not d.startswith(self.root + os.sep):
                break
            d = os.path.dirname(d)
        layers = []
        for d in dirs:
            p = os.path.join(d, "conftest.py")
            if not os.path.isfile(p):
                continue
            if p not in self.conftests:
                try:
                    mod = self.import_file(p)
                    self.conftests[p] = _fixtures_in(vars(mod))
                except Skipped:
                    self.conftests[p] = []
                except BaseException as e:
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    self.conftests[p] = e
            if isinstance(self.conftests[p], BaseException):
                raise self.conftests[p]
            layers.append(self.conftests[p])
        return layers

    # -- collection
    def collect(self, mod, path, stem, relfile, layers):
        items, ucases = [], []
        modmarks = _get_marks(mod)
        for name, obj in list(vars(mod).items()):
            if inspect.isclass(obj):
                if obj.__dict__.get("__test__", True) is False:
                    continue
                if issubclass(obj, unittest.TestCase):
                    if not obj.__module__.startswith("unittest"):
                        ucases.append(obj)
                elif self._match(name, self.class_patterns):
                    self.collect_class(obj, mod, path, stem, relfile, layers, modmarks, items)
            elif inspect.isfunction(obj) and self._match(name, self.func_patterns) and \
                    not hasattr(obj, "_rt_fixture") and getattr(obj, "__test__", True):
                items += self.make_items(mod, path, stem, relfile, None, None, obj, name, layers,
                                         modmarks)
        return items, ucases

    def collect_class(self, cls, mod, path, stem, relfile, layers, marks, items, qual=None):
        if any("__init__" in k.__dict__ for k in cls.__mro__ if k is not object):
            return  # pytest cannot collect classes with __init__
        qual = (qual + "." if qual else "") + cls.__name__
        cls_layers = layers + [_fixtures_in(vars(k), owner=cls) for k in reversed(cls.__mro__)
                               if k is not object]
        cls_marks = marks + _get_marks(cls)
        names = []
        for k in reversed(cls.__mro__):
            for n in vars(k):
                if n not in names:
                    names.append(n)
        for n in names:
            raw = inspect.getattr_static(cls, n)
            if inspect.isclass(raw) and self._match(n, self.class_patterns) and \
                    not issubclass(raw, unittest.TestCase):
                self.collect_class(raw, mod, path, stem, relfile, cls_layers, cls_marks, items,
                                   qual)
                continue
            func = raw.__func__ if isinstance(raw, (staticmethod, classmethod)) else raw
            if not inspect.isfunction(func) or not self._match(n, self.func_patterns) or \
                    hasattr(func, "_rt_fixture"):
                continue
            items += self.make_items(mod, path, stem, relfile, cls, qual, func, n, cls_layers,
                                     cls_marks, static=isinstance(raw, staticmethod))

    def make_items(self, mod, path, stem, relfile, cls, qual, func, name, layers, marks,
                   static=False):
        fixtures = {}
        for layer in [self.builtins] + layers:
            for fd in layer:
                fixtures.setdefault(fd.name, []).append(fd)
        autouse = []
        for layer in layers:
            for fd in layer:
                if fd.autouse and fd.name not in autouse:
                    autouse.append(fd.name)
        marks = _get_marks(func) + list(marks)
        use = [a for m in marks if m.name == "usefixtures" for a in m.args]
        argnames = _argnames(func, skip_first=cls is not None and not static)
        base = "%s.%s" % (cls.__name__ if cls else stem, name)
        unwrapped = inspect.unwrap(func)
        try:
            src_file = os.path.abspath(inspect.getsourcefile(unwrapped) or path)
            lineno = inspect.getsourcelines(unwrapped)[1]
        except (TypeError, OSError):
            src_file, lineno = path, None
        psets = [_param_sets(m) for m in marks if m.name == "parametrize"]
        out = []
        for combo in itertools.product(*psets) if psets else [()]:
            direct, indirect, ids, extra = {}, {}, [], []
            for vals, pid, pmarks, ind in combo:
                for k, v in vals.items():
                    (indirect if k in ind else direct)[k] = v
                ids.append(pid)
                extra += pmarks
            # fixtures with params= multiply the test, like pytest
            order, seen = [], set()

            def visit(n, lvl=None):
                if (lvl is None and n in direct) or n == "request":
                    return
                defs = fixtures.get(n) or []
                lv = len(defs) - 1 if lvl is None else lvl
                if lv < 0 or (n, lv) in seen:
                    return
                seen.add((n, lv))
                for a in defs[lv].argnames:
                    visit(a, lv - 1 if a == n else None)
                order.append(defs[lv])
            for n in autouse + use + argnames:
                visit(n)
            fparam_lists = []
            for fd in order:
                if fd.params is not None and fd.name not in indirect:
                    opts = []
                    for i, v in enumerate(fd.params):
                        pid = None
                        if isinstance(v, ParameterSet):
                            pid, v = v.id, (v.values[0] if v.values else None)
                        if pid is None and fd.ids is not None:
                            pid = fd.ids(v) if callable(fd.ids) else \
                                (fd.ids[i] if i < len(fd.ids) else None)
                        opts.append((fd.name, i, v, str(pid) if pid is not None else
                                     _idval(v, fd.name, i)))
                    fparam_lists.append(opts)
            for fcombo in itertools.product(*fparam_lists) if fparam_lists else [()]:
                all_ids = ids + [o[3] for o in fcombo]
                tid = base + ("[%s]" % "-".join(all_ids) if all_ids else "")
                if not self.selected(tid, stem, relfile):
                    continue
                out.append(_Item(id=tid, uid=(path, tid), file=path, src_file=src_file,
                                 lineno=lineno, cls=cls, clsqual=qual, func=func, attr=name,
                                 static=static, module=mod, marks=marks + extra, direct=direct,
                                 indirect=indirect,
                                 fparams={o[0]: (o[1], o[2]) for o in fcombo},
                                 fixtures=fixtures, autouse=autouse + use, argnames=argnames))
        return out

    # -- running
    def _locate(self, tb, item_file, fallback):
        """Line in the test file where the failure surfaced, and where it was raised."""
        line, raised = None, None
        for fs in traceback.extract_tb(tb):
            fn = os.path.abspath(fs.filename)
            if fn == item_file:
                line = fs.lineno
            if fn.startswith(self.root + os.sep) and fn != SELF and "site-packages" not in fn:
                raised = (fn, fs.lineno)
        if raised and raised[0] == item_file:
            raised = None
        return line or fallback, raised

    def _failure(self, tid, e, item_file, fallback, kind, prefix=""):
        line, raised = self._locate(e.__traceback__, item_file, fallback)
        msg = prefix + _exc_message(e)
        if isinstance(e, SyntaxError) and e.filename:
            item_file, line = os.path.abspath(e.filename), e.lineno
        elif raised:
            msg += "  (raised at %s:%s)" % (_rel(raised[0], self.root), raised[1])
        self.rec.test(tid, "failed", item_file, line, msg, kind)

    def _eval_cond(self, cond, item):
        if isinstance(cond, str):
            ns = {"os": os, "sys": sys, "platform": platform, "config": self.config}
            ns.update(vars(item.module))
            return bool(eval(cond, ns))
        return bool(cond)

    def run_item(self, item, class_error):
        rec = self.rec
        for m in item.marks:
            reason = None
            if m.name == "skip":
                reason = m.kwargs.get("reason") or (m.args[0] if m.args else "skipped")
            elif m.name == "skipif":
                conds = m.args or (m.kwargs.get("condition"),)
                if any(self._eval_cond(c, item) for c in conds):
                    reason = m.kwargs.get("reason", "skipif")
            if reason:
                rec.test(item.id, "skipped", item.src_file, item.lineno, reason)
                return
        xfail = None
        for m in item.marks:
            if m.name == "xfail":
                cond = m.args[0] if m.args else m.kwargs.get("condition", True)
                if self._eval_cond(cond, item):
                    xfail = m
        if xfail is not None and not xfail.kwargs.get("run", True):
            rec.test(item.id, "xfailed", item.src_file, item.lineno)
            return
        rec.start(item.id)
        run = _Run(self, item)
        saved = (sys.stdout, sys.stderr)
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        err, cwd = None, os.getcwd()
        try:
            if class_error is not None:
                raise class_error
            if item.cls is not None:
                item.instance = item.cls()
                setup = getattr(item.instance, "setup_method", None)
                if setup:
                    _call_optional(setup, getattr(item.instance, item.attr))
            elif hasattr(item.module, "setup_function"):
                _call_optional(item.module.setup_function, item.func)
            for n in item.autouse:
                run.get(n)
            kwargs = {n: run.get(n) for n in item.argnames}
            fn = getattr(item.instance, item.attr) if item.instance is not None else item.func
            result = fn(**kwargs)
            if inspect.isawaitable(result):
                asyncio.run(_await(result))
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            err = e
        try:
            if item.instance is not None and hasattr(item.instance, "teardown_method"):
                _call_optional(item.instance.teardown_method, getattr(item.instance, item.attr))
            elif item.cls is None and hasattr(item.module, "teardown_function"):
                _call_optional(item.module.teardown_function, item.func)
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            err = err or e
        fin_err = self.finalize(lambda k: k == ("function", item.uid))
        err = err or fin_err
        sys.stdout, sys.stderr = saved
        if os.getcwd() != cwd:
            os.chdir(cwd)
        if isinstance(err, (Skipped, unittest.SkipTest)):
            rec.test(item.id, "skipped", item.src_file, item.lineno, str(err))
        elif isinstance(err, XFailed):
            rec.test(item.id, "xfailed", item.src_file, item.lineno)
        elif xfail is not None:
            raises = xfail.kwargs.get("raises")
            if err is not None and (raises is None or isinstance(err, raises)):
                rec.test(item.id, "xfailed", item.src_file, item.lineno)
            elif err is not None:
                self._failure(item.id, err, item.src_file, item.lineno, "pytest")
            elif xfail.kwargs.get("strict"):
                rec.test(item.id, "failed", item.src_file, item.lineno,
                         "[XPASS(strict)] " + str(xfail.kwargs.get("reason", "")), "pytest")
            else:
                rec.test(item.id, "xpassed", item.src_file, item.lineno)
        elif err is not None:
            self._failure(item.id, err, item.src_file, item.lineno, "pytest")
        else:
            rec.test(item.id, "passed", item.src_file, item.lineno, kind="pytest")

    def run_unittest(self, ucases, stem, relfile):
        loader = unittest.TestLoader()
        suite, tests = unittest.TestSuite(), []
        for cls in ucases:
            names = loader.getTestCaseNames(cls) or (["runTest"] if hasattr(cls, "runTest")
                                                     else [])
            for n in names:
                tid = "%s.%s" % (cls.__name__, n)
                if self.selected(tid, stem, relfile):
                    suite.addTest(cls(n))
                    tests.append((tid, cls, n))
        if not tests:
            return
        self.kinds.add("unittest")
        result = _UnittestResult()
        saved = (sys.stdout, sys.stderr)
        try:
            suite.run(result)
        finally:
            sys.stdout, sys.stderr = saved
        for tid, cls, n in tests:
            try:
                src_file = os.path.abspath(inspect.getsourcefile(cls))
                lineno = inspect.getsourcelines(inspect.unwrap(getattr(cls, n)))[1]
            except (TypeError, OSError):
                src_file, lineno = os.path.abspath(self.current_file), None
            outcome, err, prefix = result.status.get(tid, (None, None, ""))
            if outcome is None:
                # never ran: setUpClass / setUpModule failed
                fx = [e for desc, e in result.fixture_errors
                      if desc.startswith("setUpModule") or
                      re.search(r"\.%s\)$" % re.escape(cls.__name__), desc)]
                if fx:
                    outcome, err, prefix = "failed", fx[0], "error in class/module setup: "
                else:
                    outcome = "skipped"
            if outcome == "failed" and isinstance(err, BaseException):
                self._failure(tid, err, src_file, lineno, "unittest", prefix)
            elif outcome == "failed":
                self.rec.test(tid, "failed", src_file, lineno, prefix + (err or "failed"),
                              "unittest")
            else:
                self.rec.test(tid, outcome, src_file, lineno, kind="unittest")
        for desc, e in result.fixture_errors:
            if desc.startswith("tearDown"):
                self._failure(desc.split()[0] + " " + stem, e, os.path.abspath(
                    self.current_file), None, "unittest")

    def run_file(self, path):
        stem = os.path.splitext(os.path.basename(path))[0]
        relfile = _rel(path, self.root)
        self.current_file = path
        cwd = os.getcwd()
        try:
            layers = self.conftest_layers(path)
            mod = self.import_file(path)
        except Skipped:
            return
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            self._failure(stem, e, path, None, "collect", "error collecting %s: " % relfile)
            return
        try:
            layers = layers + [_fixtures_in(vars(mod))]
            items, ucases = self.collect(mod, path, stem, relfile, layers)
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            self._failure(stem, e, path, None, "collect", "error collecting %s: " % relfile)
            return
        if items:
            self.kinds.add("pytest")
            module_error = None
            try:
                if hasattr(mod, "setup_module"):
                    _call_optional(mod.setup_module, mod)
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                module_error = e
            current, class_error = None, None
            for item in items:
                if item.clsqual != current:
                    self._end_class(current, path)
                    current, class_error = item.clsqual, None
                    if item.cls is not None and hasattr(item.cls, "setup_class"):
                        try:
                            _call_optional(item.cls.setup_class, item.cls)
                        except BaseException as e:
                            if isinstance(e, KeyboardInterrupt):
                                raise
                            class_error = e
                self._current_cls = item.cls
                self.run_item(item, module_error or class_error)
            self._end_class(current, path)
            if hasattr(mod, "teardown_module"):
                try:
                    _call_optional(mod.teardown_module, mod)
                except BaseException as e:
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    self._failure("teardown_module " + stem, e, path, None, "pytest")
        self.run_unittest(ucases, stem, relfile)
        err = self.finalize(lambda k: k[0] in ("class", "module") and k[1] == path)
        if err is not None:
            self._failure("fixture teardown " + stem, err, path, None, "pytest")
        if os.getcwd() != cwd:
            os.chdir(cwd)

    def _end_class(self, qual, path):
        if qual is None:
            return
        cls = getattr(self, "_current_cls", None)
        if cls is not None and hasattr(cls, "teardown_class"):
            try:
                _call_optional(cls.teardown_class, cls)
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                self._failure("%s.teardown_class" % cls.__name__, e, path, None, "pytest")
        err = self.finalize(lambda k: k == ("class", path, qual))
        if err is not None:
            self._failure("fixture teardown " + qual, err, path, None, "pytest")


async def _await(awaitable):
    return await awaitable


def _call_optional(fn, arg):
    """Call an xunit-style setup/teardown hook with its argument if it takes one."""
    try:
        n = len([p for p in inspect.signature(fn).parameters.values()
                 if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY,
                                                        p.POSITIONAL_OR_KEYWORD)])
    except (TypeError, ValueError):
        n = 1
    return fn(arg) if n else fn()


class _UnittestResult(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self)
        self.buffer = True
        self.status, self.fixture_errors = {}, []

    def _set(self, test, outcome, err=None, prefix=""):
        tid = "%s.%s" % (type(test).__name__, getattr(test, "_testMethodName", "?"))
        if self.status.get(tid, ("",))[0] == "failed":
            return
        value = err[1] if isinstance(err, tuple) else err
        if isinstance(err, tuple) and value is not None and value.__traceback__ is None:
            value = value.with_traceback(err[2])
        self.status[tid] = (outcome, value, prefix)

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        self._set(test, "passed")

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        self._set(test, "failed", err)

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        if isinstance(test, unittest.TestCase):
            self._set(test, "failed", err)
        else:  # _ErrorHolder: setUpClass / setUpModule / tearDown* failed
            value = err[1] if err[1] is not None else err[0]()
            if value.__traceback__ is None:
                value = value.with_traceback(err[2])
            self.fixture_errors.append((str(test), value))

    def addSkip(self, test, reason):
        unittest.TestResult.addSkip(self, test, reason)
        self._set(test, "skipped")

    def addExpectedFailure(self, test, err):
        unittest.TestResult.addExpectedFailure(self, test, err)
        self._set(test, "xfailed")

    def addUnexpectedSuccess(self, test):
        unittest.TestResult.addUnexpectedSuccess(self, test)
        self._set(test, "failed", "unexpected success (test is marked expectedFailure)")

    def addSubTest(self, test, subtest, err):
        unittest.TestResult.addSubTest(self, test, subtest, err)
        if err is not None:
            desc = subtest._subDescription() if hasattr(subtest, "_subDescription") else ""
            outcome = "skipped" if issubclass(err[0], unittest.SkipTest) else "failed"
            self._set(test, outcome, err, (desc + " ") if desc != "(<subtest>)" else "")


def _source_kind(path):
    text = _read(path)
    if re.search(r"^\s*(import pytest|from pytest\b)", text, re.M) or \
            re.search(r"^(async )?def test", text, re.M):
        return "pytest"
    if "unittest" in text or "TestCase" in text:
        return "unittest"
    return None


def python_runner(spec):
    """Child-process entry point: run the Python tests and report each result."""
    root = os.getcwd()
    path, filt = spec.get("path") or ".", spec.get("filter") or ""
    target = os.path.abspath(os.path.join(root, path))
    rootdir, cfg = find_pytest_config(root, target)
    rec = _Recorder(os.environ.get("RUN_TESTS_RESULT"), root)
    sys.dont_write_bytecode = True
    here = os.path.dirname(SELF)
    sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != here]
    extra = [os.path.join(rootdir, p) for p in cfg.get("pythonpath", [])]
    for d in (rootdir, root):
        if os.path.isdir(os.path.join(d, "src")):
            extra.append(os.path.join(d, "src"))
    extra += [rootdir, root]
    for p in reversed(list(collections.OrderedDict.fromkeys(os.path.abspath(e) for e in extra))):
        if p not in sys.path:
            sys.path.insert(0, p)
    sys.modules["pytest"] = _build_pytest_module()
    sys.meta_path.insert(0, _RewriteFinder())
    builtins.__rt_cmp__, builtins.__rt_val__ = _rt_cmp, _rt_val
    os.chdir(rootdir)

    patterns = cfg.get("python_files") or ["test*.py", "*_test.py"]
    if os.path.isfile(target):
        tops = [target]
    elif os.path.normpath(path) == "." and cfg.get("testpaths"):
        tops = [os.path.join(rootdir, t) for t in cfg["testpaths"]
                if os.path.exists(os.path.join(rootdir, t))] or [target]
    else:
        tops = [target]
    files = []
    for top in tops:
        for f in _walk_files(top):
            if (os.path.isfile(target) or _is_py_test_file(os.path.basename(f), patterns)) and \
                    f.endswith(".py") and f not in files:
                files.append(f)

    sess = _Session(root, rootdir, cfg, filt, rec)
    for f in files:
        sess.run_file(f)
    err = sess.finalize(lambda k: True)
    if err is not None:
        sess._failure("session fixture teardown", err, rootdir, None, "pytest")
    if _TMP_FACTORY._base is not None:
        shutil.rmtree(str(_TMP_FACTORY._base), ignore_errors=True)

    source_kinds = {_source_kind(f) for f in files}
    if "pytest" in sess.kinds or "pytest" in source_kinds:
        framework = "pytest-style"
    elif "unittest" in sess.kinds or "unittest" in source_kinds:
        framework = "unittest"
    else:
        framework = "pytest-style"
    c = rec.counts
    total = sum(c.values())
    rec.write(t="done", framework=framework, files=len(files))
    rec.out.write("%s: %d passed, %d failed, %d skipped in %d files\n"
                  % (framework, c["passed"], c["failed"], c["skipped"], len(files)))
    return 1 if c["failed"] else (5 if total == 0 else 0)


def run_python(root, target, path, filt, timeout):
    spec = json.dumps({"path": path, "filter": filt})
    fd, result_file = tempfile.mkstemp(prefix="run_tests_", suffix=".jsonl", dir=_tmpdir())
    os.close(fd)
    command = "python3 %s --run-python %s" % (shlex.quote(SELF), shlex.quote(spec))
    env = dict(os.environ, RUN_TESTS_RESULT=result_file, PYTHONDONTWRITEBYTECODE="1")
    note, code, stderr = "", None, ""
    try:
        proc = subprocess.run([sys.executable, SELF, "--run-python", spec], cwd=root, env=env,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, timeout=timeout)
        code, stderr = proc.returncode, proc.stderr
    except subprocess.TimeoutExpired:
        note = "timed out after %ss" % timeout
    records = []
    try:
        with open(result_file, encoding="utf-8") as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except ValueError:
                    pass
    finally:
        os.unlink(result_file)
    passed, skipped, failing, started, done = 0, 0, [], None, None
    for r in records:
        if r.get("t") == "start":
            started = r.get("id")
        elif r.get("t") == "test":
            started = None
            if r["outcome"] == "passed":
                passed += 1
            elif r["outcome"] == "failed":
                failing.append({"id": r["id"], "file": r.get("file"), "line": r.get("line"),
                                "message": r.get("message") or "failed"})
            elif r["outcome"] == "skipped":
                skipped += 1
        elif r.get("t") == "done":
            done = r
    if started:
        failing.append({"id": started, "file": None, "line": None,
                        "message": "test did not finish: " + (note or "the process exited "
                                                              "(code %s)" % code)})
    if done is None and not note:
        note = "runner exited early (code %s): %s" % (code, _trim(stderr, 300))
    framework = done["framework"] if done else _guess_python_framework(target)
    return _result(framework, command, code, passed, failing, skipped, note)


def _guess_python_framework(target):
    kinds = {_source_kind(f) for f in _walk_files(target) if f.endswith(".py")}
    return "pytest-style" if "pytest" in kinds or "unittest" not in kinds else "unittest"


# ------------------------------------------------------------------------------- output

def _result(framework, command, exit_code, passed, failing, skipped=0, note=""):
    failed = len(failing)
    parts = ["%d passed" % passed, "%d failed" % failed]
    if skipped:
        parts.append("%d skipped" % skipped)
    summary = "%s: %s" % (framework, ", ".join(parts))
    if passed + failed + skipped == 0 and not note:
        summary += " (no tests found)"
    if failing:
        first = failing[0]
        summary += "; first: %s (%s:%s) %s" % (first["id"], first.get("file"), first.get("line"),
                                               _trim(first["message"].splitlines()[0], 120))
    if note:
        summary += "; " + note
    shown = failing[:MAX_FAILING]
    if len(failing) > MAX_FAILING:
        summary += "; only the first %d failures are listed" % MAX_FAILING
    return {"framework": framework, "command": command, "exit_code": exit_code,
            "passed": passed, "failed": failed, "failing": shown, "summary": summary}


def main(argv):
    if len(argv) > 1 and argv[1] == "--run-python":
        return python_runner(json.loads(argv[2]) if len(argv) > 2 else {})
    try:
        args = json.loads(argv[1]) if len(argv) > 1 and argv[1].strip() else {}
        if not isinstance(args, dict):
            raise ValueError("expected a JSON object")
    except ValueError as e:
        print(json.dumps(_result("other", "", 2, 0, [], note="bad JSON argument: %s" % e)))
        return 2
    path = str(args.get("path") or ".")
    filt = str(args.get("filter") or "")
    timeout = args.get("timeout") or DEFAULT_TIMEOUT
    root = os.getcwd()
    target = os.path.abspath(os.path.join(root, path))
    try:
        if not os.path.exists(target):
            result = _result("other", "", 2, 0, [], note="path %r does not exist" % path)
        else:
            kind = detect(root, target)
            if kind == "python":
                result = run_python(root, target, path, filt, timeout)
            elif kind == "node":
                result = run_node(root, target, path, filt, timeout)
            else:
                result = _result("other", "", None, 0, [],
                                 note="no unittest, pytest-style or node:test tests found under %r"
                                 % path)
    except Exception as e:  # always end with a JSON line
        result = _result("other", "", None, 0, [],
                         note="run_tests internal error: %s" % _exc_message(e))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
