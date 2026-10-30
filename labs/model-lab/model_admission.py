"""Staged, evidence-based model admission for the Haven Model Lab.

A model card, a downloaded file, a runtime that can parse it, a loaded process and a
completed inference are different facts. This module reports which of them are true for
each model, and never promotes a later stage from an earlier one:

  CATALOGED            pinned in catalog.json (revision, SHA-256, license, source)
  ARTIFACT_PRESENT     the file exists, its GGUF header parses and its architecture
                       matches the catalog's declared architecture
  RUNTIME_COMPATIBLE   the installed pinned llama.cpp build is at least the build that
                       added this architecture (catalog runtime.min_build)
  LOADABLE             compatible AND a chat interface the Lab's managed engine serves;
                       memory fit is still checked at load time, not here
  LOADED               the Lab currently owns an engine serving this exact SHA-256
  VERIFIED_BY_INFERENCE  a COMPLETED, non-test-double receipt for this exact SHA-256 is
                       in this Lab's own benchmarks.jsonl

Blocking codes explain where the ladder stops: ARTIFACT_MISSING, ARTIFACT_MISMATCH,
ARTIFACT_UNREADABLE, ENGINE_NOT_INSTALLED, UNVERIFIED_MODEL_RUNTIME and NOT_CHAT_MODEL.
Catalog `verification` entries are recorded receipts from named hosts (for example an
off-host CPU container). They are shown as provenance and never count as local
VERIFIED_BY_INFERENCE.

Standard library only; reads at most HEADER_LIMIT bytes of a GGUF file.
"""
from __future__ import annotations

from pathlib import Path
import re
import struct

CONTRACT = 'haven.model-capability/v1'
STAGES = ('CATALOGED', 'ARTIFACT_PRESENT', 'RUNTIME_COMPATIBLE', 'LOADABLE', 'LOADED',
          'VERIFIED_BY_INFERENCE')
INTERFACES = ('chat', 'systemone')
ROLES = ('general_chat', 'tool_agent', 'coding', 'reasoning', 'decision', 'routing',
         'classification', 'guardrail', 'extraction', 'reranking', 'vision', 'audio')
EVIDENCE = ('measured_on_slink', 'measured_off_host', 'vendor_claim', 'unsupported_by_runtime',
            'not_supported')
# Only measured evidence may drive an automatic decision; vendor claims are display-only.
TRUSTED_EVIDENCE = ('measured_on_slink', 'measured_off_host')
SYSTEMONE_QUESTION_TYPES = ('noul', 'choice', 'score')
HEADER_LIMIT = 32 * 1024 * 1024
_TAG = re.compile(r'^b(\d+)$')
_GGUF_SCALAR = {0: '<B', 1: '<b', 2: '<H', 3: '<h', 4: '<I', 5: '<i', 6: '<f', 7: '<?',
                10: '<Q', 11: '<q', 12: '<d'}


def build_number(tag) -> int | None:
    """'b11146' -> 11146. Anything else is unknown, never zero."""
    m = _TAG.match(str(tag or ''))
    return int(m.group(1)) if m else None


class GGUFHeaderError(ValueError):
    pass


def read_gguf_metadata(path: Path, limit: int = HEADER_LIMIT) -> dict:
    """Parse the GGUF key/value header only (no tensors, no weights).

    Large arrays (tokenizer vocabularies) are skipped, not materialized.
    """
    with Path(path).open('rb') as f:
        data = f.read(limit)
    pos = 0

    def take(n):
        nonlocal pos
        if pos + n > len(data):
            raise GGUFHeaderError('GGUF header is truncated or larger than the read limit.')
        chunk = data[pos:pos + n]
        pos += n
        return chunk

    def scalar(code):
        fmt = _GGUF_SCALAR[code]
        return struct.unpack(fmt, take(struct.calcsize(fmt)))[0]

    def string():
        n = scalar(10)
        if n > 1 << 20:
            raise GGUFHeaderError('GGUF string is implausibly long.')
        return take(n).decode('utf-8', 'replace')

    def value(code, depth=0):
        if code == 8:
            return string()
        if code == 9:
            if depth:
                raise GGUFHeaderError('Nested GGUF arrays are not expected in model metadata.')
            inner, count = scalar(4), scalar(10)
            if count > 64:  # skip vocabularies and merges without keeping them
                for _ in range(count):
                    value(inner, depth + 1)
                return {'array_of': count}
            return [value(inner, depth + 1) for _ in range(count)]
        if code not in _GGUF_SCALAR:
            raise GGUFHeaderError(f'Unknown GGUF value type {code}.')
        return scalar(code)

    if take(4) != b'GGUF':
        raise GGUFHeaderError('Not a GGUF file.')
    version = scalar(4)
    if version not in (2, 3):
        raise GGUFHeaderError(f'Unsupported GGUF version {version}.')
    scalar(10)  # tensor count
    pairs = scalar(10)
    if pairs > 100_000:
        raise GGUFHeaderError('Implausible GGUF metadata count.')
    meta = {}
    for _ in range(pairs):
        key = string()
        meta[key] = value(scalar(4))
    return meta


def artifact_facts(meta: dict) -> dict:
    """The few header facts admission needs, without trusting free-text fields."""
    arch = meta.get('general.architecture')
    if not isinstance(arch, str):
        raise GGUFHeaderError('GGUF header has no general.architecture.')
    decision = meta.get(f'{arch}.decision.type')
    ctx = meta.get(f'{arch}.context_length')
    return {'architecture': arch,
            'decision_type': decision if isinstance(decision, str) else None,
            'context_length': ctx if isinstance(ctx, int) else None,
            'license': meta.get('general.license.name') or meta.get('general.license')}


_HEADER_CACHE: dict = {}


def cached_artifact_facts(path: Path) -> dict:
    p = Path(path)
    st = p.stat()
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key not in _HEADER_CACHE:
        if len(_HEADER_CACHE) > 64:
            _HEADER_CACHE.clear()
        try:  # most headers fit in 4 MiB; large tokenizers need the full bounded read
            meta = read_gguf_metadata(p, 4 * 1024 * 1024)
        except GGUFHeaderError as error:
            if 'truncated' not in str(error):
                raise
            meta = read_gguf_metadata(p)
        _HEADER_CACHE[key] = artifact_facts(meta)
    return dict(_HEADER_CACHE[key])


def validate_entry(entry: dict) -> list[str]:
    """Problems with the capability contract of one catalog entry ([] when valid).

    Fields are optional for older entries, but anything present must be well formed so
    a router can rely on it.
    """
    problems = []
    mid = entry.get('id', '?')
    if 'architecture' in entry and not (isinstance(entry['architecture'], str) and entry['architecture']):
        problems.append(f'{mid}: architecture must be the GGUF general.architecture string')
    interface = entry.get('interface', 'chat')
    if interface not in INTERFACES:
        problems.append(f'{mid}: interface {interface!r} not in {INTERFACES}')
    for role in entry.get('roles', []):
        if role not in ROLES:
            problems.append(f'{mid}: unknown role {role!r}')
    caps = entry.get('capabilities', {})
    if not isinstance(caps, dict):
        problems.append(f'{mid}: capabilities must map capability -> evidence')
    else:
        for cap, ev in caps.items():
            if ev not in EVIDENCE:
                problems.append(f'{mid}: capability {cap} has unknown evidence {ev!r}')
    runtime = entry.get('runtime')
    if runtime is not None:
        if not isinstance(runtime, dict) or runtime.get('backend') != 'llama.cpp':
            problems.append(f'{mid}: runtime.backend must be llama.cpp')
        elif runtime.get('min_build') is not None and not isinstance(runtime['min_build'], int):
            problems.append(f'{mid}: runtime.min_build must be an integer llama.cpp build')
        if interface == 'systemone':
            qt = (runtime or {}).get('question_types') or []
            if not qt or any(q not in SYSTEMONE_QUESTION_TYPES for q in qt):
                problems.append(f'{mid}: systemone runtime.question_types must be a subset of {SYSTEMONE_QUESTION_TYPES}')
    elif interface == 'systemone':
        problems.append(f'{mid}: a systemone model must declare its runtime')
    for receipt in entry.get('verification', []):
        if not isinstance(receipt, dict) or not {'where', 'runtime_build', 'evidence'} <= set(receipt):
            problems.append(f'{mid}: verification receipts need where, runtime_build and evidence')
        elif receipt['evidence'] not in TRUSTED_EVIDENCE:
            problems.append(f'{mid}: a verification receipt must be measured, not {receipt["evidence"]!r}')
    explanation = entry.get('explanation')
    if explanation is not None:
        if not isinstance(explanation, dict) or set(explanation) != {'why', 'can', 'cannot'} \
                or not all(isinstance(v, str) and v.strip() for v in explanation.values()):
            problems.append(f'{mid}: explanation needs non-empty why, can and cannot text')
    if (entry.get('roles') or entry.get('capabilities')) and not entry.get('architecture'):
        problems.append(f'{mid}: capability metadata requires the GGUF architecture it describes')
    return problems


def router_view(entry: dict, admission: dict) -> dict:
    """The only fields a router may rely on (contract haven.model-capability/v1).

    Capabilities backed by vendor claims are reported but flagged untrusted; a router must
    not route on them automatically. `usable_now` is true only for a model at LOADED or
    later on this Lab; everything else is planning information.
    """
    caps = entry.get('capabilities') or {}
    return {'contract': CONTRACT, 'id': entry.get('id'), 'interface': entry.get('interface', 'chat'),
            'architecture': entry.get('architecture'), 'roles': list(entry.get('roles') or []),
            'trusted_capabilities': sorted(c for c, ev in caps.items() if ev in TRUSTED_EVIDENCE),
            'untrusted_capabilities': sorted(c for c, ev in caps.items() if ev not in TRUSTED_EVIDENCE),
            'runtime_min_build': (entry.get('runtime') or {}).get('min_build'),
            'stage': admission.get('stage'), 'blocked': admission.get('blocked'),
            'usable_now': admission.get('stage') in ('LOADED', 'VERIFIED_BY_INFERENCE')}


def local_receipt_count(records: list[dict], sha256: str | None) -> int:
    """COMPLETED, non-test-double inference receipts for this exact artifact, produced by
    this Lab's own managed engine. Worker or cloud-lane receipts prove another process ran
    a file with that hash; they do not prove this Lab's engine serves it."""
    if not sha256:
        return 0
    return sum(1 for r in records
               if isinstance(r, dict) and r.get('model_sha256') == sha256
               and r.get('state') == 'COMPLETED' and r.get('test_double') is False
               and r.get('provider_id', 'managed') == 'managed')


def assess(entry: dict, *, artifact_path=None, engine_tag=None, engine_installed=False,
           loaded_sha256=None, receipts=()) -> dict:
    """Admission ladder for one catalog entry. Pure apart from reading the GGUF header."""
    interface = entry.get('interface', 'chat')
    checks = [{'stage': 'CATALOGED', 'ok': True,
               'detail': 'Pinned revision and SHA-256 in the catalog.' if entry.get('sha256')
               else 'Catalog entry without a pinned SHA-256.'}]
    result = {'contract': CONTRACT, 'stage': 'CATALOGED', 'blocked': None, 'interface': interface,
              'chat_loadable': False, 'checks': checks,
              'recorded_receipts': [dict(r) for r in entry.get('verification', [])]}

    def stop(code, detail):
        result['blocked'] = code
        result['reason'] = detail
        return result

    # 1. artifact
    if not artifact_path or not Path(artifact_path).is_file():
        checks.append({'stage': 'ARTIFACT_PRESENT', 'ok': False, 'detail': 'Not downloaded.'})
        return stop('ARTIFACT_MISSING', 'The pinned file is not on this host.')
    try:
        facts = cached_artifact_facts(Path(artifact_path))
    except (OSError, GGUFHeaderError) as error:
        checks.append({'stage': 'ARTIFACT_PRESENT', 'ok': False, 'detail': str(error)[:200]})
        return stop('ARTIFACT_UNREADABLE', 'The file exists but its GGUF header could not be read.')
    result['artifact'] = facts
    declared = entry.get('architecture')
    if declared and facts['architecture'] != declared:
        checks.append({'stage': 'ARTIFACT_PRESENT', 'ok': False,
                       'detail': f"Header architecture {facts['architecture']!r}, catalog declares {declared!r}."})
        return stop('ARTIFACT_MISMATCH', 'The file on disk is not the architecture the catalog describes.')
    if interface == 'chat' and facts['decision_type']:
        checks.append({'stage': 'ARTIFACT_PRESENT', 'ok': False,
                       'detail': f"Header declares decision model {facts['decision_type']!r}; the catalog entry says chat."})
        return stop('ARTIFACT_MISMATCH', 'The file is a decision model, not a chat model.')
    if interface == 'systemone' and not facts['decision_type']:
        checks.append({'stage': 'ARTIFACT_PRESENT', 'ok': False,
                       'detail': 'Catalog says decision model; header has no <arch>.decision.type.'})
        return stop('ARTIFACT_MISMATCH', 'The file does not carry decision-model metadata.')
    checks.append({'stage': 'ARTIFACT_PRESENT', 'ok': True,
                   'detail': f"GGUF header architecture {facts['architecture']}"
                             + (f", decision type {facts['decision_type']}" if facts['decision_type'] else '')
                             + '. SHA-256 was verified when the Lab downloaded it.'})
    result['stage'] = 'ARTIFACT_PRESENT'

    # 2. runtime
    if not engine_installed:
        checks.append({'stage': 'RUNTIME_COMPATIBLE', 'ok': False, 'detail': 'No pinned llama.cpp engine installed.'})
        return stop('ENGINE_NOT_INSTALLED', 'Install the pinned engine first.')
    have = build_number(engine_tag)
    need = (entry.get('runtime') or {}).get('min_build')
    if need is not None and (have is None or have < need):
        checks.append({'stage': 'RUNTIME_COMPATIBLE', 'ok': False,
                       'detail': f'Needs llama.cpp b{need} or newer; the installed pinned engine is '
                                 f'{engine_tag or "unknown"}.'})
        return stop('UNVERIFIED_MODEL_RUNTIME',
                    f'The installed llama.cpp {engine_tag or "build"} predates b{need}, which added this '
                    'architecture. The Lab will not try to load it; a newer pinned engine must be '
                    'installed and verified first.')
    checks.append({'stage': 'RUNTIME_COMPATIBLE', 'ok': True,
                   'detail': (f'Installed engine {engine_tag} meets the catalog requirement (b{need}+).' if need
                              else f'No minimum build declared; this entry predates the capability contract '
                                   f'and was cataloged for the pinned {engine_tag}. Loading is the real test.')})
    result['stage'] = 'RUNTIME_COMPATIBLE'

    # 3. interface
    if interface != 'chat':
        checks.append({'stage': 'LOADABLE', 'ok': False,
                       'detail': f'{interface} model: answers typed questions in one forward pass; '
                                 'it is not a chat model and the managed chat engine does not serve it.'})
        return stop('NOT_CHAT_MODEL', 'Decision specialists are served on their own endpoint, not in chat.')
    checks.append({'stage': 'LOADABLE', 'ok': True, 'detail': 'Chat model; memory fit is checked when you load it.'})
    result['stage'] = 'LOADABLE'
    result['chat_loadable'] = True

    # 4. loaded
    sha = entry.get('sha256')
    if not (sha and loaded_sha256 == sha):
        checks.append({'stage': 'LOADED', 'ok': False, 'detail': 'Not the model the Lab currently serves.'})
        return result
    checks.append({'stage': 'LOADED', 'ok': True, 'detail': 'The Lab-owned engine serves this exact SHA-256.'})
    result['stage'] = 'LOADED'

    # 5. verified by a local receipt
    n = local_receipt_count(list(receipts), sha)
    checks.append({'stage': 'VERIFIED_BY_INFERENCE', 'ok': n > 0,
                   'detail': f'{n} completed local benchmark receipt(s) for this SHA-256.' if n
                   else 'No completed local benchmark receipt for this SHA-256 yet; run a benchmark.'})
    if n:
        result['stage'] = 'VERIFIED_BY_INFERENCE'
    return result


def file_refusal(path) -> str | None:
    """Refuse a decision-model GGUF in the chat engine, whether cataloged or user-imported.

    A header that cannot be parsed is not a refusal: llama-server stays the judge of
    malformed files, as before this contract existed.
    """
    try:
        facts = cached_artifact_facts(Path(path))
    except (OSError, GGUFHeaderError):
        return None
    if facts['decision_type']:
        return (f"This file is a {facts['decision_type']} decision model, not a chat model. "
                'Nothing was loaded.')
    return None


def load_refusal(entry: dict, engine_tag) -> str | None:
    """Why the managed chat engine must not start this catalog model, or None."""
    if not entry:
        return None
    interface = entry.get('interface', 'chat')
    if interface != 'chat':
        return (f"{entry.get('name', entry.get('id'))} is a {interface} decision model, not a chat model. "
                'Nothing was loaded.')
    need = (entry.get('runtime') or {}).get('min_build')
    have = build_number(engine_tag)
    if need is not None and (have is None or have < need):
        return (f"{entry.get('name', entry.get('id'))} needs llama.cpp b{need} or newer; the installed "
                f'pinned engine is {engine_tag or "unknown"}. Nothing was loaded.')
    return None
