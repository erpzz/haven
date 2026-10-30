"""Validate untrusted secpatch repo-evaluation inputs before subprocesses or writes.

This is input confinement, NOT process isolation. Third-party install/test code must
still run in an independently verified disposable VM or equivalent sandbox.
"""
from __future__ import annotations

import pathlib
import re

_REPO = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z')
_SHA = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
_KEY = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')


def python_path(value: object, label: str) -> pathlib.PurePosixPath:
    """Reject traversal, absolute paths, option-like names and ambiguous spellings."""
    if (not isinstance(value, str) or not 1 <= len(value) <= 512 or
            '\\' in value or '\x00' in value or ':' in value or
            any(part in ('', '.', '..') or part.startswith('-') for part in value.split('/'))):
        raise ValueError(f'Invalid {label} path.')
    path = pathlib.PurePosixPath(value)
    if path.is_absolute() or path.suffix != '.py':
        raise ValueError(f'Invalid {label} path.')
    return path


def validate_candidate(cand: object) -> None:
    """Fail before clone, checkout, pip or pytest if a harvested row is unsafe."""
    if not isinstance(cand, dict):
        raise ValueError('Candidate must be an object.')
    if not isinstance(cand.get('key'), str) or not _KEY.fullmatch(cand['key']):
        raise ValueError('Invalid candidate advisory ID.')
    repo = cand.get('repo')
    if (not isinstance(repo, str) or not _REPO.fullmatch(repo) or
            any(part in ('.', '..') for part in repo.split('/'))):
        raise ValueError('Invalid GitHub owner/repository.')
    for field in ('commit', 'parent'):
        value = cand.get(field)
        if not isinstance(value, str) or not _SHA.fullmatch(value):
            raise ValueError(f'Invalid immutable {field} SHA.')
    python_path(cand.get('path'), 'source')
    name = cand.get('function')
    if (not isinstance(name, str) or not 1 <= len(name) <= 256 or
            not all(part.isidentifier() for part in name.split('.'))):
        raise ValueError('Invalid qualified function name.')
    tests = cand.get('tests')
    if not isinstance(tests, list) or not 1 <= len(tests) <= 64:
        raise ValueError('Expected 1–64 recorded tests.')
    for test in tests:
        if not isinstance(test, dict):
            raise ValueError('Invalid recorded test.')
        python_path(test.get('path'), 'test')
        test_name = test.get('name')
        if (not isinstance(test_name, str) or not 1 <= len(test_name) <= 256 or
                not all(part.isidentifier() for part in test_name.split('.'))):
            raise ValueError('Invalid pytest node name.')


def safe_source_path(work: pathlib.Path, relative: str) -> pathlib.Path:
    """Refuse source symlinks (including parent components) before read/write.

    Recheck after every Git checkout: a path safe at the fix commit may become
    a symlink in the vulnerable parent. This does not protect against an
    actively malicious concurrent process; the disposable VM is still required.
    """
    path = python_path(relative, 'source')
    base = work.resolve(strict=True)
    current = base
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Source path contains a symlink.')
    if not current.is_file() or not current.resolve(strict=True).is_relative_to(base):
        raise ValueError('Source path is not a regular file inside the checkout.')
    return current
