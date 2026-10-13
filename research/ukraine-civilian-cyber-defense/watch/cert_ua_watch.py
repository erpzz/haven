#!/usr/bin/env python3
"""CERT-UA advisory change detector. Official RSS only; no target probing.

Detections below are high-level suggested defensive reviews, NOT verified IOCs.
Reads RSS locally by default. --fetch explicitly retrieves cert.gov.ua official feed.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

SOURCE = 'https://cert.gov.ua/api/articles/rss'
MAX_BYTES = 2_000_000
USER_AGENT = 'UkraineCivilianDefense-CERTUA-Watch/0.1 (+public RSS only)'
RULES = [
    (re.compile(r'clickfix|cloudflare|перевірк[аи] люд', re.I),
     'Social engineering / ClickFix', 'Review endpoint script execution and user-reported fake verification prompts.'),
    (re.compile(r'фішинг|phish|поштов|електронн.{0,12}лист', re.I),
     'Email-origin threats', 'Review recent suspicious messages, authentication events and attachment execution.'),
    (re.compile(r'power(?:shell)?|powershell|скрипт|script|vbs|vbe|bat-файл', re.I),
     'Script execution', 'Review suspicious script host invocations and new scheduled-task persistence.'),
    (re.compile(r'викраден|крадіжк|stealer|credential|обліков.{0,10}дан', re.I),
     'Credential exposure', 'Review suspicious sign-ins, session revocations and MFA method changes.'),
    (re.compile(r'шифрувал|ransomware|вимагач', re.I),
     'Ransomware', 'Confirm recoverable, isolated backups and investigate suspicious file-encryption activity.'),
]


def clean_text(value: str | None, limit: int = 900) -> str:
    """Strip markup to prevent injecting arbitrary feed HTML into Markdown output."""
    unescaped = html.unescape(value or '')
    removed = re.sub(r'<[^>]*>', ' ', unescaped)
    return re.sub(r'\s+', ' ', removed).strip()[:limit]


def cert_url(raw: str | None) -> str | None:
    if not raw:
        return None
    url = raw.strip()
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'cert.gov.ua' or parsed.username or parsed.password or parsed.port:
        return None
    if not re.fullmatch(r'/articles?/\d+/?', parsed.path):
        return None
    if any(char in url for char in ('\n', '\r', '<', '>', '|')):
        return None
    return url


def iso_date(raw: str | None) -> str:
    if not raw:
        return ''
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except (TypeError, ValueError, IndexError):
        return ''


def parse_rss(payload: bytes) -> list[dict[str, object]]:
    if len(payload) > MAX_BYTES:
        raise ValueError('Feed exceeds maximum allowed size')
    root = ET.fromstring(payload)
    if root.tag != 'rss':
        raise ValueError('Expected official RSS 2.0 XML; Atom not supported')
    items = []
    seen = set()
    for entry in root.findall('./channel/item'):
        url = cert_url(entry.findtext('link'))
        if not url or url in seen:
            continue
        seen.add(url)
        title = clean_text(entry.findtext('title'), 200) or 'Untitled CERT-UA advisory'
        description = clean_text(entry.findtext('description'), 450)
        published = iso_date(entry.findtext('pubDate'))
        text = title + ' ' + description
        suggestions = [{"category": category, "review": action} for pattern, category, action in RULES if pattern.search(text)]
        items.append({'title': title, 'url': url, 'published_utc': published,
                      'summary': description, 'review_suggestions': suggestions,
                      'source': SOURCE})
    return sorted(items, key=lambda i: (i['published_utc'], i['url']), reverse=True)


def fetch_official_feed() -> bytes:
    req = urllib.request.Request(SOURCE, headers={'User-Agent': USER_AGENT})
    # No redirects, so an upstream redirect never results in contacting another host.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError('Redirect not allowed for the official feed')
    opener = urllib.request.build_opener(NoRedirect)
    with opener.open(req, timeout=15) as response:
        size = response.headers.get('Content-Length')
        if size and int(size) > MAX_BYTES:
            raise ValueError('Feed exceeds maximum allowed size')
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError('Feed exceeds maximum allowed size')
    return payload


def update_state(items: list[dict], old: dict | None) -> tuple[dict, list[dict], bool]:
    baseline = old is None
    known = set(old.get('seen_urls', []) if old else [])
    newly_found = [] if baseline else [row for row in items if row['url'] not in known]
    all_urls = list(dict.fromkeys([row['url'] for row in items] + (old.get('seen_urls', []) if old else [])))[:1500]
    return {'schema': 1, 'source': SOURCE, 'seen_urls': all_urls}, newly_found, baseline


def markdown_brief(items: list[dict], new: list[dict], baseline: bool) -> str:
    result = ['# CERT-UA Advisory Watch', '',
              'Official public reports only. No endpoint scanning, live infrastructure interaction, or automatic blocking.', '',
              '**Status:** ' + ('Initial baseline; no new-alert claims.' if baseline else f'{len(new)} new advisory(ies) since last run.'), '',
              '## Newly observed advisories', '']
    if not new:
        result.append('_None detected. Initial runs baseline without sending false new alerts._' if baseline else '_No newly published feed items._')
    for row in new:
        title = row['title'].replace('[', r'\[').replace(']', r'\]').replace('*', r'\*')
        result.extend([f'### [{title}]({row["url"]})', '',
                       f'Date: {row["published_utc"] or "Not provided"}', '',
                       row['summary'].replace('[', r'\[').replace(']', r'\]'), ''])
        for item in row['review_suggestions']:
            result.append(f'- **Possible topic: {item["category"]}.** {item["review"]}')
        if row['review_suggestions']:
            result.append('')
    result.extend(['## Operational handling', '',
                   '- Confirm reporting and attribution from the original advisory before using it to make security decisions.',
                   '- Treat keyword-derived review suggestions as analyst prompts, not validated detections.',
                   '- Do **not** block broad countries, ASNs, cloud providers or domains without vetted, current evidence.',
                   '- Preserve source links and dates; request authorization before collecting endpoint data or deploying controls.',
                   '', f'Source: {SOURCE}', ''])
    return '\n'.join(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    feed = parser.add_mutually_exclusive_group(required=True)
    feed.add_argument('--rss-file', type=Path, help='Use a saved local RSS file (no network)')
    feed.add_argument('--fetch', action='store_true', help='Fetch official CERT-UA RSS via HTTPS')
    parser.add_argument('--state', required=True, type=Path, help='Local persisted JSON state')
    parser.add_argument('--output-dir', required=True, type=Path, help='Existing local results directory')
    args = parser.parse_args(argv)
    if not args.output_dir.is_dir():
        parser.error('--output-dir must already exist')
    try:
        raw = fetch_official_feed() if args.fetch else args.rss_file.read_bytes()
        items = parse_rss(raw)
        if not items:
            raise ValueError('Official RSS had no valid linked items; refusing to change state')
        old = json.loads(args.state.read_text(encoding='utf-8')) if args.state.exists() else None
        if old is not None and (old.get('schema') != 1 or old.get('source') != SOURCE or not isinstance(old.get('seen_urls'), list)):
            raise ValueError('State schema/source not recognized')
        new_state, new_items, baseline = update_state(items, old)
        outputs = {
            args.state: json.dumps(new_state, ensure_ascii=False, indent=2) + '\n',
            args.output_dir / 'latest_advisories.json': json.dumps(items, ensure_ascii=False, indent=2) + '\n',
            args.output_dir / 'new_advisories.json': json.dumps(new_items, ensure_ascii=False, indent=2) + '\n',
            args.output_dir / 'defense_brief.md': markdown_brief(items, new_items, baseline),
        }
        for destination, value in outputs.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(value, encoding='utf-8')
        print(json.dumps({'status': 'baseline' if baseline else 'update', 'feed_items': len(items), 'new_items': len(new_items)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, ET.ParseError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f'Feed processing failed; do not treat as an all-clear: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
