#!/usr/bin/env python3
"""Offline quality gate for manual defensive IOC review; never connects or deploys."""
from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DOMAIN = re.compile(r'(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}$', re.I)


def good_indicator(kind: str, indicator: str) -> bool:
    if kind == 'ipv4':
        try:
            ip = ipaddress.ip_address(indicator)
            return ip.version == 4 and ip.is_global
        except ValueError:
            return False
    if kind == 'domain':
        value = indicator.lower().rstrip('.')
        if value.startswith('*.') or not DOMAIN.fullmatch(value):
            return False
        # Exclude internal/placeholder suffixes, not broad countries or providers.
        return not value.endswith(('.local', '.internal', '.test', '.invalid', '.example'))
    return False


def parse_utc(date: str) -> datetime:
    value = datetime.fromisoformat(date.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('UTC timezone required')
    return value.astimezone(timezone.utc)


def evaluate(record: dict, now: datetime) -> tuple[bool, list[str]]:
    issues = []
    kind = record.get('type')
    indicator = record.get('indicator', '')
    if not isinstance(indicator, str) or not good_indicator(str(kind), indicator):
        issues.append('Invalid, nonpublic, or too-broad domain/IP indicator')
    source = str(record.get('source_url') or '')
    uri = urlparse(source)
    if uri.scheme != 'https' or not uri.hostname or uri.username or uri.password:
        issues.append('Missing public HTTPS evidence URL')
    if record.get('approved') is not True or not str(record.get('approved_by') or '').strip():
        issues.append('Written manual approval missing')
    try:
        confidence = int(record.get('confidence'))
        if confidence < 80 or confidence > 100:
            issues.append('Confidence below 80 or above 100')
    except (ValueError, TypeError):
        issues.append('Missing numeric confidence')
    try:
        expiration = parse_utc(str(record['expires_utc']))
        if expiration <= now:
            issues.append('Indicator expired')
        if expiration > now.replace(microsecond=0) and (expiration - now).days > 30:
            issues.append('Expiry exceeds 31-day review window')
    except (ValueError, KeyError, TypeError):
        issues.append('Missing valid UTC expiry')
    return not issues, issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_json', type=Path, help='Local indicator manifest; never auto-created from feeds')
    parser.add_argument('--output', type=Path, required=True, help='Local CSV for manual import into approved defensive tools')
    args = parser.parse_args()
    try:
        rows = json.loads(args.input_json.read_text(encoding='utf-8'))
        if not isinstance(rows, list):
            raise ValueError('Manifest must be a JSON list')
        now = datetime.now(timezone.utc)
        evaluated = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Manifest entries must be JSON objects')
            passed, reasons = evaluate(row, now)
            evaluated.append({'indicator': row.get('indicator', ''), 'type': row.get('type', ''),
                              'decision': 'CANDIDATE' if passed else 'HOLD',
                              'reason': '; '.join(reasons), 'source_url': row.get('source_url', ''),
                              'expires_utc': row.get('expires_utc', '')})
        with args.output.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['indicator', 'type', 'decision', 'reason', 'source_url', 'expires_utc'])
            writer.writeheader()
            writer.writerows(evaluated)
        print(f'{sum(row["decision"] == "CANDIDATE" for row in evaluated)} of {len(evaluated)} indicators passed manual review gate. No rules deployed.')
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
