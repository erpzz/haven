"""Autonomy modes and the executor's permission decision.

The decision is made here, in the executor process, from the tool name and its
arguments. A model can ask for anything; it cannot change the mode, the scope
or this table. Three modes:

  observe     read-only discovery. Writes are refused; shell commands run only
              when they are recognised as read-only, inside a read-only sandbox.
  engineer    edits and development commands inside the workspace. Commands
              classified as higher impact (push, history rewrite, installs that
              need the network, recursive deletes) wait for owner approval.
  autonomous  everything the scope allows, without approval, inside the OS
              sandbox. Requires a working sandbox backend.

Some classes are never granted by any mode (ADMIN: privilege escalation, disk
and boot tools, credential stores, host service managers). They need separate
authority that this executor does not hold.

Command classification is a guard rail for approvals, not the security
boundary: a shell is Turing-complete. The boundary for filesystem writes,
network and setuid is the OS sandbox in sandbox.py.
"""
from __future__ import annotations

import dataclasses
import re
import shlex

MODES = ("observe", "engineer", "autonomous")
ALLOW, ASK, DENY = "allow", "ask", "deny"

# Tool -> capability class. Unknown tools are denied.
TOOL_CLASS = {
    "list_dir": "read", "read_file": "read", "search": "read", "project_info": "read",
    "git_status": "read", "git_diff": "read", "git_log": "read",
    "process_status": "read",
    "write_file": "write", "edit_file": "write", "apply_patch": "write",
    "run_command": "exec", "start_process": "exec", "stop_process": "exec",
    "git_commit": "git_write", "git_branch": "git_write",
    "deploy": "deploy",
    "delegate": "delegate",
}

PROTECTED_BRANCHES = ("main", "master", "production", "release")

# First words (or word pairs) of commands that only inspect.
_READ_ONLY = {
    "ls", "cat", "head", "tail", "wc", "pwd", "echo", "printf", "true", "false", "stat", "file",
    "grep", "egrep", "rg", "ag", "tree", "du", "df", "which", "type", "env", "printenv", "uname",
    "date", "whoami", "id", "basename", "dirname", "realpath", "readlink", "sort", "uniq", "cut",
    "tr", "diff", "cmp", "jq", "test", "[", "nproc", "sha256sum", "shasum", "md5sum", "less", "more",
    "column", "nl", "od", "xxd", "hexdump", "strings", "uptime", "free", "ps", "lsof", "nvidia-smi",
    "sw_vers", "sysctl", "vm_stat", "hostname",
}
_READ_ONLY_GIT = {"status", "diff", "log", "show", "branch", "rev-parse", "ls-files", "blame",
                  "remote", "describe", "shortlog", "grep", "worktree", "config", "tag", "cat-file"}
# git subcommands whose read-only form becomes a write with extra args.
_GIT_WRITE_FLAGS = {"branch": {"-d", "-D", "-m", "-M", "--delete", "--move", "-c", "-C", "-f", "--force"},
                    "worktree": {"add", "remove", "prune", "move", "lock", "unlock", "repair"},
                    "config": {"--add", "--unset", "--unset-all", "--replace-all", "--global", "--system",
                               "--edit", "-e"},
                    "tag": {"-a", "-d", "-s", "-f", "--delete"},
                    "remote": {"add", "remove", "rm", "rename", "set-url", "set-head", "prune"}}

# Never granted by a mode. Matched on any command segment's first word.
_ADMIN_WORDS = set("""
    sudo su doas pkexec login passwd chsh visudo dd mkfs fdisk gdisk
    sfdisk parted wipefs diskutil hdiutil asr bless nvram efibootmgr grub-install update-grub mount
    umount losetup cryptsetup csrutil spctl launchctl systemctl service shutdown reboot halt poweroff
    init kextload insmod rmmod modprobe ufw iptables nft pfctl security networksetup scutil
    dscl useradd userdel usermod groupadd chown fdesetup tmutil softwareupdate apt apt-get dpkg
    snap port mullvad tailscale
""".split())
# systemctl --user status style inspection is still useful; allow read-only verbs explicitly.
_ADMIN_READ_FORMS = {("systemctl", "status"), ("systemctl", "is-active"), ("systemctl", "list-units"),
                     ("launchctl", "list"), ("launchctl", "print"), ("tailscale", "status"),
                     ("mullvad", "status"), ("dpkg", "-l"), ("apt", "list"), ("snap", "list")}
_CREDENTIAL_PATHS = re.compile(r"(~|\$HOME|/Users/[^/\s]+|/home/[^/\s]+)?/?\.(ssh|gnupg|aws|netrc|docker/config)"
                               r"|Library/Keychains|\.config/(gh|claude[^/\s]*)|\.codex/auth|\.claude/\.credentials"
                               r"|id_(rsa|ed25519|ecdsa)")

# Higher impact: approval in engineer mode, allowed in autonomous mode (inside the sandbox).
_NETWORK_INSTALL = re.compile(r"^(pip3?|uv|npm|pnpm|yarn|bun|cargo|go|gem|brew|conda|poetry)\b.*\b(install|add|get|update|upgrade|i)\b")
_NETWORK_WORDS = {"curl", "wget", "ssh", "scp", "rsync", "nc", "ncat", "telnet", "ftp", "sftp", "gh"}
_DESTRUCTIVE = [
    (re.compile(r"\brm\b.*\s-[a-zA-Z]*r[a-zA-Z]*f|\brm\b.*\s-[a-zA-Z]*f[a-zA-Z]*r|\brm\s+-r"), "recursive delete"),
    (re.compile(r"\bgit\s+(reset\s+--hard|clean\s+-[a-zA-Z]*f|checkout\s+--\s|restore\s|stash\s+(drop|clear))"),
     "discards uncommitted work"),
    (re.compile(r"\bgit\s+push\b"), "publishes to a remote"),
    (re.compile(r"\bgit\s+(rebase|filter-branch|filter-repo|commit\s+--amend|update-ref|reflog\s+expire|gc\s+--prune)"),
     "rewrites history"),
    (re.compile(r"\bgit\s+(merge|cherry-pick|revert)\b"), "integrates other history"),
    (re.compile(r"\bchmod\s+-R|\bfind\b.*\s-(delete|exec)\b"), "bulk permission or delete"),
]
_FORCE_PUSH = re.compile(r"\bgit\s+push\b.*(\s--force\b|\s-f\b|\s\+\S+|--force-with-lease)")


@dataclasses.dataclass(frozen=True)
class Scope:
    """What the owner granted for one workspace. Created by the owner, never by a model."""
    mode: str = "engineer"
    network: bool = False             # sandbox network for commands (autonomous installs, fetch)
    push_remotes: tuple = ()          # remotes an autonomous agent may push non-protected branches to
    deploy_targets: tuple = ()        # deployment targets this scope may deploy to without approval
    protected_branches: tuple = PROTECTED_BRANCHES
    max_command_seconds: int = 600

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"unknown mode {self.mode!r}")


@dataclasses.dataclass(frozen=True)
class Decision:
    action: str          # allow | ask | deny
    reason: str
    klass: str           # capability class
    network: bool = False

    def as_dict(self):
        return dataclasses.asdict(self)


_OPERATORS = {";", "&&", "||", "|", "&", "|&", ";;", "(", ")", "\n"}


def segments(command: str):
    """Split a shell command into simple-command word lists, respecting quotes. None if unparseable."""
    lex = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|()")
    lex.whitespace_split = True
    lex.commenters = "#"
    try:
        tokens = list(lex)
    except ValueError:
        return None
    words, cur = [], []
    for tok in tokens:
        if tok in _OPERATORS or (tok and set(tok) <= set(";&|()")):
            if cur:
                words.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        words.append(cur)
    out = []
    for parts in words:
        while parts and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", parts[0]):  # VAR=value prefix
            parts = parts[1:]
        if parts and parts[0] in ("time", "nice", "nohup", "command", "builtin", "exec", "timeout", "env"):
            parts = parts[1:]
            while parts and (parts[0].startswith("-") or re.match(r"^\d+[smh]?$", parts[0]) or "=" in parts[0]):
                parts = parts[1:]
        if parts:
            out.append(parts)
    return out


def _base(word: str) -> str:
    return word.rsplit("/", 1)[-1]


def classify_command(command: str, scope: Scope):
    """Return (klass, reasons). klass: read_only | dev | high_impact | admin."""
    reasons = []
    if _CREDENTIAL_PATHS.search(command):
        return "admin", ["touches a credential store"]
    if "$(" in command or "`" in command or "<(" in command:
        reasons.append("command substitution")
    segs = segments(command)
    if segs is None:
        return "high_impact", ["unparseable shell syntax"]
    if not segs:
        return "read_only", []
    klass = "read_only"
    for words in segs:
        first = _base(words[0])
        second = words[1] if len(words) > 1 else ""
        if first in _ADMIN_WORDS and (first, second) not in _ADMIN_READ_FORMS:
            if first == "systemctl" and second == "--user" and len(words) > 2 \
                    and words[2] in ("status", "is-active", "list-units", "show"):
                continue
            return "admin", [f"{first} needs separate host authority"]
        if first in _ADMIN_WORDS:
            continue
        if first == "git":
            sub = next((w for w in words[1:] if not w.startswith("-")), "")
            if sub in _READ_ONLY_GIT and not (set(words[2:]) & _GIT_WRITE_FLAGS.get(sub, set())):
                continue
            klass = max(klass, "dev", key=_RANK.get)
            if sub == "push":
                branch_words = [w for w in words[2:] if not w.startswith("-")]
                target = branch_words[-1].split(":")[-1].lstrip("+") if len(branch_words) >= 2 else ""
                if _FORCE_PUSH.search(" ".join(words)) and (not target or target in scope.protected_branches):
                    return "admin", ["force push to a protected or unnamed branch"]
                if target in scope.protected_branches:
                    return "admin", [f"push to protected branch {target}"]
            continue
        if first in _READ_ONLY:
            continue
        if first in _NETWORK_WORDS:
            klass = "high_impact"
            reasons.append(f"{first} uses the network")
            continue
        klass = max(klass, "dev", key=_RANK.get)
    joined = " ".join(" ".join(w) for w in segs)
    if _NETWORK_INSTALL.search(joined) or any(_NETWORK_INSTALL.search(" ".join(w)) for w in segs):
        klass = "high_impact"
        reasons.append("package install needs the network")
    for pattern, why in _DESTRUCTIVE:
        if pattern.search(command):
            klass = "high_impact"
            reasons.append(why)
    if re.search(r"(^|[^<>&0-9])>>?\s*[^\s&|]", command) and klass == "read_only":
        klass = "dev"
        reasons.append("redirects output to a file")
    return klass, reasons


_RANK = {"read_only": 0, "dev": 1, "high_impact": 2, "admin": 3}


def decide(tool: str, args: dict, scope: Scope, sandboxed: bool) -> Decision:
    klass = TOOL_CLASS.get(tool) or ("skill" if tool.startswith("skill_") else None)
    if klass is None:
        return Decision(DENY, f"unknown tool {tool!r}", "unknown")
    mode = scope.mode
    if klass == "read":
        return Decision(ALLOW, "read-only inspection", klass)
    if klass == "write":
        if mode == "observe":
            return Decision(DENY, "observe mode is read-only", klass)
        return Decision(ALLOW, f"{mode} mode may edit inside the workspace", klass)
    if klass == "git_write":
        if mode == "observe":
            return Decision(DENY, "observe mode is read-only", klass)
        branch = str(args.get("branch") or args.get("_current_branch") or "")
        if branch in scope.protected_branches:
            return Decision(ASK if mode == "engineer" else DENY,
                            f"commit on protected branch {branch}", klass)
        return Decision(ALLOW, "commit on a working branch", klass)
    if klass == "skill":
        if scope.mode == "observe":
            return Decision(DENY, "observe mode does not run code, including inherited skills", klass)
        if not sandboxed:
            return Decision(ASK, "inherited skill; no OS sandbox on this host", klass)
        return Decision(ALLOW, "admitted skill (verified hash) in the sandbox", klass)
    if klass == "delegate":
        if mode == "observe":
            return Decision(DENY, "observe mode cannot start child agents", klass)
        return Decision(ALLOW, "child agent with no more authority than this one", klass)
    if klass == "deploy":
        target = str(args.get("target") or "")
        if target in scope.deploy_targets and mode == "autonomous":
            return Decision(ALLOW, f"deploy target {target} is granted in this scope", klass)
        if mode == "observe":
            return Decision(DENY, "observe mode cannot deploy", klass)
        return Decision(ASK, f"deploy to {target or 'an unnamed target'} needs owner approval", klass)
    # exec
    if tool == "stop_process":
        return Decision(ALLOW if mode != "observe" else DENY, "stop a process this executor started", klass)
    command = str(args.get("command") or "")
    cmd_class, reasons = classify_command(command, scope)
    why = "; ".join(reasons) or cmd_class.replace("_", " ")
    if cmd_class == "admin":
        return Decision(DENY, f"{why} (not grantable by an autonomy mode)", "admin")
    if not sandboxed:
        # Without OS enforcement, every non-inspection command needs a human.
        if cmd_class == "read_only" and mode != "observe":
            return Decision(ALLOW, "read-only command (no sandbox available)", klass)
        return Decision(ASK if mode != "observe" else DENY, f"{why}; no OS sandbox on this host", klass)
    if mode == "observe":
        if cmd_class == "read_only":
            return Decision(ALLOW, "read-only command in a read-only sandbox", klass)
        return Decision(DENY, f"observe mode runs only read-only commands ({why})", klass)
    if mode == "engineer":
        if cmd_class == "high_impact":
            network_only = all(_needs_network([r]) and "remote" not in r for r in reasons)
            if network_only and scope.network:
                return Decision(ALLOW, f"{why}; network granted for this scope", klass, network=True)
            return Decision(ASK, why, klass, network=_needs_network(reasons))
        return Decision(ALLOW, f"development command in the sandbox ({why})", klass, network=scope.network)
    # autonomous
    if "publishes to a remote" in reasons:
        remote = _push_remote(command)
        if remote not in scope.push_remotes:
            return Decision(ASK, f"push to remote {remote or '?'} is outside this scope", klass, network=True)
        return Decision(ALLOW, f"push to granted remote {remote}", klass, network=True)
    if cmd_class == "high_impact" and _needs_network(reasons) and not scope.network:
        return Decision(ASK, f"{why}; this scope has no network grant", klass, network=True)
    return Decision(ALLOW, f"autonomous scope ({why})", klass, network=scope.network)


def _needs_network(reasons):
    return any("network" in r or "remote" in r for r in reasons)


def _push_remote(command):
    for words in segments(command) or []:
        if _base(words[0]) == "git" and "push" in words:
            rest = [w for w in words[words.index("push") + 1:] if not w.startswith("-")]
            return rest[0] if rest else "origin"
    return ""
