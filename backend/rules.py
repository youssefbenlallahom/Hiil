from backend.sources import normalize

LABELS = {'company_name': 'Dénomination', 'company_id': 'Identifiant', 'new_address': 'Nouvelle adresse', 'current_address': 'Adresse actuelle', 'representative': 'Représentant', 'decision_date': 'Date de décision'}

def checks(case):
    grouped = {}
    for document in case['documents']:
        for field in document['fields']:
            grouped.setdefault(field['key'], []).append({**field, 'document_id': document['id'], 'document_name': document['name']})
    issues = []
    for key in ('company_name', 'company_id', 'new_address'):
        fields = grouped.get(key, [])
        distinct = {normalize(f['value']) for f in fields}
        if len(distinct) > 1:
            confirmed = case['confirmations'].get(key)
            issues.append({'key': key, 'label': LABELS[key], 'type': 'conflict', 'resolved': bool(confirmed), 'confirmation': confirmed, 'evidence': fields})
    pending = [d['id'] for d in case['documents'] if d['status'] != 'extracted']
    return {'issues': issues, 'pending_documents': pending, 'field_count': sum(len(d['fields']) for d in case['documents']), 'open_count': sum(not issue['resolved'] for issue in issues), 'scope': 'Contrôles de cohérence uniquement. Complétude réglementaire et authenticité non vérifiées.'}

def can_submit(case):
    result = checks(case)
    return bool(case['documents']) and result['field_count'] > 0 and not result['pending_documents'] and result['open_count'] == 0
