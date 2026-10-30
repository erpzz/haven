"""haven-sentinel: a read-only security posture audit of a Haven host.

Every finding is a measurement of this host with its evidence attached; nothing is
inferred from threat feeds, and nothing is changed. Checks:

  exposure     listening sockets that are not loopback and not on the allowlist
  ssh          sshd settings that matter on a LAN-reachable port (unreadable = UNKNOWN, never PASS)
  secrets      key/token files readable by group or others
  git-secrets  credential-shaped strings in tracked files of Haven checkouts (values redacted)
  deps         installed Python packages in Haven venvs with a matching OSV advisory (offline export)
  drift        persistence surfaces (units, timers, cron, rc files, authorized_keys, autostart)
               compared with an owner-accepted baseline

Usage:
  python3 sentinel.py --config sentinel.json --out ~/.local/state/haven-sentinel
  python3 sentinel.py --config sentinel.json --out ... --accept-baseline   # after reviewing a report

Exit status: 0 no failing finding of severity high; 1 at least one; 2 the audit itself failed.
Reports hold host details; keep them in a private state directory, never in Git.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import time
import zipfile

SCHEMA = 'haven-sentinel-report-v1'
LOOPBACK = re.compile(r'^(127\.\d+\.\d+\.\d+|\[::1\]|::1|localhost)(%\w+)?:')
SECRET_NAME = re.compile(r'(^|[-_.])(key|token|secret|password|passwd|credential|cookie)s?([-_.]|$)|\.pem$|^id_(rsa|ed25519|ecdsa)$', re.I)
SECRET_PATTERNS = {
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----'),
    'huggingface-token': re.compile(r'\bhf_[A-Za-z0-9]{30,}\b'),
    'github-token': re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b'),
    'openai-style-key': re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b'),
    'anthropic-key': re.compile(r'\bsk-ant-[A-Za-z0-9_-]{32,}\b'),
    'aws-access-key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    'slack-token': re.compile(r'\bxox[abposr]-[A-Za-z0-9-]{10,}\b'),
}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'site-packages', 'dist-packages', '.venv', 'venv'}
NOT_CREDENTIAL_FILES = ('.py', '.md', '.mdx', '.rst', '.txt', '.html', '.js', '.ts', '.gif', '.png', '.jpg', '.svg',
                        '.pub', '.lock', '.bak')


def finding(check, severity, status, title, evidence=None, remediation=None):
    return {'check': check, 'severity': severity, 'status': status, 'title': title,
            'evidence': evidence or {}, 'remediation': remediation}


def run(argv, timeout=60) -> tuple[int, str, str]:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, '', str(exc)


# ---------- exposure ----------

def parse_ss(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        proto, local = parts[0], parts[4]
        proc = re.search(r'\(\("([^"]+)",pid=(\d+)', line)
        out.append({'proto': proto, 'local': local, 'process': proc.group(1) if proc else None,
                    'pid': int(proc.group(2)) if proc else None})
    return out


def check_exposure(sockets: list[dict], allow: list[str]) -> list[dict]:
    exposed = []
    for s in sockets:
        if LOOPBACK.match(s['local']) or s['local'].startswith('127.0.0.53') or s['local'].startswith('127.0.0.54'):
            continue
        label = f"{s['proto']} {s['local']}"
        if any(label == pat or fnmatch.fnmatch(label, pat.replace('[', '[[]')) for pat in allow):
            continue
        exposed.append(s)
    if not sockets:
        return [finding('exposure', 'medium', 'unknown', 'No socket list could be read', remediation='Check that `ss` is installed.')]
    if exposed:
        return [finding('exposure', 'high', 'fail', f'{len(exposed)} listening socket(s) reachable beyond loopback and not allowlisted',
                        {'sockets': exposed},
                        'Bind the service to 127.0.0.1, or add it to the allowlist with the reason in sentinel.json.')]
    return [finding('exposure', 'info', 'pass', f'All {len(sockets)} listening sockets are loopback or allowlisted',
                    {'allowlist': allow})]


# ---------- ssh ----------

def sshd_settings(paths: list[pathlib.Path]) -> tuple[dict, list[str]]:
    """First value wins, as in sshd_config (Include files in sshd_config.d are read first on Debian/Ubuntu)."""
    values, unreadable = {}, []
    for p in paths:
        try:
            text = p.read_text()
        except PermissionError:
            unreadable.append(str(p))
            continue
        except OSError:
            continue
        for line in text.splitlines():
            m = re.match(r'\s*(\w+)\s+(\S+)', line)
            if m and not line.lstrip().startswith('#'):
                values.setdefault(m.group(1).lower(), m.group(2).lower())
    return values, unreadable


def check_ssh(etc: pathlib.Path, sshd_listening: bool) -> list[dict]:
    if not sshd_listening:
        return [finding('ssh', 'info', 'pass', 'sshd is not listening')]
    paths = sorted((etc / 'ssh' / 'sshd_config.d').glob('*.conf')) + [etc / 'ssh' / 'sshd_config']
    values, unreadable = sshd_settings(paths)
    out = []
    pw = values.get('passwordauthentication')
    if pw == 'yes':
        out.append(finding('ssh', 'high', 'fail', 'sshd accepts passwords on a LAN-reachable port',
                           {'passwordauthentication': pw}, 'Set PasswordAuthentication no (keys only) and reload sshd.'))
    elif pw is None and unreadable:
        out.append(finding('ssh', 'medium', 'unknown',
                           'PasswordAuthentication could not be determined: a config file is unreadable without root',
                           {'unreadable': unreadable},
                           'Run `sudo sshd -T | grep -Ei "passwordauthentication|permitrootlogin"` and record the result.'))
    elif pw is None:
        out.append(finding('ssh', 'medium', 'fail', 'PasswordAuthentication is not set (OpenSSH default is yes)',
                           remediation='Set PasswordAuthentication no.'))
    else:
        out.append(finding('ssh', 'info', 'pass', 'Password authentication is off', {'passwordauthentication': pw}))
    root = values.get('permitrootlogin')
    if root in ('yes',):
        out.append(finding('ssh', 'high', 'fail', 'sshd permits root login', {'permitrootlogin': root},
                           'Set PermitRootLogin no.'))
    return out


# ---------- secrets on disk ----------

def walk(root: pathlib.Path, max_depth: int):
    root_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(pathlib.Path(dirpath).parts) - root_depth
        if '.git' in dirnames and pathlib.Path(dirpath) != root:
            dirnames[:] = []  # a source checkout: its files are code, and git-secrets covers what it tracks
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and depth < max_depth]
        for f in filenames:
            yield pathlib.Path(dirpath) / f


def check_secret_files(roots: list[pathlib.Path], max_depth: int = 6) -> list[dict]:
    loose, seen = [], 0
    for root in roots:
        if not root.exists():
            continue
        for p in walk(root, max_depth):
            if not SECRET_NAME.search(p.name) or p.suffix.lower() in NOT_CREDENTIAL_FILES:
                continue
            try:
                st = p.lstat()
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            seen += 1
            if st.st_mode & 0o077:
                loose.append({'path': str(p), 'mode': oct(st.st_mode & 0o777)})
    if loose:
        return [finding('secrets', 'high', 'fail', f'{len(loose)} credential-named file(s) readable by group or others',
                        {'files': loose[:50], 'more': max(0, len(loose) - 50)}, 'chmod 600 each file (and 700 its directory).')]
    return [finding('secrets', 'info', 'pass', f'{seen} credential-named file(s) checked; all are owner-only')]


def redact(s: str) -> str:
    return s[:4] + '…' + f'({len(s)} chars)'


def check_git_secrets(repos: list[pathlib.Path], max_bytes: int = 1_000_000) -> list[dict]:
    hits, scanned, missing = [], 0, []
    for repo in repos:
        code, out, _ = run(['git', '-C', str(repo), 'ls-files', '-z'])
        if code != 0:
            missing.append(str(repo))
            continue
        for rel in filter(None, out.split('\0')):
            p = repo / rel
            try:
                if p.is_symlink() or p.stat().st_size > max_bytes:
                    continue
                text = p.read_text(errors='ignore')
            except OSError:
                continue
            scanned += 1
            for kind, rx in SECRET_PATTERNS.items():
                for m in rx.finditer(text):
                    line = text.count('\n', 0, m.start()) + 1
                    hits.append({'repo': str(repo), 'file': rel, 'line': line, 'kind': kind, 'match': redact(m.group(0))})
    out = []
    if hits:
        out.append(finding('git-secrets', 'high', 'fail', f'{len(hits)} credential-shaped string(s) in tracked files',
                           {'hits': hits[:50]},
                           'Revoke the credential at its issuer first, then remove it from the file and history.'))
    else:
        out.append(finding('git-secrets', 'info', 'pass', f'No credential-shaped strings in {scanned} tracked files',
                           {'repos': [str(r) for r in repos if str(r) not in missing]}))
    if missing:
        out.append(finding('git-secrets', 'low', 'unknown', 'Configured path(s) are not readable git checkouts', {'paths': missing}))
    return out


# ---------- dependencies (offline OSV) ----------

def canon(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def installed(venv: pathlib.Path) -> dict[str, str]:
    """Read dist-info METADATA; never imports or runs code from the venv."""
    pkgs = {}
    for meta in venv.glob('lib/python*/site-packages/*.dist-info/METADATA'):
        name = version = None
        for line in meta.read_text(errors='ignore').splitlines():
            if line.startswith('Name: '):
                name = line[6:].strip()
            elif line.startswith('Version: '):
                version = line[9:].strip()
            if name and version:
                break
            if not line:
                break
        if name and version:
            pkgs[canon(name)] = version
    return pkgs


def affected(version: str, entry: dict, V) -> bool:
    if version in (entry.get('versions') or []):
        return True
    try:
        v = V(version)
    except Exception:
        return False
    for rng in entry.get('ranges') or []:
        if rng.get('type') != 'ECOSYSTEM':
            continue
        events = []  # OSV: evaluate events in version order, whatever order they are listed in
        for ev in rng.get('events') or []:
            for kind in ('introduced', 'fixed', 'last_affected'):
                if kind in ev:
                    try:
                        events.append((V('0') if ev[kind] == '0' else V(ev[kind]), kind))
                    except Exception:
                        pass
        inside = False
        for ver, kind in sorted(events, key=lambda e: e[0]):
            if kind == 'introduced' and ver <= v:
                inside = True
            elif kind == 'fixed' and ver <= v:
                inside = False
            elif kind == 'last_affected' and ver < v:
                inside = False
        if inside:
            return True
    return False


def osv_index(archive: pathlib.Path) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if not name.endswith('.json'):
                continue
            adv = json.loads(z.read(name))
            if adv.get('withdrawn'):
                continue
            for entry in adv.get('affected') or []:
                pkg = entry.get('package') or {}
                if pkg.get('ecosystem') == 'PyPI' and pkg.get('name'):
                    index.setdefault(canon(pkg['name']), []).append(
                        {'id': adv['id'], 'aliases': adv.get('aliases') or [], 'summary': (adv.get('summary') or '')[:160],
                         'published': adv.get('published'), 'entry': entry,
                         'severity': [s.get('score') for s in adv.get('severity') or []][:1]})
    return index


def fixed_versions(entry: dict) -> list[str]:
    return [ev['fixed'] for r in entry.get('ranges') or [] for ev in r.get('events') or [] if 'fixed' in ev]


def dedupe(matches: list[dict]) -> list[dict]:
    """One entry per vulnerability: GHSA/PYSEC/CVE records that alias each other are merged."""
    groups: list[tuple[set, dict]] = []
    for m in matches:
        ids = {m['advisory'], *m['aliases']}
        for g, first in groups:
            if g & ids:
                g |= ids
                first['fixed_in'] = sorted(set(first['fixed_in']) | set(m['fixed_in']))
                break
        else:
            groups.append((ids, dict(m)))
    out = []
    for g, first in groups:
        first['ids'] = sorted(g)
        out.append(first)
    return out


def upgrade_target(installed_version: str, vulns: list[dict], V):
    """Smallest version that fixes every listed advisory; None when any advisory has no fixed release."""
    need = None
    for v in vulns:
        fixes = []
        for f in v['fixed_in']:
            try:
                if V(f) > V(installed_version):
                    fixes.append(V(f))
            except Exception:
                pass
        if not fixes:
            return None
        lowest = min(fixes)
        need = lowest if need is None or lowest > need else need
    return str(need) if need else None


def venv_label(venv: pathlib.Path) -> str:
    return f'{venv.parent.name}/{venv.name}' if venv.name in ('venv', '.venv') else venv.name


def check_deps(venvs: list[pathlib.Path], archive: pathlib.Path | None) -> list[dict]:
    if not archive or not archive.exists():
        return [finding('deps', 'medium', 'unknown', 'No OSV PyPI export available; dependencies not checked',
                        remediation='Run with --refresh-osv, or download https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip')]
    try:
        from packaging.version import Version as V
    except ImportError:
        return [finding('deps', 'medium', 'unknown', 'python3-packaging is missing; dependencies not checked')]
    index = osv_index(archive)
    age_days = round((time.time() - archive.stat().st_mtime) / 86400, 1)
    out, total = [], 0
    for venv in venvs:
        pkgs = installed(venv)
        total += len(pkgs)
        per_pkg = []
        for name, version in sorted(pkgs.items()):
            raw = [{'advisory': a['id'], 'aliases': a['aliases'], 'summary': a['summary'], 'published': a['published'],
                    'fixed_in': fixed_versions(a['entry']), 'cvss': a['severity']}
                   for a in index.get(name, []) if affected(version, a['entry'], V)]
            if raw:
                vulns = dedupe(raw)
                per_pkg.append({'package': name, 'installed': version, 'vulnerabilities': len(vulns),
                                'upgrade_to': upgrade_target(version, vulns, V),
                                'without_fix': sum(1 for v in vulns if not v['fixed_in']),
                                'advisories': [{'ids': v['ids'][:4], 'summary': v['summary'], 'fixed_in': v['fixed_in'][:3]}
                                               for v in vulns]})
        if per_pkg:
            n = sum(p['vulnerabilities'] for p in per_pkg)
            serves = any(p['package'] == 'open-webui' for p in per_pkg)
            out.append(finding('deps', 'high' if serves else 'medium', 'fail',
                               f'{venv_label(venv)}: {n} known vulnerabilit{"y" if n == 1 else "ies"} in {len(per_pkg)} package(s)',
                               {'venv': str(venv), 'packages': per_pkg},
                               'Upgrade in a copy of the venv, run its tests, then switch (keep the old venv for rollback).'))
    if not out:
        out.append(finding('deps', 'info', 'pass', f'No advisory matches across {total} installed packages'))
    out.append(finding('deps', 'info', 'pass' if age_days <= 8 else 'fail',
                       f'OSV export age: {age_days} days', {'archive': str(archive), 'advisory_packages': len(index)}))
    return out


def refresh_osv(dest: pathlib.Path) -> None:
    """Download the public OSV PyPI export (the only network use; fixed HTTPS URL; atomic replace)."""
    import urllib.request
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix('.part')
    with urllib.request.urlopen('https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip', timeout=600) as r, \
            tmp.open('wb') as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    zipfile.ZipFile(tmp).testzip()
    tmp.replace(dest)


# ---------- persistence drift ----------

def surfaces(home: pathlib.Path) -> dict[str, str]:
    """sha256 of every persistence surface; directories are expanded one level."""
    items = {}
    for rel in ('.bashrc', '.profile', '.bash_profile', '.zshrc', '.ssh/authorized_keys', '.ssh/rc', '.config/environment.d'):
        p = home / rel
        if p.is_file():
            items[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    for d in ('.config/systemd/user', '.config/autostart', '.config/systemd/user/default.target.wants',
              '.config/systemd/user/timers.target.wants'):
        base = home / d
        if base.is_dir():
            for p in sorted(base.iterdir()):
                if p.is_file() or p.is_symlink():
                    data = os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
                    items[f'{d}/{p.name}'] = hashlib.sha256(data).hexdigest()
    code, out, err = run(['crontab', '-l'])
    items['crontab'] = hashlib.sha256(out.encode()).hexdigest() if code == 0 else 'none'
    return items


def check_drift(current: dict, baseline: dict | None) -> list[dict]:
    if not baseline:
        return [finding('drift', 'low', 'unknown', f'No accepted baseline; {len(current)} persistence surfaces recorded',
                        {'surfaces': sorted(current)},
                        'Review this report, then run with --accept-baseline to make it the reference.')]
    old = baseline['surfaces']
    added = sorted(set(current) - set(old))
    removed = sorted(set(old) - set(current))
    changed = sorted(k for k in set(current) & set(old) if current[k] != old[k])
    if added or removed or changed:
        return [finding('drift', 'medium', 'fail', 'Persistence surfaces changed since the accepted baseline',
                        {'added': added, 'removed': removed, 'changed': changed, 'baseline_accepted_at': baseline.get('accepted_at')},
                        'Confirm each change is yours (deploys, new units); then re-accept the baseline.')]
    return [finding('drift', 'info', 'pass', f'{len(current)} persistence surfaces match the baseline',
                    {'baseline_accepted_at': baseline.get('accepted_at')})]


# ---------- main ----------

def audit(cfg: dict, home: pathlib.Path, ss_text: str | None = None, etc: pathlib.Path = pathlib.Path('/etc'),
          baseline: dict | None = None) -> dict:
    def expand(p):
        return pathlib.Path(os.path.expanduser(p))

    def expand_all(patterns):  # entries may be globs, e.g. ~/.local/share/haven-workspaces/*
        out = []
        for pat in patterns:
            matches = sorted(pathlib.Path('/').glob(os.path.expanduser(pat).lstrip('/'))) if any(c in pat for c in '*?[') else [expand(pat)]
            out += matches
        return out
    if ss_text is None:
        _, ss_text, _ = run(['ss', '-ltnupH'])
    sockets = parse_ss(ss_text)
    findings = []
    findings += check_exposure(sockets, cfg.get('exposure_allowlist', []))
    findings += check_ssh(etc, any(s['local'].endswith(':22') and not LOOPBACK.match(s['local']) for s in sockets))
    findings += check_secret_files([expand(p) for p in cfg.get('secret_roots', [])])
    findings += check_git_secrets(expand_all(cfg.get('git_repos', [])))
    findings += check_deps(expand_all(cfg.get('venvs', [])), expand(cfg['osv_pypi_export']) if cfg.get('osv_pypi_export') else None)
    current = surfaces(home)
    findings += check_drift(current, baseline)
    counts = {}
    for f in findings:
        if f['status'] != 'pass':
            key = f"{f['status']}:{f['severity']}"
            counts[key] = counts.get(key, 0) + 1
    return {'schema': SCHEMA, 'host': os.uname().nodename, 'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'counts': counts, 'findings': findings, 'surfaces': current,
            'scope': 'read-only; no changes made; no network used'}


def markdown(report: dict) -> str:
    order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
    lines = [f"# haven-sentinel — {report['host']} — {report['generated_utc']}", '',
             'Read-only audit; every line below is a measurement of this host.', '']
    for f in sorted(report['findings'], key=lambda f: (f['status'] == 'pass', order[f['severity']])):
        mark = {'fail': 'FAIL', 'unknown': 'UNKNOWN', 'pass': 'PASS'}[f['status']]
        lines.append(f"- **{mark}** [{f['severity']}] `{f['check']}` — {f['title']}")
        if f['status'] != 'pass' and f.get('remediation'):
            lines.append(f"  - Fix: {f['remediation']}")
        if f['check'] == 'deps' and f['status'] == 'fail':
            for p in sorted(f['evidence']['packages'], key=lambda p: -p['vulnerabilities']):
                fix = f"upgrade to >= {p['upgrade_to']}" if p['upgrade_to'] else f"{p['without_fix']} without a fixed release"
                lines.append(f"  - {p['package']} {p['installed']}: {p['vulnerabilities']} — {fix}")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--refresh-osv', action='store_true', help='Download the current OSV PyPI export first (network).')
    ap.add_argument('--refresh-osv-days', type=float, help='Refresh only when the export is older than this many days.')
    ap.add_argument('--accept-baseline', action='store_true',
                    help='Make the current persistence surfaces the reference (after reviewing the latest report).')
    args = ap.parse_args(argv)
    os.umask(0o077)
    args.out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(args.config.read_text())
    export = pathlib.Path(os.path.expanduser(cfg['osv_pypi_export'])) if cfg.get('osv_pypi_export') else None
    stale = export is not None and args.refresh_osv_days is not None and (
        not export.exists() or time.time() - export.stat().st_mtime > args.refresh_osv_days * 86400)
    if export is not None and (args.refresh_osv or stale):
        try:
            refresh_osv(export)
        except Exception as exc:  # the audit still runs; the export-age finding shows the staleness
            print(f'OSV refresh failed: {type(exc).__name__}: {exc}', file=sys.stderr)
    base_path = args.out / 'baseline.json'
    baseline = json.loads(base_path.read_text()) if base_path.exists() else None
    try:
        report = audit(cfg, pathlib.Path.home(), baseline=baseline)
    except Exception as exc:
        print(f'AUDIT FAILED: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2
    stamp = report['generated_utc'].replace(':', '').replace('-', '')
    (args.out / f'report-{stamp}.json').write_text(json.dumps(report, indent=1) + '\n')
    (args.out / 'latest.json').write_text(json.dumps(report, indent=1) + '\n')
    (args.out / 'latest.md').write_text(markdown(report))
    if args.accept_baseline:
        base_path.write_text(json.dumps({'accepted_at': report['generated_utc'], 'surfaces': report['surfaces']}, indent=1) + '\n')
    print(markdown(report))
    return 1 if any(f['status'] == 'fail' and f['severity'] == 'high' for f in report['findings']) else 0


if __name__ == '__main__':
    sys.exit(main())
