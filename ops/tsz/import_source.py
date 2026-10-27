"""Ingest a private, owner-supplied network inventory as DISCOVERY ONLY.

This bridges router/MDM/tailnet inventory exports, not active network scanning.
Even a verified inventory source does not approve access to an observed device.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = "tsz-network-inventory-v1"
MAC = re.compile(r"^(?:[0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}$")
INTERFACE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
SOURCE = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
MAX_SIZE = 1024 * 1024
MAX_DEVICES = 2000


class InventoryError(ValueError):
    pass


def read_owner_inventory(path: Path) -> dict:
    """Do not accept world-readable inventories, symlinks or oversized JSON."""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise InventoryError("network inventory must be an owner-private regular file")
    if info.st_size > MAX_SIZE:
        raise InventoryError("network inventory exceeds size limit")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise InventoryError("network inventory schema mismatch")
    return doc


def parse_network_inventory(doc: dict, interfaces: set[str], now: int) -> list[dict]:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise InventoryError("unexpected network inventory schema")
    source = doc.get("source")
    if not isinstance(source, str) or not SOURCE.fullmatch(source):
        raise InventoryError("invalid inventory source")
    captured = doc.get("observed_at")
    if type(captured) is not int or captured > now or now - captured > 3600:
        raise InventoryError("stale or future network inventory")
    if not interfaces or any(not isinstance(i, str) or not INTERFACE.fullmatch(i) for i in interfaces):
        raise InventoryError("explicit source interfaces required")
    devices = doc.get("devices")
    if not isinstance(devices, list) or len(devices) > MAX_DEVICES:
        raise InventoryError("invalid device list size")
    observations = []
    for device in devices:
        if not isinstance(device, dict):
            raise InventoryError("invalid device entry")
        ip, mac, iface = device.get("address"), device.get("mac"), device.get("interface")
        if not isinstance(iface, str):
            raise InventoryError("invalid interface in inventory")
        if iface not in interfaces:
            continue
        if not isinstance(mac, str) or not MAC.fullmatch(mac):
            raise InventoryError("invalid MAC in allowed interface")
        if not isinstance(ip, str):
            raise InventoryError("invalid network address")
        try:
            address = str(ipaddress.ip_address(ip))
        except ValueError as exc:
            raise InventoryError("invalid IP in inventory") from exc
        normalized = ":".join(part.zfill(2).lower() for part in mac.split(":"))
        cid = "neighbor-" + hashlib.sha256((iface + "\0" + normalized).encode("ascii")).hexdigest()[:24]
        observations.append({"candidate_id": cid, "interface": iface, "mac": normalized,
                             "address": address, "origin": "owner-export:" + source})
    return observations
