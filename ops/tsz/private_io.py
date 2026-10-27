"""Owner-private JSON and locks shared by TSZ's local adapters (POSIX)."""
from contextlib import contextmanager
import errno
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile

MAX_SIZE = 1024 * 1024


def private_dir(path):
    path = Path(path).expanduser()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700
            or info.st_uid != os.getuid()):
        raise ValueError("state directory must be owner-owned mode 0700, not a link")
    return path


def _check(info):
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_uid != os.getuid() or info.st_nlink != 1):
        raise ValueError("JSON/lock must be an owner-owned mode 0600 regular file with one link")


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def _constant(value):
    raise ValueError("non-finite JSON number")


def read_json(path):
    # Check the opened descriptor, not a pathname that can be swapped after stat.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError("private JSON must not be a symbolic link") from exc
        raise
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        _check(before)
        if before.st_size > MAX_SIZE:
            raise ValueError("JSON exceeds size limit")
        raw = stream.read(MAX_SIZE + 1)
        after = os.fstat(stream.fileno())
        _check(after)
        if len(raw) > MAX_SIZE or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("JSON changed during read or exceeds size limit")
    try:
        data = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds limit") from exc
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def write_json(path, document):
    serialized = json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if len(serialized.encode("utf-8")) > MAX_SIZE:
        raise ValueError("JSON exceeds size limit; prior state preserved")
    path = Path(path)
    directory = private_dir(path.parent)
    try:
        _check(path.lstat())
    except FileNotFoundError:
        pass
    # Random names allow threads and processes to write different state files safely.
    fd, name = tempfile.mkstemp(prefix=".tsz-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(serialized)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
        dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def lock(directory):
    directory = private_dir(directory)
    fd = os.open(directory / ".fleet.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        _check(os.fstat(fd))
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)
