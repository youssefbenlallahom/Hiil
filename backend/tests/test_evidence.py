import asyncio
import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from backend import ai, config, store
from backend.demo import demo_case
from backend.evidence import report, fingerprint
from backend.main import app
from backend.rne_models import RneState
from backend import rne_agent


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'DATA', tmp_path)
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'azure_ready', lambda: False)
    with TestClient(app) as c:
        yield c


def turn(client, base, **body):
    state = client.get(base + '/rne').json()
    result = client.post(base + '/rne/turn', json={'revision': state['revision'], 'request_id': str(uuid4()), **body})
    assert result.status_code == 200, result.text
    return result.json()


def prepare_demo(client):
    base = '/api/cases/' + client.post('/api/demo').json()['case_id']
    turn(client, base, action='select_modification', modification='seat_address')
    turn(client, base, action='use_evidence', key='company_id', document_id='registry')
    turn(client, base, action='confirm')
    state = turn(client, base, action='prepare')
    return base, state


def test_demo_detects_identifier_error_but_does_not_compare_old_and_new_as_conflict():
    result = report(demo_case())
    checks = {c['id']: c for c in result['cross_checks']}
    assert checks['company-identity']['status'] == 'attention'
    assert checks['address-timeline']['status'] == 'context'
    assert 'proposed-address-conflict' not in checks
    assert result['counts']['documented'] == 4
    assert result['counts']['declared'] == 4


def test_conflicting_proposed_addresses_are_not_silently_harmonized():
    case = demo_case()
    doc = copy.deepcopy(case['documents'][-1])
    doc['id'] = 'another-decision'
    doc['fields'][-1]['value'] = '99, rue du Lac, Tunis'
    case['documents'].append(doc)
    assert any(c['id'] == 'proposed-address-conflict' and c['status'] == 'attention' for c in report(case)['cross_checks'])


def test_altered_source_quote_is_flagged():
    case = demo_case()
    case['documents'][0]['pages'][0]['text'] = 'Texte différent'
    result = report(case)
    assert result['counts']['attention'] == 4
    assert not result['rows'][1]['evidence'][0]['passage_verified']


def test_cross_check_rejects_extracted_value_without_matching_passage():
    case = demo_case()
    case['documents'][1]['pages'][0]['text'] = 'DOCUMENT FICTIF — contenu remplacé'
    checks = report(case)['cross_checks']
    assert any(c['id'] == 'source-passages' and c['status'] == 'attention' for c in checks)


def test_reference_tool_reads_the_versioned_original_form():
    from backend.rne_corpus import retrieve_reference
    reference = retrieve_reference('siège social')
    assert len(reference['form_pages']) == 2
    assert all(len(p['text']) > 100 for p in reference['form_pages'])
    assert reference['source']['sha256'] == 'ef9fcf5544e3bf20b3148fd46dce94005e7570e9fe583e435b2e4ef2e6c567fb'
    assert any(n['id'] == 'f005-choices' for n in reference['interpretation_notes'])


def test_retain_evidence_corrects_form_without_mutating_original(client):
    base = '/api/cases/' + client.post('/api/demo').json()['case_id']
    original = client.get(base).json()['documents']
    state = turn(client, base, action='use_evidence', key='company_id', document_id='registry')
    assert state['values']['company_id']['value'] == '1234567A'
    assert state['values']['company_id']['evidence'][0]['origin'] == 'document'
    assert not state['values']['company_id']['confirmed']
    assert state['report']['counts']['cross_attention'] == 0
    assert client.get(base).json()['documents'] == original


def test_institutional_correction_loop_preserves_old_snapshot(client):
    base, state = prepare_demo(client)
    submission = client.post(base + '/rne/submit', json={'revision': state['revision'], 'signature': state['report']['signature']})
    assert submission.status_code == 200, submission.text
    first = submission.json()
    first_pdf = base + '/rne/submissions/' + first['submission_id'] + '/pdf'
    from pypdf import PdfReader
    from io import BytesIO
    initial_text = PdfReader(BytesIO(client.get(first_pdf).content)).pages[0].extract_text()
    assert '22123456' in initial_text
    assert client.get('/api/institution/queue').json()[0]['submission_id'] == first['submission_id']
    bad = client.post(base + '/rne/review', json={'submission_id': first['submission_id'], 'action': 'request_correction', 'note': 'Corriger le contact', 'check_ids': []})
    assert bad.status_code == 422
    decision = client.post(base + '/rne/review', json={'submission_id': first['submission_id'], 'action': 'request_correction', 'note': 'Veuillez préciser le numéro GSM du déclarant.', 'check_ids': ['phone']})
    assert decision.status_code == 200
    turn(client, base, action='edit', key='phone', value='22987654')
    assert PdfReader(BytesIO(client.get(first_pdf).content)).pages[0].extract_text() == initial_text
    turn(client, base, action='confirm')
    updated = turn(client, base, action='prepare')
    assert client.post(base + '/rne/submit', json={'revision': updated['revision'], 'signature': updated['report']['signature']}).status_code == 409
    assert client.post(base + '/correction-response', json={'note': 'Le contact GSM a été corrigé.'}).status_code == 200
    second = client.post(base + '/rne/submit', json={'revision': updated['revision'], 'signature': updated['report']['signature']}).json()
    assert second['signature'] != first['signature']
    assert second['history'][0]['snapshot']['values']['phone']['value'] == '22123456'
    assert second['snapshot']['values']['phone']['value'] == '22987654'
    assert PdfReader(BytesIO(client.get(first_pdf).content)).pages[0].extract_text() == initial_text
    assert client.post(base + '/rne/review', json={'submission_id': first['submission_id'], 'action': 'reviewed', 'note': 'Ancienne version'}).status_code == 409
    assert client.post(base + '/rne/review', json={'submission_id': second['submission_id'], 'action': 'reviewed', 'note': 'Les rubriques et leurs sources ont été examinées.'}).status_code == 200
    assert client.get(base).json()['status'] == 'reviewed'


def test_stale_content_and_conflict_block_handoff(client):
    base, state = prepare_demo(client)
    turn(client, base, action='edit', key='company_id', value='9999999A')
    turn(client, base, action='confirm')
    updated = turn(client, base, action='prepare')
    assert client.post(base + '/rne/submit', json={'revision': state['revision'], 'signature': state['report']['signature']}).status_code == 409
    assert client.post(base + '/rne/submit', json={'revision': updated['revision'], 'signature': updated['report']['signature']}).status_code == 409


def test_content_signature_ignores_chat_but_changes_with_source():
    case = demo_case()
    original = fingerprint(case)
    case['rne']['messages'] = []
    case['rne']['revision'] += 1
    assert fingerprint(case) == original
    case['documents'][0]['pages'][0]['text'] += 'Autre passage'
    assert fingerprint(case) != original


def test_real_crewai_agent_executes_tool_with_fake_transport(monkeypatch):
    """The actual CrewAI executor is exercised; only Azure transport is substituted."""
    monkeypatch.setattr(config, 'azure_ready', lambda: True)
    monkeypatch.setattr(config, 'DEPLOYMENT', 'Kimi-K2.6')
    monkeypatch.setattr(config, 'MODEL_THINKING', 'auto')
    calls = []
    replies = [
        'Thought: I need the available evidence.\nAction: examiner_preuves_dossier\nAction Input: {"topic":"identifiant"}',
        'Thought: I can explain the check.\nFinal Answer: ' + json.dumps({'reply': 'Le numéro du formulaire diffère des pièces. Vérifiez le chiffre signalé.', 'updates': [], 'source_ids': []}),
    ]
    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def with_options(self, **kwargs): return self
        @property
        def chat(self): return self
        @property
        def completions(self): return self
        async def create(self, **kwargs):
            assert kwargs['extra_body'] == {'thinking': {'type': 'disabled'}}
            calls.append(kwargs['messages'])
            assert replies, 'Unexpected extra model call'
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=replies.pop(0)))])
    monkeypatch.setattr(ai, 'client', FakeClient)
    case = demo_case()
    result = asyncio.run(rne_agent.propose(RneState.model_validate(case['rne']), 'Pourquoi ce numéro ?', case))
    assert result.reply.startswith('Le numéro')
    assert len(calls) == 2
    assert any('company-identity' in str(message) for message in calls[-1])
