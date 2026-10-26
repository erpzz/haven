# Prepared Strata on Linux

This uses [official release v0.2.6](https://github.com/Niko1221/Strata/releases/tag/v0.2.6)
and its signed component feed. The preserved Windows v0.1.39 installer pin is not
silently updated. [Linux pins](strata-linux-pins.json) record the separate source,
Control archive, engine archive, feed and existing IQ2_XS model identity.

Actual installation: Control 0.1.51 checksum/signature checks passed. Signed
engine 0.1.50 was selected for Linux CUDA 13, explicitly including `sm_75`, and
passed its binary version check. Both pinned model shards have now been downloaded, SHA-256 verified and
prepared by a separate ordinary-user job with `--no-start`. The finite first
response job is in progress; its result is recorded in the current handoff. Do not turn a binary check into a
model-performance claim.

## Installation recipe already in use

The private run used a fresh scoped `~/.local/share/haven-strata` directory. The
downloaded official `install.sh` was reviewed and matched SHA-256
`3d93b5fba42b6be68514c0ae6bb50784c68eb72319562c2e505780e411750c19`.
The installer used release v0.2.6, not an unpinned latest URL, and retained
upstream signature enforcement. No root, global Python, compiler, source build,
desktop app or model load was required.

The following environment must stay consistent for Strata commands:

```sh
export STRATA_HOME="$HOME/.local/state/haven-strata"
export STRATA_COMPONENTS_DIR="$HOME/.local/share/haven-strata/components"
export STRATA_UPDATE_FEED=https://github.com/Niko1221/Strata/releases/download/v0.2.6
strata_cli="$HOME/.local/share/haven-strata/bin/strata"
```

The first engine command was `"$strata_cli" update --no-control --backend cuda`.
The verified signed feed chose the compatible variant. Preparation used:

```sh
"$strata_cli" install -- --family qwen --model IQ2_XS --context 8192 --parallel 1 --vision no --mtp off --data-dir "$HOME/.local/share/haven-strata/data" --port 8880 --no-browser --no-start --skip-build --source huggingface --yes
```

That download is about 68 GB. Preserve partial chunks for resumption. Inspect
the existing `haven-strata-model` unit and its error before launching another
installer. The upstream preparer validates shards and writes a local run config;
keep that config, model paths and journals private. The initial recipe leaves
experimental speed projection, vision and MTP off. No automatic tuning run is
needed to obtain the first answer.

## Serve through Haven

After preparation succeeds, review the generated native config and save a
private mode-0600 copy as `~/.local/state/haven-strata/run-profile.json`. Preserve
its real pack/model paths, signed `component:strata-engine` selection, 8K context
and single-slot setting. Remove any unused image/MCP/startup-hook configuration.
Do not invent a ready config while the download is incomplete.

Install `systemd/haven-strata.service` into the ordinary user's unit directory,
reload the manager, then start it explicitly:

```sh
systemctl --user start haven-strata
journalctl --user -u haven-strata -n 40 --no-pager
```

The wrapper runs native `strata serve` in the foreground, on authenticated
`127.0.0.1:8880`, with remote image fetching/MCP disabled. It creates a private
API key locally; no key is printed or supplied through process arguments. The
unit contains its children, limits memory to 58 GiB with a 54-GiB soft threshold
and 1-GiB swap ceiling, and does not retry or automatically start at boot.
It performs no installation, downloads, updates or tuning when started.

The Lab's Linux Setup panel has **Connect Haven Strata**. It reads the private
key on the server and attaches only the fixed loopback endpoint. The key never
enters the browser or API state. The same operation is available on the server:

```sh
python3 ~/projects/haven/ops/haven-core/labctl.py strata
```

An owned GGUF must be unloaded first. Disconnecting/stopping the Lab leaves
external Strata running. Stop it explicitly with
`systemctl --user stop haven-strata`; this stops only that unit's process group.
The Mac's standard tunnel forwards the Lab's port 8877. To use Strata's native
UI separately, establish another explicit loopback SSH forward for port 8880.
The Haven chat interface itself needs no second forward.

## Rollback and handback

Stop the Strata user unit and disconnect it in the Lab. Keep installed components,
prepared data and resumable downloads unless the operator decides to archive
them. Removing this integration requires only its user unit, wrapper and private
profile/key; it does not remove drivers, modify firmware, expose ports or change
the Windows installer. Preserve negative results and exact component pins.
Do not describe a stopped HTTP stream as proof that a hybrid engine ceased work;
use the owned service stop when confirmed process cessation is required.

A finite first run can be requested explicitly with `first-strata-run.py --execute`
only when the Lab is idle. It retains a new private receipt, checks one real
response and external ownership, then stops Strata and restores the existing
fast GGUF. `haven-strata-first-response` is its one-shot unit, not an enabled
background benchmark or recurring job. Inspect an existing run before starting
another.
