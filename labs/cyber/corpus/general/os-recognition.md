---
id: general.os-recognition
title: Recognising operating systems and choosing the right commands
domain: general
topic: platform
source_url: https://www.freedesktop.org/software/systemd/man/latest/os-release.html
source_org: freedesktop.org
published: null
retrieved: 2026-10-31
product_version: os-release(5); macOS sw_vers(1); uname(1)
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [linux, macos, windows]
prerequisites: []
see_also: [https://support.apple.com/guide/terminal/welcome/mac]
---

# Recognising operating systems

## Evidence that identifies the platform

- `uname -s`: `Linux`, `Darwin` (macOS), `FreeBSD`. `uname -r` on Linux gives the kernel; on macOS it gives the Darwin version (Darwin 25 is macOS 26).
- Linux distribution: `/etc/os-release` fields `ID` (`ubuntu`, `debian`, `rhel`, `fedora`, `alpine`, `arch`), `VERSION_ID`, `ID_LIKE`.
- macOS: `sw_vers` prints ProductName/ProductVersion/BuildVersion. There is no `/etc/os-release` on macOS.
- Windows: `ver`, `systeminfo`, or PowerShell `$PSVersionTable.OS` / `Get-CimInstance Win32_OperatingSystem`.

## Package and service managers by platform

| Platform | Packages | Services |
|---|---|---|
| Debian / Ubuntu | `apt`, `dpkg -l` | `systemctl` (systemd) |
| RHEL / Fedora / Rocky | `dnf` (older: `yum`), `rpm -qa` | `systemctl` |
| Alpine | `apk` | `rc-service` / OpenRC (often no systemd, busybox userland, musl libc) |
| macOS | `brew` (if installed), `pkgutil` | `launchctl` (launchd); no systemd |
| Windows | `winget`, `choco` (if installed) | `Get-Service`, `sc.exe` |

## Pitfalls

- Inside a container, `uname -r` shows the **host** kernel, while `/etc/os-release` shows the container image's distribution.
- BusyBox tools on Alpine accept fewer flags (e.g. `ps aux` differs; `ss` may be missing, use `netstat`).
- macOS ships BSD userland: `sed -i ''` and `date -v` differ from GNU.
- Do not assume `sudo`, Docker or a package manager exists; check with `command -v`.
