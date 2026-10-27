"""Select OSV advisories that name a concrete GitHub fix commit.

Input is the OSV.dev ecosystem export (e.g. PyPI/all.zip). GHSA and PyPA
(PYSEC) records are CC-BY-4.0; each candidate keeps its record ids, source
database, modified time and the archive digest so attribution survives every
later stage. Advisories describing the same vulnerability (shared aliases) or
the same commit collapse into one candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import zipfile

COMMIT_RE = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/commit/([0-9a-f]{7,40})/?$')
ADVISORY_LICENSE = {'GHSA': 'CC-BY-4.0', 'PYSEC': 'CC-BY-4.0'}


def fix_commits(record: dict) -> list[tuple[str, str]]:
    """(owner/repo, sha) pairs from FIX references, falling back to any commit reference."""
    refs = record.get('references') or []
    ranked = sorted(refs, key=lambda r: r.get('type') != 'FIX')
    out = []
    for ref in ranked:
        m = COMMIT_RE.match(ref.get('url', ''))
        if m:
            pair = (f'{m[1]}/{m[2]}'.lower().removesuffix('.git'), m[3])
            if pair not in out:
                out.append(pair)
    return out


def cwes(record: dict) -> list[str]:
    found = set((record.get('database_specific') or {}).get('cwe_ids') or [])
    return sorted(c for c in found if re.fullmatch(r'CWE-\d{1,5}', c))


def candidates(archive: pathlib.Path) -> list[dict]:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    groups: dict[str, dict] = {}
    alias_of: dict[str, str] = {}
    with zipfile.ZipFile(archive) as z:
        for name in sorted(z.namelist()):
            rec = json.loads(z.read(name))
            source = rec['id'].split('-')[0]
            if source not in ADVISORY_LICENSE or rec.get('withdrawn'):
                continue  # MAL-* (malicious packages) carry no fix; unknown sources have no license record.
            commits = fix_commits(rec)
            if not commits:
                continue
            names = {rec['id'], *(rec.get('aliases') or [])}
            key = next((alias_of[n] for n in names if n in alias_of), None) or rec['id']
            row = groups.setdefault(key, {'key': key, 'advisories': [], 'commits': [], 'cwes': set(),
                                          'published': rec.get('published', ''), 'summary': '', 'details': ''})
            for n in names:
                alias_of[n] = key
            row['advisories'].append({'id': rec['id'], 'source_db': source, 'license': ADVISORY_LICENSE[source],
                                      'modified': rec.get('modified'), 'aliases': sorted(rec.get('aliases') or [])})
            row['cwes'].update(cwes(rec))
            row['published'] = min(filter(None, [row['published'], rec.get('published', '')]))
            # GHSA text is usually the more specific description; keep the longest summary and details seen.
            if len(rec.get('summary') or '') > len(row['summary']):
                row['summary'] = rec['summary']
            if len(rec.get('details') or '') > len(row['details']):
                row['details'] = rec['details']
            for c in commits:
                if c not in row['commits']:
                    row['commits'].append(c)
    out, seen_commit = [], set()
    for row in groups.values():
        repo, sha = row['commits'][0]
        if (repo, sha[:12]) in seen_commit:
            continue
        seen_commit.add((repo, sha[:12]))
        out.append({**row, 'cwes': sorted(row['cwes']), 'repo': repo, 'commit': sha,
                    'other_commits': [f'{r}@{s}' for r, s in row['commits'][1:]],
                    'osv_archive_sha256': digest})
    return sorted(out, key=lambda r: (r['published'], r['key']))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    args = ap.parse_args(argv)
    rows = candidates(args.archive)
    with args.out.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(json.dumps({'candidates': len(rows), 'repos': len({r['repo'] for r in rows}), 'out': str(args.out)}))


if __name__ == '__main__':
    main()
