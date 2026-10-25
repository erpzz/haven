#!/usr/bin/env bash
# Minimal, operator-approved Ubuntu baseline. Never formats disks or changes authentication policy.
set -euo pipefail

usage() {
  printf 'Usage: %s [--plan|--apply]\n' "$0"
}
mode="${1:---plan}"
if [[ $# -gt 1 ]]; then usage >&2; exit 2; fi
case "$mode" in
  --plan|--apply) ;;
  *) usage >&2; exit 2 ;;
esac

packages=(openssh-server ca-certificates curl git jq tmux python3-venv)
printf 'Haven Core minimal bootstrap\n'
printf 'Planned operations:\n'
printf '  apt-get update\n'
printf '  apt-get install -y %s\n' "${packages[*]}"
printf '  systemctl enable --now ssh\n'
printf 'No firewall, SSH auth policy, drivers, storage, firmware or Tailscale changes.\n'

if [[ "$mode" == "--plan" ]]; then
  printf 'PLAN ONLY: no changes made. Use --apply from an interactive Ubuntu session.\n'
  exit 0
fi

if [[ ! -r /etc/os-release ]]; then echo 'OS identification unavailable' >&2; exit 1; fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo 'Refusing modifications: target OS is not Ubuntu' >&2
  exit 1
fi
if [[ ! -t 0 ]]; then
  echo 'Refusing noninteractive apply; run at a human-operated terminal' >&2
  exit 1
fi
if [[ $EUID -eq 0 ]]; then
  echo 'Run from an unprivileged operator account with sudo, not as root' >&2
  exit 1
fi

read -r -p 'Type APPLY to approve listed changes: ' confirmation
if [[ "$confirmation" != 'APPLY' ]]; then
  echo 'No changes made'
  exit 1
fi

sudo -v
sudo apt-get update
sudo apt-get install -y "${packages[@]}"
sudo systemctl enable --now ssh
printf 'SSH service status: '
systemctl is-active ssh
printf 'Bootstrap completed. Verify host fingerprint locally before remote SSH.\n'
