import json
import pathlib
import subprocess
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import sentinel as s  # noqa: E402

SS = """tcp   LISTEN 0 4096 127.0.0.1:8877 0.0.0.0:* users:(("python3",pid=1,fd=3))
tcp   LISTEN 0 4096 0.0.0.0:22 0.0.0.0:*
tcp   LISTEN 0 4096 0.0.0.0:8080 0.0.0.0:* users:(("open-webui",pid=7,fd=9))
udp   UNCONN 0 0 127.0.0.53%lo:53 0.0.0.0:*
tcp   LISTEN 0 4096 [::1]:9000 [::]:*
"""


def test_exposure_flags_only_non_loopback_non_allowlisted():
    assert s.check_exposure(s.parse_ss('tcp LISTEN 0 1 [::]:22 [::]:*'), ['tcp [::]:22'])[0]['status'] == 'pass'
    f = s.check_exposure(s.parse_ss(SS), ['tcp 0.0.0.0:22'])
    assert f[0]['status'] == 'fail' and f[0]['severity'] == 'high'
    assert [x['local'] for x in f[0]['evidence']['sockets']] == ['0.0.0.0:8080']
    assert f[0]['evidence']['sockets'][0]['process'] == 'open-webui'
    assert s.check_exposure(s.parse_ss(SS), ['tcp 0.0.0.0:*'])[0]['status'] == 'pass'


def test_ssh_unreadable_config_is_unknown_never_pass(tmp_path):
    d = tmp_path / 'ssh' / 'sshd_config.d'
    d.mkdir(parents=True)
    (tmp_path / 'ssh' / 'sshd_config').write_text('KbdInteractiveAuthentication no\n')
    locked = d / '50-cloud-init.conf'
    locked.write_text('PasswordAuthentication yes\n')
    locked.chmod(0)
    try:
        f = s.check_ssh(tmp_path, True)
    finally:
        locked.chmod(0o600)
    if f[0]['status'] != 'fail':  # running as root can read anything
        assert f[0]['status'] == 'unknown' and 'unreadable' in f[0]['evidence']
    assert s.check_ssh(tmp_path, True)[0]['status'] == 'fail'  # readable: PasswordAuthentication yes
    (d / '50-cloud-init.conf').write_text('PasswordAuthentication no\n')
    assert s.check_ssh(tmp_path, True)[0]['status'] == 'pass'


def test_secret_files_mode(tmp_path):
    k = tmp_path / 'state' / 'api-key'
    k.parent.mkdir()
    k.write_text('x')
    k.chmod(0o644)
    (tmp_path / 'state' / 'notes.txt').write_text('x')
    clone = tmp_path / 'state' / 'sandbox' / 'repo'
    (clone / '.git').mkdir(parents=True)
    (clone / 'create_token.html').write_text('x')  # third-party source in a checkout: not a credential file
    f = s.check_secret_files([tmp_path])
    assert f[0]['status'] == 'fail' and f[0]['evidence']['files'][0]['path'].endswith('api-key')
    k.chmod(0o600)
    assert s.check_secret_files([tmp_path])[0]['status'] == 'pass'


def test_git_secrets_redacts_and_ignores_untracked(tmp_path):
    repo = tmp_path / 'r'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    token = 'hf_' + 'a1B2c3D4e5' * 4
    (repo / 'config.py').write_text(f'TOKEN = "{token}"\n')
    (repo / 'untracked.txt').write_text(token)
    subprocess.run(['git', '-C', str(repo), 'add', 'config.py'], check=True)
    f = s.check_git_secrets([repo])
    hit = f[0]['evidence']['hits']
    assert f[0]['status'] == 'fail' and len(hit) == 1 and hit[0]['file'] == 'config.py' and hit[0]['line'] == 1
    assert token not in json.dumps(f)


def make_osv(path, advisories):
    with zipfile.ZipFile(path, 'w') as z:
        for a in advisories:
            z.writestr(a['id'] + '.json', json.dumps(a))


def venv_with(tmp_path, pkgs):
    sp = tmp_path / 'venv' / 'lib' / 'python3.12' / 'site-packages'
    for name, ver in pkgs.items():
        d = sp / f'{name}-{ver}.dist-info'
        d.mkdir(parents=True)
        (d / 'METADATA').write_text(f'Metadata-Version: 2.1\nName: {name}\nVersion: {ver}\n\nbody\n')
    return tmp_path / 'venv'


def test_deps_osv_ranges_in_version_order(tmp_path):
    osv = tmp_path / 'all.zip'
    make_osv(osv, [
        {'id': 'GHSA-1', 'affected': [{'package': {'ecosystem': 'PyPI', 'name': 'Open_WebUI'},
                                       'ranges': [{'type': 'ECOSYSTEM', 'events': [{'fixed': '0.9.6'}, {'introduced': '0'}]}]}]},
        {'id': 'GHSA-2', 'affected': [{'package': {'ecosystem': 'PyPI', 'name': 'jinja2'},
                                       'ranges': [{'type': 'ECOSYSTEM', 'events': [{'introduced': '3.0'}, {'last_affected': '3.1.2'}]}]}]},
        {'id': 'GHSA-3', 'withdrawn': '2026-01-01', 'affected': [{'package': {'ecosystem': 'PyPI', 'name': 'jinja2'},
                                                                 'versions': ['3.1.6']}]},
    ])
    venv = venv_with(tmp_path, {'open-webui': '0.9.5', 'Jinja2': '3.1.6'})
    f = s.check_deps([venv], osv)
    pkgs = f[0]['evidence']['packages']
    assert [(p['package'], p['upgrade_to']) for p in pkgs] == [('open-webui', '0.9.6')] and f[0]['severity'] == 'high'
    venv2 = venv_with(tmp_path / 'b', {'open-webui': '0.9.6', 'jinja2': '3.1.2'})
    pkgs2 = s.check_deps([venv2], osv)[0]['evidence']['packages']
    assert [(p['package'], p['upgrade_to'], p['without_fix']) for p in pkgs2] == [('jinja2', None, 1)]


def test_aliases_are_one_vulnerability_and_upgrade_target_covers_all():
    from packaging.version import Version as V
    vulns = s.dedupe([{'advisory': 'GHSA-a', 'aliases': ['CVE-1'], 'fixed_in': ['2.0']},
                      {'advisory': 'PYSEC-9', 'aliases': ['CVE-1'], 'fixed_in': ['2.0']},
                      {'advisory': 'GHSA-b', 'aliases': [], 'fixed_in': ['1.5', '2.3']}])
    assert len(vulns) == 2
    assert s.upgrade_target('1.0', vulns, V) == '2.0'
    assert s.upgrade_target('1.9', vulns, V) == '2.3'


def test_drift_detects_added_and_changed_units(tmp_path):
    home = tmp_path
    units = home / '.config' / 'systemd' / 'user'
    units.mkdir(parents=True)
    (units / 'a.service').write_text('[Service]\nExecStart=/bin/true\n')
    base = {'accepted_at': 't0', 'surfaces': s.surfaces(home)}
    assert s.check_drift(s.surfaces(home), base)[0]['status'] == 'pass'
    (units / 'a.service').write_text('[Service]\nExecStart=/tmp/x\n')
    (units / 'b.timer').write_text('[Timer]\n')
    (units / 'a.service.d').mkdir()
    (units / 'a.service.d' / 'override.conf').write_text('[Service]\nExecStart=\nExecStart=/tmp/y\n')
    f = s.check_drift(s.surfaces(home), base)[0]
    assert f['status'] == 'fail'
    assert f['evidence']['added'] == ['.config/systemd/user/a.service.d/override.conf', '.config/systemd/user/b.timer']
    assert f['evidence']['changed'] == ['.config/systemd/user/a.service']
