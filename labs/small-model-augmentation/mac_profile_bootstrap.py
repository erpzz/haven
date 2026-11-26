#!/usr/bin/env python3
"""Create a fresh isolated Hermes profile for the #217 Mac campaign.

The bootstrap is deliberately create-new-only. It never mutates ~/.hermes or an
existing profile. The resulting profile contains:
- exactly one enabled user plugin: haven-scope, copied from reviewed repo bytes;
- exactly one MCP server: the synthetic Red Factory fixture;
- a private .env that does not define HERMES_ENABLE_PROJECT_PLUGINS.

The campaign's #212 preflight remains the authority before any guarded run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from typing import Any

SCHEMA = "haven.mac-hermes-profile-bootstrap.v1"


class BootstrapError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(256 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _private_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, mode)
    except OSError as exc:
        raise BootstrapError("PROFILE_FILE_CREATE_FAILED") from exc
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _copy_regular_private(src: Path, dst: Path) -> str:
    if src.is_symlink() or not src.is_file():
        raise BootstrapError("SOURCE_FILE_UNTRUSTED")
    raw = src.read_bytes()
    _private_write(dst, raw)
    return hashlib.sha256(raw).hexdigest()


def create_profile(*, home: Path, augmentation_root: Path,
                   python: Path | None = None) -> dict[str, Any]:
    home = Path(home)
    augmentation_root = Path(augmentation_root).resolve()
    if not home.is_absolute():
        raise BootstrapError("PROFILE_PATH_NOT_ABSOLUTE")
    if home.exists():
        raise BootstrapError("PROFILE_ALREADY_EXISTS")
    if not augmentation_root.is_dir() or augmentation_root.is_symlink():
        raise BootstrapError("AUGMENTATION_ROOT_INVALID")

    plugin_source = augmentation_root / "hermes_scope_plugin"
    fixture = augmentation_root / "red_factory" / "mcp_fixture.py"
    for required in (plugin_source / "__init__.py", plugin_source / "plugin.yaml", fixture):
        if required.is_symlink() or not required.is_file():
            raise BootstrapError("CAMPAIGN_SOURCE_MISSING")

    python = Path(python or os.environ.get("PYTHON", "") or __import__("sys").executable).resolve()
    if not python.is_file() or not os.access(python, os.X_OK):
        raise BootstrapError("PYTHON_NOT_EXECUTABLE")

    try:
        home.mkdir(mode=0o700, parents=False)
        plugins = home / "plugins"
        plugins.mkdir(mode=0o700)
        plugin = plugins / "haven-scope"
        plugin.mkdir(mode=0o700)

        hashes = {
            "plugin_init_sha256": _copy_regular_private(
                plugin_source / "__init__.py", plugin / "__init__.py"
            ),
            "plugin_manifest_sha256": _copy_regular_private(
                plugin_source / "plugin.yaml", plugin / "plugin.yaml"
            ),
        }
        readme = plugin_source / "README.md"
        if readme.is_file() and not readme.is_symlink():
            hashes["plugin_readme_sha256"] = _copy_regular_private(
                readme, plugin / "README.md"
            )

        _private_write(
            home / ".env",
            b"# isolated Haven/Qwythos qualification profile\n",
        )

        config = {
            "plugins": {
                "enabled": ["haven-scope"],
                "disabled": [],
                "hook_callback_timeout": 30,
                "load_timeout_seconds": 10,
            },
            "mcp_servers": {
                "red-factory": {
                    "command": str(python),
                    "args": [str(fixture)],
                }
            },
        }
        raw = json.dumps(
            config, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8") + b"\n"
        _private_write(home / "config.yaml", raw)
        hashes["config_sha256"] = hashlib.sha256(raw).hexdigest()
        hashes["profile_env_sha256"] = _sha(home / ".env")
        hashes["mcp_fixture_sha256"] = _sha(fixture)

        body = {
            "schema": SCHEMA,
            "status": "pass",
            "home": str(home),
            "augmentation_root": str(augmentation_root),
            "python": str(python),
            "enabled_user_plugins": ["haven-scope"],
            "mcp_servers": ["red-factory"],
            "project_plugins_enabled": False,
            "hashes": hashes,
        }
        body["receipt_sha256"] = hashlib.sha256(
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        ).hexdigest()
        _private_write(
            home / "bootstrap-receipt.json",
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8") + b"\n",
        )
        return body
    except Exception:
        # Only clean the directory we just created. Existing paths are refused
        # before creation, so this cannot remove user state.
        try:
            shutil.rmtree(home)
        except OSError:
            pass
        raise


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument(
        "--augmentation-root", type=Path,
        default=Path(__file__).resolve().parent,
    )
    p.add_argument("--python", type=Path)
    args = p.parse_args(argv)
    result = create_profile(
        home=args.home,
        augmentation_root=args.augmentation_root,
        python=args.python,
    )
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "home": result["home"],
        "receipt_sha256": result["receipt_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
