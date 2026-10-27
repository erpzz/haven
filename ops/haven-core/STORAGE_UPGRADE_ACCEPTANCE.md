# Slink root SSD to SuperSpeed: acceptance procedure

Goal: measure what moving Slink's root disk from USB 2 to a SuperSpeed port actually changes. Nothing here writes
to the root filesystem, and nothing runs I/O benchmarks during normal operation.

## Current state (read-only, 2026-10-27)

| Item | Value | Source |
|---|---|---|
| Root and `/boot/efi` | `sdb`, Crucial X9 1 TB, USB, `uas` driver | `lsblk`, `findmnt` |
| Negotiated link | **480 Mb/s, USB 2.10**, on bus 001 (a USB 2 root hub) | `/sys/bus/usb/devices/*/speed`, `lsusb -t` |
| Free SuperSpeed root hubs | buses 002, 004, 006 (10,000 M); bus 008 has a SanDisk stick at 5,000 M | `lsusb -t` |
| Boot identity | `root=UUID=4b248510-…`, and fstab mounts `/` and `/boot/efi` by UUID | `/proc/cmdline`, `/etc/fstab` |
| 35B-A3B Lab cold load (22.1 GB) | **344 s**: job started 20:17:51, connected 20:23:35 | Lab job and connection timestamps |
| Strata cold start | **926 s**: unit start 18:58:26, `ready` 19:13:52 | `journalctl --user -u haven-strata` |

Because the mounts use UUIDs, a port move only changes the kernel name (`sdb` → `sdX`). Boot does not depend on it.

## Before the move (no load on the disk)

1. Record the read-only baseline: `ops/storage/diagnose.py` (Codex B), or failing that the three commands above, into `~/.local/state/haven-admin/storage/before.json`.
2. Find the cause. The X9 is a USB 3.2 Gen 2 device, so 480 Mb/s means the port, hub or cable is USB 2 only. Identify the physical port behind bus 001 port 006 and a port on a 10,000 M root hub, using the motherboard manual or the colour coding. Prefer a rear port wired directly to the chipset, not a front-panel header.
3. Wait for a maintenance window. Strata stopped and no Lab engine loaded, so nothing is lost. This needs the owner, because the 35B is in use now.

## The move (owner, at the machine)

1. In the Lab, unload or stop whatever is running: `labctl unload`; Strata already stopped. Then `sudo poweroff`. Do not hot-unplug the root disk.
2. Move the X9 to the SuperSpeed port, with the cable it shipped with (USB-C to USB-C or USB-C to A Gen 2).
3. Power on.

**Rollback:** if it doesn't boot, power off and put the disk back in the original port. Nothing on the disk changed.

## After the move: acceptance

| # | Check | Pass |
|---|---|---|
| 1 | `cat /sys/block/<root disk>/device/../../../../speed` (or `lsusb -t`) | 5,000 or 10,000 Mb/s, driver `uas` |
| 2 | `findmnt /` shows the same UUID; `systemctl --user is-active haven-model-lab` | same UUID; active |
| 3 | `smartctl -a` (read-only) on the disk | no new errors versus `before.json` |
| 4 | Read throughput, maintenance window only: `fio --readonly --direct=1 --rw=read --bs=1M --size=4G --filename=<model .gguf>`, 3 runs | median recorded. A USB 2 baseline tops out around 40 MiB/s |
| 5 | **The user-visible measure:** time of the next cold load you would do anyway, from Lab job `created_at` to `connection.connected_at` | compare with 344 s for the 35B (same file, same profile) |
| 6 | The next ordinary Strata start, `journalctl` start → `ready` | compare with 926 s |

Rows 5 and 6 use loads that would happen anyway. No extra cold loads are run just to measure. Record each result
with its timestamp in `~/.local/state/haven-admin/storage/after.json`. The page cache must be cold for row 5 to
count: either the first load after the reboot, or the owner explicitly drops caches.

## Risks

- A different USB controller may not have `uas` quirks applied. Check `dmesg` for `uas` resets after the move; if any appear, roll back.
- A front-panel or hub port may still negotiate USB 2. Row 1 catches it before anything else.
- Moving the root disk to internal SATA (the MX500 `sdc` is present) would be faster still, but it is a data migration, not a port move, and is not part of this procedure.
