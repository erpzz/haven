"""Authoritative current checks for retrieval, admission, release and consumption.

Implements I01/I06, original R03 C/E/F plus R03-A1 and accepted P01-A1.
All functions run within a Store transaction. No process/network operation here.
"""
from __future__ import annotations
import re
import base64
from .contracts import AuthorityVector, CANONICALIZATION, PROFILE, LIMITS, Denied, canonical, digest, uid

POLICY = 'ip01.synthetic-local.v1'
PURPOSE = 'answer.v1'
RIGHTS = ['SYNTHETIC_DEMO_CONTENT_ONLY.v1']
TOOL_DIGEST = digest({'tools': [], 'external_effects': False})


def active_session(tx, session, *, permit_bootstrap=False):
    current = tx.get('sessions', session['id']) if session else None
    now = tx.store.clock()
    if not current or not current['active'] or current['expires_at'] <= now:
        raise Denied('SESSION_EXPIRED', 401)
    if current['authority_instance_epoch'] != tx.meta('authority_instance_epoch'):
        raise Denied('SESSION_EXPIRED', 401)
    if not permit_bootstrap and current['person'] not in ('A', 'B'):
        raise Denied('DEMO_LOGIN_REQUIRED', 401)
    return current


def live(tx):
    if tx.store.continuity_uncertain:
        raise Denied('CONTINUITY_UNKNOWN', 503)
    if tx.meta('review_only'):
        raise Denied('RESTORE_QUARANTINED', 409, 'Restored state is review-only; current authority has not been reconciled.')
    if tx.store.clock() < tx.meta('last_time') - 5:
        raise Denied('CLOCK_UNCERTAIN', 503)


def source_grant(tx, source, person, *, fixed=None):
    if source['owner'] == person:
        return None
    now = tx.store.clock()
    grants = [tx.get('grants', fixed)] if fixed else tx.all('grants')
    eligible = [g for g in grants if g and g['source_id'] == source['id'] and g['recipient'] == person
                and g['status'] == 'ACTIVE' and g['not_before'] <= now < g['expires_at']
                and g['purpose'] == 'answer' and g['profile'] == PROFILE
                and g['authority_instance_epoch'] == tx.meta('authority_instance_epoch')]
    if not eligible:
        raise Denied('SOURCE_UNAVAILABLE', 404)
    return sorted(eligible, key=lambda g: g['id'])[0]


def resolve_closure(tx, person, roots, *, fixed_grants=None):
    sources, grants, edges, visiting = {}, {}, set(), set()
    def visit(source_id, depth):
        if depth > LIMITS['depth']:
            raise Denied('LINEAGE_DEPTH_LIMIT', 413)
        if source_id in visiting:
            raise Denied('LINEAGE_CYCLE', 409)
        source = tx.get('sources', source_id)
        if not source or source['tombstone']:
            raise Denied('SOURCE_UNAVAILABLE', 404)
        if source_id in sources:
            return
        grant = source_grant(tx, source, person, fixed=(fixed_grants or {}).get(source_id))
        if grant:
            grants[grant['id']] = grant
        sources[source_id] = source
        if len(sources) > LIMITS['sources'] or len(grants) > LIMITS['grants']:
            raise Denied('CLOSURE_LIMIT', 413)
        visiting.add(source_id)
        for parent in source['parents']:
            edges.add((source_id, parent['id'], parent['revision']))
            if len(edges) > LIMITS['edges']:
                raise Denied('LINEAGE_EDGE_LIMIT', 413)
            current = tx.get('sources', parent['id'])
            if not current or current['revision'] != parent['revision']:
                raise Denied('STALE_LINEAGE')
            visit(parent['id'], depth + 1)
        visiting.remove(source_id)
    for root in sorted(set(roots)):
        visit(root, 0)
    return sources, grants, sorted(edges)


def make_vector(tx, session, job, sources, grants, edges):
    source_dependencies = [{k: source[k] for k in ('id', 'revision', 'sha256', 'lineage_epoch', 'authenticity_epoch')}
                           for source in sorted(sources.values(), key=lambda s: s['id'])]
    grant_dependencies = [{'id': g['id'], 'revision': g['authorization_revision'], 'revocation_epoch': g['revocation_epoch']}
                          for g in sorted(grants.values(), key=lambda g: g['id'])]
    vector = {'vector_version': 'ip01.authority.v1',
        'authority_instance_epoch': tx.meta('authority_instance_epoch'), 'restore_epoch': tx.meta('restore_epoch'),
        'policy_ref': POLICY, 'purpose_definition_ref': PURPOSE, 'rights_policy_refs': RIGHTS,
        'principal_ref': session['person'], 'session_revision': session['id'],
        'device_binding_revision': session['device_ref'], 'device_epoch': session['device_epoch'],
        'service_capability_revision': 'LOCAL_ASSISTANT.v1', 'tool_catalog_digest': TOOL_DIGEST,
        'grant_dependencies': grant_dependencies, 'source_dependencies': source_dependencies,
        'subject_scope_revision': 'SYNTHETIC_A_B.v1', 'participant_area_scope_revision': 'NOT_APPLICABLE.v1',
        'job_ref': job['job_id'], 'lease_fence': job['lease_fence'],
        'cancel_scope_epochs': [{'scope_id': job['job_id'], 'epoch': job['cancel_epoch']}],
        'destination_ref': session['destination_ref'], 'destination_epoch': session['destination_epoch'],
        'audience_revision': session['person'] + '.v1', 'route_profile_revision': 'LOCAL_BROWSER_WHOLE_OUTPUT.v1',
        'provider_data_policy_revision': 'NOT_APPLICABLE_LOCAL_ONLY',
        'dependency_closure_digest': digest({'sources': source_dependencies, 'grants': grant_dependencies, 'edges': edges}),
        'canonicalization_version': CANONICALIZATION}
    AuthorityVector.model_validate(vector)
    if len(canonical(vector).encode()) > LIMITS['metadata_bytes']:
        raise Denied('METADATA_LIMIT', 413)
    return vector


def check_current(tx, vector, *, phase, operation=None, now=None):
    live(tx)
    try:
        AuthorityVector.model_validate(vector)
    except Exception as error:
        raise Denied('INCOMPLETE_AUTHORITY_VECTOR') from error
    session = active_session(tx, tx.get('sessions', vector['session_revision']))
    job = tx.get('jobs', vector['job_ref'])
    if not job or job['owner'] != session['person'] or job['session_id'] != session['id']:
        raise Denied('JOB_UNAVAILABLE', 404)
    if len(vector['cancel_scope_epochs']) != 1 or vector['cancel_scope_epochs'][0]['scope_id'] != job['job_id']:
        raise Denied('INCOMPLETE_CANCEL_CLOSURE')
    if job['cancel_epoch'] != vector['cancel_scope_epochs'][0]['epoch'] or job['disposition'] == 'CANCELLED':
        raise Denied('CANCELLED')
    if job['lease_fence'] != vector['lease_fence']:
        raise Denied('LEASE_LOST')
    # The compute deadline governs admission/release; the separately bounded release
    # validity governs consume. A successful compute does not run during delivery.
    if phase in ('retrieval', 'admission', 'egress', 'release') and tx.store.clock() >= job['deadline_utc']:
        raise Denied('DEADLINE_EXCEEDED')
    fixed = {}
    for dep in vector['grant_dependencies']:
        grant = tx.get('grants', dep['id'])
        if not grant:
            raise Denied('AUTH_REVOKED')
        fixed[grant['source_id']] = grant['id']
    sources, grants, edges = resolve_closure(tx, session['person'], [s['id'] for s in vector['source_dependencies']], fixed_grants=fixed)
    current = make_vector(tx, session, job, sources, grants, edges)
    if canonical(current) != canonical(vector):
        raise Denied('STALE_CONTEXT')
    return {'decision': 'ELIGIBLE_AT_CHECK', 'vector': current, 'sources': sources, 'grants': grants}


STOPWORDS = frozenset('a an the what where when which who how is are was were to of for and or in on my me about tell please does do can i we with have'.split())


def words(text):
    return set(re.findall(r'[\w-]+', text.lower())) - STOPWORDS


def build_context(tx, session, request):
    live(tx)
    session = active_session(tx, session)
    job = tx.get('jobs', request['job_id'])
    query = words(request['question'])
    selected = []
    explicit = request.get('source_ids')
    if explicit is not None:
        selected = list(explicit)
    else:
        ranked = []
        for source in tx.all('sources'):
            if source['kind'] != 'note' or source['tombstone']:
                continue
            try:
                resolve_closure(tx, session['person'], [source['id']])
            except Denied:
                continue
            score = len(query & words(source['title'] + ' ' + source['text']))
            if score:
                ranked.append((score, source['id']))
        # This is explicit retrieval selection; all selected dependencies are then
        # retained without truncating authority. Unselected text never reaches worker.
        selected = [sid for _, sid in sorted(ranked, reverse=True)[:8]]
    if request.get('image_source_id'):
        selected.append(request['image_source_id'])
    sources, grants, edges = resolve_closure(tx, session['person'], selected)
    vector = make_vector(tx, session, job, sources, grants, edges)
    excerpts = []
    for sid in sorted(sources):
        source = sources[sid]
        excerpts.append({'id': sid, 'source_id': sid, 'revision': source['revision'], 'title': source['title'],
                         'text': source['text'][:4000], 'kind': source['kind'], 'selected': sid in selected,
                         'excerpt_omitted_chars': max(0, len(source['text']) - 4000)})
    context = {'question': request['question'], 'sources': excerpts, 'source_refs': sorted(sources),
               'authority_vector': vector, 'omissions': 'Up to eight relevant current notes selected; excerpts limited to 4000 characters.',
               'route': request['route'], 'image_source_id': request.get('image_source_id')}
    if len(canonical(context).encode()) > LIMITS['metadata_bytes']:
        raise Denied('METADATA_LIMIT', 413)
    if request.get('image_source_id'):
        source = sources[request['image_source_id']]
        if source['kind'] != 'image':
            raise Denied('IMAGE_SOURCE_REQUIRED', 422)
        image_bytes = (tx.store.runtime_dir / 'media' / (source['id'] + '.png')).read_bytes()
        from .contracts import raw_digest
        if raw_digest(image_bytes) != source['image']['derivative_sha256']:
            raise Denied('IMAGE_INTEGRITY_FAILED')
        context['image_base64'] = base64.b64encode(image_bytes).decode('ascii')
        context['image_sha256'] = source['image']['derivative_sha256']
        context['image_preprocessing'] = source['image']['preprocessing']
    context['context_digest'] = digest(context)
    check_current(tx, vector, phase='retrieval')
    return context


def deterministic_payload(context):
    query = words(context['question'])
    candidates = [s for s in context['sources'] if s['kind'] == 'note' and s['selected']]
    candidates.sort(key=lambda s: (-len(query & words(s['title'] + ' ' + s['text'])), s['id']))
    refs, parts = [], []
    for source in candidates[:3]:
        sentences = re.split(r'(?<=[.!?])\s+|\n+', source['text'])
        ranked = sorted(enumerate(sentences), key=lambda pair: (-len(query & words(pair[1])), pair[0]))
        excerpt = ' '.join(sentence for _, sentence in ranked[:2]).strip()[:900]
        refs.append(source['id'])
        parts.append(f"[{len(refs)}] {source['title']}: {excerpt}")
    text = '\n\n'.join(parts) if parts else 'No current eligible notes match this question. Add a note with the relevant details, or choose an eligible note explicitly.'
    if context.get('image_source_id'):
        text += '\n\nThe imported image is retained as a source. This deterministic route does not interpret image content.'
    return {'text': text, 'label': 'Deterministic source excerpts · no model inference', 'source_refs': refs,
            'limitations': 'Selected excerpts are not a synthesized or independently verified answer.'}


def binding(output):
    return {k: output[k] for k in ('output_id', 'output_digest', 'canonicalization_version', 'destination_ref',
                                   'destination_epoch', 'route_profile_revision', 'audience_revision',
                                   'release_id', 'release_sequence', 'chunk_id')}


def authorize_release(tx, candidate, *, release_key, request_digest):
    job = tx.get('jobs', candidate['job_id'])
    if not job or job['request_digest'] != candidate['request_digest']:
        raise Denied('RESULT_IDENTITY_CONFLICT')
    prior = next((r for r in tx.all('release_receipts') if r['release_key'] == release_key), None)
    if prior:
        if prior['request_digest'] != request_digest:
            raise Denied('IDEMPOTENCY_CONFLICT')
        return {'disposition': 'HISTORY_ONLY', 'release_id': prior['release_id'], 'output_id': prior['output_id']}
    context = tx.get('contexts', job['context_id'])
    if candidate['context_digest'] != context['context_digest'] or candidate['lease_fence'] != job['lease_fence'] or candidate['cancel_epoch'] != job['cancel_epoch'] or candidate['attempt_id'] != job['attempt_id']:
        raise Denied('STALE_RESULT_FENCE')
    payload = candidate['payload']
    if len(canonical(payload).encode()) > LIMITS['output_bytes']:
        raise Denied('OUTPUT_LIMIT', 413)
    output_digest = digest(payload)
    if candidate['output_digest'] != output_digest:
        raise Denied('OUTPUT_DIGEST_MISMATCH')
    if not set(candidate['source_refs']).issubset(context['source_refs']):
        raise Denied('INVALID_CITATION')
    current = check_current(tx, context['authority_vector'], phase='release')
    grants = current['grants']
    for grant in grants.values():
        ledger = tx.get('quota_ledger', grant['id'])
        if grant['max_uses'] is not None and ledger['charged_units'] >= grant['max_uses']:
            raise Denied('GRANT_QUOTA_EXHAUSTED')
    now = tx.store.clock()
    release_id, output_id = uid('release'), uid('output')
    vector = current['vector']
    expires_at = min([now + 300, tx.get('sessions', job['session_id'])['expires_at']] + [g['expires_at'] for g in grants.values()])
    output = {'output_id': output_id, 'job_id': job['job_id'], 'owner': job['owner'], 'session_id': job['session_id'],
        'payload': payload, 'output_digest': output_digest, 'canonicalization_version': CANONICALIZATION,
        'destination_ref': vector['destination_ref'], 'destination_epoch': vector['destination_epoch'],
        'route_profile_revision': vector['route_profile_revision'], 'audience_revision': vector['audience_revision'],
        'release_id': release_id, 'release_sequence': tx.sequence, 'chunk_id': 'WHOLE_OUTPUT',
        'nonce': uid('slot'), 'expires_at': expires_at, 'vector': vector, 'consumption_id': None}
    receipt = {**binding(output), 'id': release_id, 'job_id': job['job_id'], 'release_key': release_key,
        'request_digest': request_digest, 'decision': 'RELEASE_AUTHORIZED', 'at': now,
        'expires_at': expires_at, 'authority_vector': vector, 'authority_vector_digest': digest(vector),
        'profile': PROFILE, 'authorizer': 'IP01_APP_AUTHORITY'}
    for grant in sorted(grants.values(), key=lambda g: g['id']):
        if grant['max_uses'] is None:
            continue
        ledger = tx.get('quota_ledger', grant['id'])
        ledger['charged_units'] += 1
        ledger['accounting_sequence'] += 1
        tx.put('quota_ledger', grant['id'], ledger)
        claim_id = uid('claim')
        tx.put('grant_use_claims', claim_id, {**binding(output), 'id': claim_id, 'grant_id': grant['id'],
            'authorization_revision': grant['authorization_revision'], 'revocation_epoch': grant['revocation_epoch'],
            'profile': PROFILE, 'claim_units': 1, 'quota_ledger_sequence_after': ledger['accounting_sequence'],
            'charged_units_after': ledger['charged_units'], 'authority_vector': vector, 'at': now})
    tx.put('outputs', output_id, output, insert=True)
    tx.put('release_receipts', release_id, receipt)
    job.update(output_id=output_id, release_id=release_id, disposition='SUCCEEDED', error=None)
    tx.put('jobs', job['job_id'], job)
    return {'disposition': 'RELEASE_ADMITTED', 'release_id': release_id, 'output_id': output_id}


def output_for_session(tx, session, output_id):
    session = active_session(tx, session)
    output = tx.get('outputs', output_id)
    if not output or output['owner'] != session['person']:
        raise Denied('OUTPUT_UNAVAILABLE', 404)
    return output


def eligibility(tx, output):
    try:
        checked = check_current(tx, output['vector'], phase='consume')
        if tx.store.clock() >= output['expires_at']:
            raise Denied('RELEASE_EXPIRED')
        result, reason, vector = 'ELIGIBLE_AT_CHECK', None, checked['vector']
    except Denied as error:
        result, reason, vector = 'DENIED', error.code, None
    decision_id = uid('eligibility')
    decision = {**binding(output), 'id': decision_id, 'decision': result, 'reason': reason,
                'at': tx.store.clock(), 'check_sequence': tx.sequence, 'authority_vector': vector,
                'expected_vector_digest': digest(output['vector']), 'bearer_permission': False}
    tx.put('eligibility_decisions', decision_id, decision)
    return decision


def consume_output(tx, session, request):
    output = output_for_session(tx, session, request['output_id'])
    exact = ('release_id', 'output_digest', 'destination_ref', 'nonce')
    if any(request[k] != output[k] for k in exact) or session['id'] != output['session_id'] or session['destination_ref'] != output['destination_ref']:
        raise Denied('CONSUMPTION_BINDING_CONFLICT')
    old = tx.get('consumption_receipts', output['consumption_id']) if output['consumption_id'] else None
    request_digest = digest(request)
    decision = eligibility(tx, output)
    if old:
        if old['request_digest'] != request_digest:
            raise Denied('IDEMPOTENCY_CONFLICT')
        return {'status': 'HISTORY_ONLY', 'message': 'Previously consumed; reload does not replay this answer.',
                'ConsumptionPermitReceipt': public_receipt(old), 'PermitEligibilityDecision': public_receipt(decision)}
    if decision['decision'] != 'ELIGIBLE_AT_CHECK':
        # Return a denied response value, so the separate eligibility record commits.
        return {'status': 'DENIED', 'code': decision['reason'], 'PermitEligibilityDecision': public_receipt(decision)}
    # Each finite parent must have an immutable matching release claim. Zero
    # remaining quota is deliberately not a denial for this already admitted slot.
    for dep in output['vector']['grant_dependencies']:
        grant = tx.get('grants', dep['id'])
        if grant['max_uses'] is not None:
            claims = [c for c in tx.all('grant_use_claims') if c['release_id'] == output['release_id'] and c['grant_id'] == grant['id']]
            if len(claims) != 1 or claims[0]['authorization_revision'] != dep['revision'] or claims[0]['output_digest'] != output['output_digest']:
                raise Denied('CLAIM_UNAVAILABLE')
    consume_id = uid('consume')
    receipt = {**binding(output), 'id': consume_id, 'consumption_id': consume_id, 'nonce': output['nonce'],
        'session_ref': session['id'], 'device_ref': session['device_ref'], 'consumption_sequence': tx.sequence,
        'authority_vector': output['vector'], 'authority_vector_digest': digest(output['vector']),
        'request_digest': request_digest, 'operation_key': request['idempotency_key'],
        'at': tx.store.clock(), 'expires_at': output['expires_at'], 'status': 'CONSUMED'}
    tx.put('consumption_receipts', consume_id, receipt)
    output['consumption_id'] = consume_id
    tx.put('outputs', output['output_id'], output)
    observation_id = uid('observation')
    tx.put('delivery_observations', observation_id, {**binding(output), 'id': observation_id,
        'consumption_id': consume_id, 'consumption_sequence': tx.sequence, 'kind': 'DELIVERY_UNKNOWN',
        'at': tx.store.clock(), 'reporter': 'AUTHORITY', 'reason': 'Consumption committed; response delivery and display unconfirmed.',
        'authority_vector_digest': digest(output['vector'])})
    return {'status': 'FRESH_CONSUMPTION', 'payload': output['payload'], 'ConsumptionPermitReceipt': public_receipt(receipt),
            'PermitEligibilityDecision': public_receipt(decision)}


def public_receipt(receipt):
    # No source text, credentials, sealed context, or output payload in history.
    return {k: v for k, v in receipt.items() if k not in ('authority_vector', 'vector', 'payload', 'request_digest', 'release_key')}


def receipts(tx, session, output_id):
    output = output_for_session(tx, session, output_id)
    decision = eligibility(tx, output)
    return {'ReleaseAuthorizationReceipt': public_receipt(tx.get('release_receipts', output['release_id'])),
            'ConsumptionPermitReceipt': public_receipt(tx.get('consumption_receipts', output['consumption_id'])) if output['consumption_id'] else None,
            'DeliveryObservation': [public_receipt(r) for r in tx.all('delivery_observations') if r['release_id'] == output['release_id']],
            'PermitEligibilityDecision': public_receipt(decision),
            'message': 'Historical receipts cannot replay an answer. A display report does not prove human perception.'}
