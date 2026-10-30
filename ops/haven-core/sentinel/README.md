# haven-sentinel

A daily, read-only security posture audit of a Haven host (Slink). It changes nothing on the host. Its only network use is a weekly download of the public OSV PyPI advisory export.

Every finding is a measurement of this host, with its evidence attached. "Unknown" means it could not be measured (for example, a root-only file), and it is never shown as a pass. Nothing comes from threat feeds or guesswork.

| Check | Fails when |
|---|---|
| `exposure` | a socket listens beyond loopback and is not on the allowlist in `sentinel.slink.json` (each entry has a reason) |
| `ssh` | sshd accepts passwords or root logins on a LAN-reachable port; an unreadable config is reported as UNKNOWN |
| `secrets` | a credential-named file (key, token, secret, `.pem`, `id_*`) is readable by group or others; source checkouts are skipped |
| `git-secrets` | a tracked file in a Haven checkout or agent workspace contains a private key or a Hugging Face, GitHub, OpenAI, Anthropic, AWS or Slack token pattern; values are redacted in reports |
| `deps` | an installed package in a Haven venv matches an OSV advisory. Matching is offline against the export and evaluates OSV ranges in version order. GHSA, PYSEC and CVE aliases count as one vulnerability. The report gives the smallest upgrade that fixes everything, or says no fix exists |
| `drift` | a persistence surface (user units and timers, cron, shell rc files, `authorized_keys`, autostart) differs from the owner-accepted baseline |

Severity:

- **high:** a reachable service, a password-capable SSH port, a readable secret, a committed credential, or a vulnerable package in the internet-facing UI venv (`open-webui` itself).
- **medium:** everything else that fails.

Exit status: 0, 1 (a high finding failed) or 2 (the audit itself failed).

## Run

```bash
python3 sentinel.py --config sentinel.slink.json --out ~/.local/state/haven-sentinel/reports
```

The latest report is written to `latest.md` and `latest.json`, plus a timestamped JSON copy. To make the current persistence surfaces the reference after reviewing a report, add `--accept-baseline`.

## Install (user units, no root)

```bash
mkdir -p ~/.local/state/haven-sentinel/code && cp -r sentinel.py sentinel.slink.json README.md ~/.local/state/haven-sentinel/code/
cp systemd/haven-sentinel.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now haven-sentinel.timer
```

## Rollback

```bash
systemctl --user disable --now haven-sentinel.timer
rm ~/.config/systemd/user/haven-sentinel.{service,timer} && systemctl --user daemon-reload
```

Reports in `~/.local/state/haven-sentinel/` can be deleted or kept. Nothing else was changed.

## Limits

- It does not use root, so it cannot read `sshd -T`, firewall rules or system-wide packages.
- It checks Python dependencies only. Debian packages, snaps, the Node toolchain and model files are not covered.
- A matching advisory means the installed version falls inside a published affected range. It does not prove that Haven exercises the vulnerable code path.
