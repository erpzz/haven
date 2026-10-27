#!/usr/bin/env python3
"""OS enforcement for agent commands, without root.

macOS: Seatbelt (`sandbox-exec`), the mechanism Codex and Claude Code use.
Linux: Landlock (kernel 5.13+; TCP rules need ABI 4 / kernel 6.7+) plus
no_new_privs, applied by re-executing this file as a small wrapper.

Both give the same contract:
  * writes only inside the workspace, the git common dir it needs, and a
    private temporary directory;
  * no reads of credential stores or Haven's private state;
  * no network unless the scope grants it (Linux: TCP only; Landlock cannot
    filter UDP, and filters by port rather than address);
  * no privilege gain through setuid binaries (no_new_privs / exec denial).

`describe()` reports what the host actually supports. The executor refuses
autonomous mode where `available` is false.
"""
from __future__ import annotations

import ctypes
import json
import os
import pathlib
import platform
import shutil
import struct
import sys

HOME = pathlib.Path.home()
# Read-denied (and write-denied) relative to HOME.
SENSITIVE_HOME = (
    ".ssh", ".gnupg", ".aws", ".azure", ".kube", ".docker", ".netrc", ".npmrc", ".pypirc",
    ".git-credentials", ".config/gh", ".config/claude-haven-personal", ".claude", ".claude.json",
    ".codex", ".local/state", ".local/share/opencode", ".config/opencode", ".local/share/haven-engineer",
    "Library/Keychains", "Library/Cookies", "Library/Mail", "Library/Messages",
    "Library/Application Support/Google", "Library/Application Support/Firefox",
    "Library/Application Support/Claude", "Library/Application Support/com.apple.TCC",
    ".config/google-chrome", ".mozilla", ".password-store",
)
SETUID_DENY = ("/usr/bin/sudo", "/usr/bin/su", "/usr/bin/login", "/usr/bin/passwd", "/usr/sbin/visudo",
               "/usr/bin/pkexec", "/usr/bin/doas", "/usr/bin/security", "/usr/sbin/diskutil",
               "/usr/bin/osascript")


def describe():
    system = platform.system()
    if system == "Darwin":
        ok = shutil.which("sandbox-exec") is not None
        return {"backend": "seatbelt" if ok else "none", "available": ok,
                "network_filter": "all" if ok else "none", "read_deny": ok}
    if system == "Linux":
        abi = landlock_abi()
        return {"backend": f"landlock-abi{abi}" if abi > 0 else "none", "available": abi >= 1,
                "network_filter": "tcp-ports" if abi >= 4 else "none", "read_deny": abi >= 1}
    return {"backend": "none", "available": False, "network_filter": "none", "read_deny": False}


def wrap(argv, *, workspace, writable=(), tmpdir, network=False, read_only=False, local_ports=(), protect=()):
    """Return argv that runs `argv` under the host sandbox. Raises if none is available."""
    info = describe()
    if not info["available"]:
        raise RuntimeError("no OS sandbox backend on this host")
    roots = [] if read_only else [workspace, *writable]
    roots = [_real(p) for p in roots] + [_real(tmpdir)]
    if info["backend"] == "seatbelt":
        return ["sandbox-exec", "-p", seatbelt_profile(roots, network=network, protect=[_real(p) for p in protect]),
                *argv]
    spec = {"write": roots, "deny": [str(HOME / s) for s in SENSITIVE_HOME], "network": network,
            "local_ports": list(local_ports)}
    return [sys.executable, "-I", str(pathlib.Path(__file__).resolve()), "--landlock-exec",
            json.dumps(spec), "--", *argv]


def _real(path):
    return os.path.realpath(os.path.expanduser(str(path)))


def _sb_str(path):
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


def seatbelt_profile(write_roots, *, network, protect=()):
    deny_paths = []
    for rel in SENSITIVE_HOME:
        p = HOME / rel
        deny_paths.append(f"(subpath {_sb_str(_real(p))})")
    lines = [
        "(version 1)",
        "(allow default)",
        "(deny file-write*)",
        "(allow file-write* " + " ".join(f"(subpath {_sb_str(r)})" for r in write_roots)
        + ' (literal "/dev/null") (literal "/dev/zero") (literal "/dev/tty") (literal "/dev/dtracehelper")'
        + ' (regex #"^/dev/fd/") (regex #"^/dev/ttys[0-9]+$") (regex #"^/private/var/folders/[^/]+/[^/]+/C/"))',
        "(deny file-read* file-write* " + " ".join(deny_paths) + ")",
        "(deny process-exec " + " ".join(f"(literal {_sb_str(p)})" for p in SETUID_DENY) + ")",
    ]
    if protect:  # git hooks/config inside a writable root: a later deny overrides the allow
        lines.append("(deny file-write* " + " ".join(f"(subpath {_sb_str(p)})" for p in protect) + ")")
    if not network:
        lines += [
            "(deny network*)",
            '(allow network-bind network-inbound (local ip "localhost:*"))',
            '(allow network-outbound (remote ip "localhost:*"))',
            "(allow network-outbound (remote unix-socket "
            + " ".join(f"(subpath {_sb_str(r)})" for r in write_roots) + "))",
            "(allow network-bind (local unix-socket "
            + " ".join(f"(subpath {_sb_str(r)})" for r in write_roots) + "))",
        ]
    return "\n".join(lines)


# ---- Linux Landlock -------------------------------------------------------

_SYS = {"x86_64": (444, 445, 446), "aarch64": (444, 445, 446)}
_FS_EXECUTE, _FS_WRITE_FILE, _FS_READ_FILE, _FS_READ_DIR = 1, 2, 4, 8
_FS_WRITE_MASK_V1 = 2 | 16 | 32 | 64 | 128 | 256 | 512 | 1024 | 2048 | 4096  # write + remove + make_*
_FS_REFER, _FS_TRUNCATE = 1 << 13, 1 << 14
_NET_BIND, _NET_CONNECT = 1, 2
_PR_SET_NO_NEW_PRIVS = 38
_O_PATH, _O_CLOEXEC = 0o10000000, 0o2000000


def landlock_abi():
    if platform.system() != "Linux" or platform.machine() not in _SYS:
        return 0
    libc = ctypes.CDLL(None, use_errno=True)
    abi = libc.syscall(_SYS[platform.machine()][0], None, ctypes.c_size_t(0), ctypes.c_uint32(1))
    return abi if abi > 0 else 0


def _landlock_exec(spec, argv):
    create, add_rule, restrict = _SYS[platform.machine()]
    libc = ctypes.CDLL(None, use_errno=True)
    abi = landlock_abi()
    if abi < 1:
        raise SystemExit("landlock unavailable")
    write_mask = _FS_WRITE_MASK_V1 | (_FS_REFER if abi >= 2 else 0) | (_FS_TRUNCATE if abi >= 3 else 0)
    read_mask = _FS_EXECUTE | _FS_READ_FILE | _FS_READ_DIR
    handled_fs = write_mask | read_mask
    handled_net = (_NET_BIND | _NET_CONNECT) if abi >= 4 and not spec["network"] else 0
    attr = struct.pack("QQ", handled_fs, handled_net) if abi >= 4 else struct.pack("Q", handled_fs)
    buf = ctypes.create_string_buffer(attr, len(attr))
    fd = libc.syscall(create, buf, ctypes.c_size_t(len(attr)), ctypes.c_uint32(0))
    if fd < 0:
        raise SystemExit("landlock_create_ruleset failed: " + os.strerror(ctypes.get_errno()))

    def allow(path, access):
        try:
            pfd = os.open(path, _O_PATH | _O_CLOEXEC)
        except OSError:
            return
        try:
            is_dir = os.path.isdir(path)
            mask = access if is_dir else access & (_FS_EXECUTE | _FS_READ_FILE | _FS_WRITE_FILE | _FS_TRUNCATE)
            rule = struct.pack("=Qi", mask, pfd)  # landlock_path_beneath_attr is packed
            rbuf = ctypes.create_string_buffer(rule, len(rule))
            if libc.syscall(add_rule, fd, 1, rbuf, ctypes.c_uint32(0)) != 0:
                raise SystemExit(f"landlock_add_rule {path}: " + os.strerror(ctypes.get_errno()))
        finally:
            os.close(pfd)

    deny = [os.path.realpath(d) for d in spec["deny"]]
    for path in _readable_roots(deny):
        allow(path, read_mask)
    for root in spec["write"]:
        allow(root, read_mask | write_mask)
    for dev in ("/dev/null", "/dev/zero", "/dev/tty", "/dev/pts"):
        allow(dev, read_mask | _FS_WRITE_FILE | (_FS_TRUNCATE if abi >= 3 else 0))
    if handled_net:
        for port in spec.get("local_ports") or []:
            rule = struct.pack("=QQ", _NET_BIND | _NET_CONNECT, int(port))
            rbuf = ctypes.create_string_buffer(rule, len(rule))
            libc.syscall(add_rule, fd, 2, rbuf, ctypes.c_uint32(0))
    if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        raise SystemExit("no_new_privs failed")
    if libc.syscall(restrict, fd, ctypes.c_uint32(0)) != 0:
        raise SystemExit("landlock_restrict_self failed: " + os.strerror(ctypes.get_errno()))
    os.close(fd)
    os.execvp(argv[0], argv)


_STANDARD_TOP = ("bin", "boot", "dev", "etc", "lib", "lib32", "lib64", "libx32", "media", "mnt", "nix", "opt",
                 "proc", "run", "sbin", "snap", "srv", "sys", "tmp", "usr", "var")


def _readable_roots(deny):
    """Every top-level path except HOME, plus HOME's children minus the denied ones (two levels)."""
    home = os.path.realpath(str(HOME))
    roots = []
    try:
        top = os.listdir("/")
    except PermissionError:  # nested inside another Landlock domain: "/" itself is not listable
        top = [d for d in _STANDARD_TOP if os.path.lexists(os.path.join("/", d))]
    for entry in top:
        p = os.path.join("/", entry)
        if p == "/home" or home.startswith(p + "/"):
            continue
        roots.append(p)
    parent = os.path.dirname(home)
    if parent != "/" and parent not in roots:
        pass  # other users' homes stay unreadable
    roots.extend(_expand(home, deny, depth=3))
    return roots


def _expand(path, deny, depth):
    if path in deny:
        return []
    if not any(d.startswith(path + "/") for d in deny) or depth == 0 or not os.path.isdir(path):
        return [path]
    out = []
    try:
        names = os.listdir(path)
    except OSError:
        return []
    for name in names:
        out.extend(_expand(os.path.join(path, name), deny, depth - 1))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[1] == "--landlock-exec" and sys.argv[3] == "--":
        _landlock_exec(json.loads(sys.argv[2]), sys.argv[4:])
    print(json.dumps(describe()))
