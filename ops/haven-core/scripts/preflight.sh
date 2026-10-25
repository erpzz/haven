#!/usr/bin/env bash
# Read-only local inventory; outputs may contain machine identifiers. Do not commit raw output.
set -uo pipefail

section() { printf '\n== %s ==\n' "$1"; }
has() { command -v "$1" >/dev/null 2>&1; }
show() {
  local title="$1"; shift
  printf '\n-- %s --\n' "$title"
  "$@" 2>&1 || printf '[unavailable / insufficient permissions]\n'
}

section "System"
show "OS" bash -c 'source /etc/os-release; printf "%s (%s)\n" "${PRETTY_NAME:-unknown}" "${VERSION_ID:-unknown}"'
show "Kernel" uname -sr
show "CPU" bash -c 'lscpu | grep -E "^(Architecture|Model name|CPU\(s\)|Thread\(s\) per core):"'
if has free; then show "Memory" free -h; fi

section "Storage"
if has lsblk; then show "Disks (includes identifiers; keep output private)" lsblk -o NAME,MODEL,SIZE,TRAN,FSTYPE,MOUNTPOINTS; fi
if has findmnt; then show "Root mount" findmnt -no SOURCE,FSTYPE,OPTIONS /; fi
show "Root space" df -h /

section "Networking and access"
if has hostname; then show "Hostname" hostname; fi
if has ip; then show "Local addresses" ip -brief address; fi
if has systemctl; then
  show "SSH enabled" systemctl is-enabled ssh
  show "SSH active" systemctl is-active ssh
fi
if has tailscale; then show "Tailscale version" tailscale version; fi

section "GPU and containers"
if has nvidia-smi; then show "NVIDIA GPU" nvidia-smi --query-gpu=name,driver_version,memory.total,temperature.gpu --format=csv,noheader; else echo "nvidia-smi: not installed or unavailable"; fi
if has docker; then show "Docker client version" docker --version; fi

section "Completion"
echo "Read-only inventory complete. Keep raw results local; redact before any PR or agent handoff."
