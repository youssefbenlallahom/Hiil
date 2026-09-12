"""Explainable, deterministic preparation checks. No probability of legal acceptance."""
import hashlib
import json

from backend.rne_knowledge import LABELS, field_error
from backend.rne_models import RneState
from backend.sources import normalize

ENGINE_VERSION = 'f005-evidence-1.1'

DOCUMENT_ROLES = {
    'registry': 'extrait de registre (état actuel)',
    'decision': 'décision de transfert (changement proposé)',
    'declaration': 'déclaration de modification (intention)',
    'other': 'document complémentaire',
}


def fingerprint(case):
    """Content signature; chatting and view events do not alter the submitted content."""
    state = RneState.model_validate(case['rne'])
    content = {'version': ENGINE_VERSION, 'modification': state.modification,
        'confirmed': state.modification_confirmed,
        'values': {k: v.model_dump() for k, v in state.values.items()},
        'cin': state.cin_document_id,
        'documents': [{k: d.get(k) for k in ('id', 'kind', 'fields', 'pages', 'purpose')} for d in case['documents']]}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def document_evidence(case, key):
    results = []
    for doc in case['documents']:
        if doc.get('purpose') == 'rne_cin':
            continue
        for fact in doc['fields']:
            if fact['key'] != key:
                continue
            page = next((p for p in doc['pages'] if p['page'] == fact['page']), None)
            quote, value = normalize(fact['evidence']), normalize(fact['value'])
            verified = bool(page and quote and value and quote in normalize(page['text']) and value in quote)
            results.append({**fact, 'document_id': doc['id'], 'document_name': doc['name'],
                'kind': doc['kind'], 'sample': doc['sample'], 'passage_verified': verified})
    return results


def report(case):
    state = RneState.model_validate(case['rne'])
    rows = []
    for key, label in LABELS.items():
        fact = state.values.get(key)
        evidence = []
        for source in fact.evidence if fact else []:
            doc = next((d for d in case['documents'] if d['id'] == source.reference_id), None)
            page = next((p for p in doc['pages'] if p['page'] == source.page), None) if doc else None
            verified = bool(page and source.quote.strip() and normalize(source.quote) in normalize(page['text']))
            evidence.append({**source.model_dump(), 'document_name': doc['name'] if doc else None, 'passage_verified': verified})
        status = 'missing' if not fact else 'attention' if field_error(key, fact.value) else 'confirmed' if fact.confirmed else 'review'
        source_type = 'document' if any(e['origin'] == 'document' for e in evidence) else 'declaration' if evidence else 'none'
        broken = any(e['origin'] == 'document' and not e['passage_verified'] for e in evidence)
        if broken:
            status = 'attention'
        rows.append({'id': key, 'label': label, 'value': fact.value if fact else '', 'status': status,
            'source_type': source_type, 'evidence': evidence,
            'explanation': 'Le passage source n’est plus vérifiable dans la pièce.' if broken else field_error(key, fact.value) if fact and field_error(key, fact.value) else 'Valeur relue et confirmée par le déclarant.' if fact and fact.confirmed else 'Une confirmation humaine est attendue.' if fact else 'Cette rubrique reste à compléter.',
            'reference_id': 'pilot-scope' if key == 'same_person' else 'f005-fields'})

    cross_checks = []
    ids = document_evidence(case, 'company_id')
    chosen = state.values.get('company_id')
    different = chosen and any(normalize(f['value']) != normalize(chosen.value) for f in ids)
    if ids:
        cross_checks.append({'id': 'company-identity', 'title': 'La société est-elle la même dans les pièces ?',
            'status': 'attention' if different or not chosen else 'supported',
            'explanation': 'L’identifiant retenu diffère d’au moins une pièce. Vérifiez le numéro avec l’original avant la revue.' if different else 'Les identifiants extraits concordent avec celui du formulaire.' if chosen else 'Renseignez l’identifiant du formulaire pour le comparer.',
            'evidence': ids, 'action_key': 'company_id'})
    current = document_evidence(case, 'current_address')
    proposed = document_evidence(case, 'new_address')
    if current and proposed:
        current_kinds = set(f.get('kind', 'other') for f in current)
        proposed_kinds = set(f.get('kind', 'other') for f in proposed)
        current_role = ', '.join(DOCUMENT_ROLES.get(k, k) for k in current_kinds)
        proposed_role = ', '.join(DOCUMENT_ROLES.get(k, k) for k in proposed_kinds)
        cross_checks.append({'id': 'address-timeline', 'title': 'Une ancienne adresse et une nouvelle adresse', 'status': 'context',
            'explanation': f"L'adresse actuelle provient d'un {current_role} et l'adresse proposée d'un {proposed_role}. Leur différence ne constitue pas à elle seule une contradiction : elle reflète deux moments distincts du dossier. Confirmez que ces rôles correspondent à votre situation.",
            'evidence': current + proposed, 'action_key': None})
    if len({normalize(f['value']) for f in proposed}) > 1:
        cross_checks.append({'id': 'proposed-address-conflict', 'title': 'Deux adresses proposées différentes', 'status': 'attention',
            'explanation': 'Plusieurs pièces proposent des adresses différentes pour le nouveau siège. Une seule adresse doit figurer dans le formulaire. Vérifiez les originaux et corrigez la valeur retenue.',
            'evidence': proposed, 'action_key': None})
    unverifiable = [f for f in ids + current + proposed if not f['passage_verified']]
    if unverifiable:
        cross_checks.append({'id': 'source-passages', 'title': 'Des passages sources doivent être revérifiés', 'status': 'attention',
            'explanation': 'Un extrait ou sa valeur ne se retrouve plus dans le texte de la page. Reprenez la lecture de la pièce avant de transmettre le dossier.',
            'evidence': unverifiable, 'action_key': None})
    stats = {name: sum(row['status'] == name for row in rows) for name in ('missing', 'attention', 'review', 'confirmed')}
    stats['documented'] = sum(r['source_type'] == 'document' for r in rows)
    stats['declared'] = sum(r['source_type'] == 'declaration' for r in rows)
    stats['cross_attention'] = sum(r['status'] == 'attention' for r in cross_checks)
    return {'engine_version': ENGINE_VERSION, 'rows': rows, 'cross_checks': cross_checks, 'counts': stats,
        'signature': fingerprint(case), 'scope': 'Traçabilité et cohérence des informations disponibles. Ni authentification des pièces, ni décision de recevabilité.'}
