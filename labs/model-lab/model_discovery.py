"""Bounded public Hugging Face metadata discovery. Never downloads or runs models."""
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}')
QUANTS = ('Q2_K', 'Q3_K_M', 'Q4_0', 'Q4_K_M', 'Q5_K_M', 'Q6_K', 'Q8_0', 'F16', 'BF16')
_slots = threading.BoundedSemaphore(2)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Metadata redirect refused; no credentials or downloads are used.')


def fetch(path, params):
    url = 'https://huggingface.co/api/models' + path + '?' + urllib.parse.urlencode(params)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    if not _slots.acquire(blocking=False):
        raise ValueError('Discovery is busy. Try again after the current metadata request finishes.')
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'Haven-Metadata-Discovery/0.1'})
        with opener.open(req, timeout=10) as response:
            raw = response.read(2 * 1024**2 + 1)
        if len(raw) > 2 * 1024**2:
            raise ValueError('Metadata exceeds the discovery size bound.')
        return json.loads(raw)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ValueError('Hugging Face metadata is unavailable; no download or inference was attempted.') from error
    finally:
        _slots.release()


def clean(value, limit=200):
    return value[:limit] if isinstance(value, str) else None


def summary(row):
    ident = row.get('id') or row.get('modelId')
    if not isinstance(ident, str) or not REPO.fullmatch(ident):
        return None
    card = row.get('cardData') or {}
    if not isinstance(card, dict): card = {}
    return {'repo': ident, 'revision': clean(row.get('sha'), 64), 'task': clean(row.get('pipeline_tag')),
            'library': clean(row.get('library_name')), 'license': clean(card.get('license')) or 'UNKNOWN_REVIEW_CARD',
            'gated': row.get('gated', 'UNKNOWN'), 'stage': 'DISCOVERABLE',
            'compatibility': 'UNVERIFIED', 'qualification': 'NOT_HAVEN_QUALIFIED',
            'source': 'https://huggingface.co/' + ident}


def search(data):
    if set(data) - {'query', 'author', 'task', 'format'}:
        raise ValueError('Unknown discovery field. URLs, tokens and commands are not accepted.')
    query = data.get('query', '')
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 100 or any(ord(c) < 32 for c in query):
        raise ValueError('Enter 2–100 characters of public model name. Do not enter private text.')
    author, task, format_ = data.get('author', ''), data.get('task', ''), data.get('format', 'gguf')
    if not isinstance(author, str) or author and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}', author):
        raise ValueError('Invalid publisher filter.')
    if task not in ('', 'text-generation', 'image-text-to-text') or format_ not in ('', 'gguf', 'mlx'):
        raise ValueError('Unsupported task or format filter.')
    params = {'search': query.strip(), 'limit': 12, 'full': 'true', 'config': 'false'}
    if author: params['author'] = author
    if task: params['pipeline_tag'] = task
    if format_: params['filter'] = format_
    raw = fetch('', params)
    if not isinstance(raw, list): raise ValueError('Unexpected model-search response.')
    models = [item for item in (summary(r) for r in raw[:12] if isinstance(r, dict)) if item]
    return {'models': models, 'captured_at': time.time(), 'network': 'PUBLIC_METADATA_ONLY',
            'notice': 'Search terms go to Hugging Face. Results do not establish runtime compatibility or permission to install.'}


def detail(data):
    if set(data) != {'repo'} or not isinstance(data['repo'], str) or not REPO.fullmatch(data['repo']):
        raise ValueError('Use one publisher/model identifier; arbitrary URLs and paths are not accepted.')
    raw = fetch('/' + data['repo'], {'blobs': 'true'})
    if not isinstance(raw, dict): raise ValueError('Unexpected model-detail response.')
    model = summary(raw)
    if not model or model['repo'] != data['repo']: raise ValueError('Repository identity mismatch.')
    revision = model['revision']
    pinned = bool(revision and re.fullmatch(r'[0-9a-f]{40}', revision))
    files = []
    for entry in raw.get('siblings', [])[:2000]:
        if not isinstance(entry, dict): continue
        name = entry.get('rfilename', '')
        if not isinstance(name, str) or len(name) > 250 or '\\' in name or any(p in ('..', '') for p in name.split('/')): continue
        if not name.lower().endswith(('.gguf', '.safetensors')): continue
        lfs = entry.get('lfs') or {}; digest = lfs.get('sha256') if isinstance(lfs, dict) else None
        size = entry.get('size') or (lfs.get('size') if isinstance(lfs, dict) else None)
        valid = bool(pinned and isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest) and type(size) is int and size > 0)
        files.append({'filename': name, 'size_bytes': size if type(size) is int and size > 0 else None,
                      'sha256': digest if valid else None, 'quantization': next((q for q in QUANTS if q in name.upper()), 'UNKNOWN'),
                      'integrity': 'PINNED_LFS_METADATA' if valid else 'UNVERIFIED',
                      'format': 'GGUF' if name.lower().endswith('.gguf') else 'SAFETENSORS'})
        if len(files) >= 80: break
    return {'model': model, 'files': files, 'captured_at': time.time(), 'installation': 'REVIEW_REQUIRED',
            'notice': 'Metadata only. No files fetched. A digest is publisher metadata until the downloaded artifact is hashed. Safetensors does not imply MLX compatibility. Use the prepared catalog for bounded checksum-verified installation; other artifacts need runtime/license review.'}
