from backend.sources import normalize

LABELS = {'company_name': 'Dénomination', 'company_id': 'Identifiant', 'new_address': 'Nouvelle adresse', 'current_address': 'Adresse actuelle', 'representative': 'Représentant', 'decision_date': 'Date de décision'}
# Minimum information for this workspace's address-change draft, not a legal checklist.
REQUIRED_FIELDS = ('company_name', 'company_id', 'current_address', 'new_address')

def checks(case):
    grouped = {}
    for document in case['documents']:
        for field in document['fields']:
            grouped.setdefault(field['key'], []).append({**field, 'document_id': document['id'], 'document_name': document['name']})
    issues = []
    for key in LABELS:
        fields = grouped.get(key, [])
        distinct = {normalize(f['value']) for f in fields if f['value'].strip()}
        confirmed = case['confirmations'].get(key)
        if len(distinct) > 1:
            issues.append({'key': key, 'label': LABELS[key], 'type': 'conflict', 'resolved': bool(confirmed), 'confirmation': confirmed, 'evidence': fields})
        elif not distinct and key in REQUIRED_FIELDS:
            issues.append({'key': key, 'label': LABELS[key], 'type': 'missing', 'resolved': bool(confirmed), 'confirmation': confirmed, 'evidence': []})
    pending = [d['id'] for d in case['documents'] if d['status'] != 'extracted']
    return {'issues': issues, 'pending_documents': pending, 'field_count': sum(len(d['fields']) for d in case['documents']), 'open_count': sum(not issue['resolved'] for issue in issues), 'scope': 'Contrôles de cohérence uniquement. Complétude réglementaire et authenticité non vérifiées.'}

def can_submit(case):
    result = checks(case)
    return bool(case['documents']) and not result['pending_documents'] and result['open_count'] == 0 and not case.get('correction', {}).get('pending', False)


def prepared_fields(case):
    """Never silently choose one document when sources disagree."""
    result = []
    for key, label in LABELS.items():
        evidence = [{**f, 'document_id': d['id'], 'document_name': d['name']} for d in case['documents'] for f in d['fields'] if f['key'] == key]
        confirmed = case['confirmations'].get(key)
        values = {normalize(f['value']) for f in evidence if f['value'].strip()}
        state = 'confirmed' if confirmed else 'conflict' if len(values) > 1 else 'extracted' if values else 'missing'
        value = confirmed['value'] if confirmed else evidence[0]['value'] if len(values) == 1 else ''
        result.append({'key': key, 'label': label, 'value': value, 'state': state, 'evidence': evidence})
    return result
