"""Shared F005 packet and officer decisions, with isolated local data."""
import pytest
from fastapi.testclient import TestClient
from backend import config, store
from backend import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'DATA', tmp_path)
    monkeypatch.setattr(main, 'list_sources', lambda: [])
    with TestClient(main.app) as client:
        yield client


def prepared(client):
    case = client.post('/api/cases', json={'company': 'Entreprise TEST FICTIF'}).json()
    base = '/api/cases/' + case['id']
    fields = {'identifiant_unique': '0000000A', 'representant_legal': 'TEST',
              'identite_representant': '00000000', 'nom_declarant': 'TEST',
              'identite_declarant': '00000000', 'email': 'test@example.invalid',
              'gsm': '00000000', 'date': '2026-09-13'}
    draft = client.post(base + '/f005', json={'revision': 0, 'fields': fields,
                                           'modifications': ['siege']})
    assert draft.status_code == 200, draft.text
    assert draft.json()['ready'] is True
    assert client.post(base + '/submit').status_code == 409
    pdf = client.post(base + '/f005/generate', json={'revision': draft.json()['revision'], 'reviewed': True})
    assert pdf.status_code == 200, pdf.text
    submitted = client.post(base + '/submit')
    assert submitted.status_code == 200, submitted.text
    return base, submitted.json()


def test_flag_stale_decision_and_correction_round_trip(client):
    base, submitted = prepared(client)
    assert submitted['submitted_at']
    assert client.post(base + '/review', json={'action': 'flag', 'note': '  '}).status_code == 422
    flagged = client.post(base + '/review', json={'action': 'flag', 'note': 'Pièce à vérifier.',
                                                'expected_updated_at': submitted['updated_at']}).json()
    assert flagged['flagged'] is True
    assert flagged['status'] == 'submitted'
    stale = client.post(base + '/review', json={'action': 'request_correction', 'note': 'Corriger.',
                                               'expected_updated_at': submitted['updated_at']})
    assert stale.status_code == 409
    correction = client.post(base + '/review', json={'action': 'request_correction', 'note': 'Confirmer le déclarant.',
                                                     'expected_updated_at': flagged['updated_at']}).json()
    assert correction['status'] == 'correction_requested'
    assert correction['last_review']['note'] == 'Confirmer le déclarant.'
    assert correction['flagged'] is False
    draft = client.get(base + '/f005').json()
    assert draft['locked'] is False
    fields = {**draft['fields'], 'nom_declarant': 'TEST CORRIGE'}
    changed = client.post(base + '/f005', json={'revision': draft['revision'], 'fields': fields,
                                               'modifications': draft['modifications']}).json()
    assert changed['has_pdf'] is False
    assert client.post(base + '/submit').status_code == 409
    assert client.post(base + '/f005/generate', json={'revision': changed['revision'], 'reviewed': True}).status_code == 200
    assert client.post(base + '/submit').status_code == 200
    result = client.post(base + '/review', json={'action': 'reviewed', 'note': 'Pièces et déclaration vérifiées.',
                                                'checklist': ['identity', 'documents', 'declaration']}).json()
    assert result['status'] == 'reviewed'
    assert result['last_review']['checklist'] == ['identity', 'documents', 'declaration']
    assert client.get(base + '/f005').json()['locked'] is True
    assert client.post(base + '/f005', json={'revision': changed['revision'], 'fields': fields}).status_code == 409
    assert any(e['label'] == 'Dossier signalé' for e in result['events'])
    assert any(e['label'] == 'Correction demandée' for e in result['events'])


def test_review_requires_checklist_and_note(client):
    base, submitted = prepared(client)
    assert client.post(base + '/review', json={'action': 'reviewed', 'note': 'Vérifié.'}).status_code == 422
    assert client.post(base + '/review', json={'action': 'reviewed', 'note': 'Vérifié.',
        'checklist': ['identity', 'identity', 'identity']}).status_code == 422
    assert client.post(base + '/review', json={'action': 'reviewed',
        'checklist': ['identity', 'documents', 'declaration']}).status_code == 422
    assert client.post(base + '/f005', json={'revision': submitted['form']['revision']}).status_code == 409
