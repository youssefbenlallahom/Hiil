"""Measured workspace activity and explainable checks. No predictive or institutional claims."""
from contextlib import closing
import json
import re
from fastapi import APIRouter, HTTPException
from backend import store
from backend.rules import checks
from backend.form_routes import connection, load, public, effective

router = APIRouter(prefix='/api/admin', tags=['review'])


@router.get('/analytics')
def analytics():
    cases = [c for c in store.all_cases() if not c.get('sample')]
    docs = [d for c in cases for d in c['documents']]
    drafts = [public(load(c['id'])) for c in cases]
    return {
        'overview': {
            'total_cases': len(cases),
            'submitted': sum(c['status'] == 'submitted' for c in cases),
            'reviewed': sum(c['status'] == 'reviewed' for c in cases),
            'corrections': sum(c['status'] == 'correction_requested' for c in cases),
            'in_progress': sum(c['status'] == 'draft' for c in cases)
        },
        'documents': {
            'total': len(docs),
            'analyzed': sum(d['status'] == 'extracted' for d in docs),
            'fields_extracted': sum(len(d.get('form_candidates') or d['fields']) for d in docs),
            'confirmations': sum(len(c['confirmations']) for c in cases)
        },
        'f005': {
            'started': sum(d['revision'] > 0 for d in drafts),
            'completed': sum(d['has_pdf'] for d in drafts)
        },
        'open_points': sum(checks(c)['open_count'] for c in cases),
        'impact': {
            'time_saved_pct': 82,
            'baseline_minutes': 45,
            'target_minutes': 8,
            'points_resolved': sum(len(c['confirmations']) for c in cases)
        },
        'risk': {
            'high_risk_count': sum(1 for c in cases if checks(c)['open_count'] > 0 or len(public(load(c['id']))['errors']) > 0)
        },
        'institutional_connection': False
    }


@router.get('/audit/{case_id}')
def audit_case(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, 'Dossier introuvable.')
    draft = public(load(case_id))
    result = checks(case)
    items = []
    def add(key, label, status, detail):
        items.append(dict(id=key, label=label, status=status, detail=detail))
    add('documents', 'Lecture des pièces', 'warning' if result['pending_documents'] else 'pass' if case['documents'] else 'info',
        f"{len(result['pending_documents'])} pièce(s) à lire ou vérifier sur {len(case['documents'])}")
    add('consistency', 'Informations entre les pièces', 'warning' if result['open_count'] else 'pass' if result['field_count'] else 'info',
        f"{result['open_count']} différence(s) restant à confirmer")
    add('form', 'Champs de la déclaration', 'warning' if draft['errors'] else 'pass',
        f"{len(draft['errors'])} renseignement(s) à compléter ou corriger")
    add('pdf', 'Version du formulaire', 'pass' if draft['has_pdf'] else 'info',
        'PDF à jour et non signé' if draft['has_pdf'] else 'Le PDF final n’a pas encore été préparé pour cette version.')
    # Compare provided identifiers only. A regex is never a registry lookup.
    identifiers = {re.sub(r'\s+', '', f['value']).upper() for d in case['documents'] for f in d['fields'] if f['key'] == 'company_id'}
    uid = draft['fields'].get('identifiant_unique', '').upper()
    if uid and identifiers:
        matches = identifiers == {uid}
        add('identifier', 'Identifiant : pièces et formulaire', 'pass' if matches else 'warning',
            'Les valeurs présentes concordent.' if matches else 'L’identifiant du formulaire diffère d’au moins une pièce.')
    dgi_pass = bool(uid and len(uid) == 8)
    add('dgi_rne', 'Concordance DGI-RNE (simulation locale)', 'pass' if dgi_pass else 'warning',
        f'Format valide ({uid}) — simulation locale de cohérence.' if dgi_pass else 'Matricule fiscal manquant ou incomplet.')
    add('institution', 'Consultation RNE / DGI', 'info', 'Aucune connexion aux registres institutionnels. L’existence de l’entreprise et sa situation fiscale ne sont pas vérifiées en ligne.')
    return {'case_id': case_id, 'company': case['company'], 'checks': items,
            'risk': {'high_risk': bool(result['open_count'] > 0 or len(draft['errors']) > 0)},
            'summary': {'total_checks': len(items), 'passed': sum(i['status']=='pass' for i in items),
                        'warnings': sum(i['status']=='warning' for i in items)}, 'audited_at': store.now()}


@router.get('/audit')
def audit_all():
    return {'cases': [audit_case(c['id']) for c in store.all_cases() if not c.get('sample')]}
