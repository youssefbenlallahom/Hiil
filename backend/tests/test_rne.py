"""Offline acceptance cases. No credentials, personal documents or model calls."""
import io
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
import pytest

from backend import ai, config, rne_agent, store
from backend.main import app
from backend.rne_models import IdentityField, Proposal, Update


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'azure_ready', lambda: False)
    def no_network():
        raise AssertionError('Offline tests must not contact Azure')
    monkeypatch.setattr(ai, 'client', no_network)
    with TestClient(app) as client:
        yield client


def new(client):
    case = client.post('/api/cases', json={'company': 'Société fictive'}).json()
    return '/api/cases/' + case['id']


def turn(client, base, **body):
    state = client.get(base + '/rne').json()
    return client.post(base + '/rne/turn', json={'revision': state['revision'], 'request_id': str(uuid4()), **body})


def upload(client, base, content=None, **extra):
    if content is None:
        image = io.BytesIO()
        Image.new('RGB', (30, 30), 'white').save(image, format='PNG')
        content = image.getvalue()
    state = client.get(base + '/rne').json()
    return client.post(base + '/rne/cin', data={'revision': state['revision'], 'request_id': str(uuid4()), **extra}, files={'file': ('synthetic-cin.png', content, 'image/png')})


def ready(client, base):
    assert turn(client, base, action='select_modification', modification='seat_address').status_code == 200
    assert upload(client, base).status_code == 201
    for key, value in {'company_id': '1234567A', 'declarant_name': 'أحمد بن صالح', 'declarant_id': '00123456', 'same_person': 'yes', 'email': 'demo@example.org', 'phone': '22123456'}.items():
        result = turn(client, base, action='edit', key=key, value=value)
        assert result.status_code == 200, result.text
    assert turn(client, base, action='confirm').status_code == 200


def test_complete_form_preserves_original_and_is_exported(client):
    base = new(client)
    ready(client, base)
    result = turn(client, base, action='prepare')
    assert result.status_code == 200, result.text
    assert result.json()['stage'] == 'prepared'
    response = client.get(base + '/rne/pdf')
    assert response.status_code == 200
    pdf = PdfReader(io.BytesIO(response.content))
    assert len(pdf.pages) == 2
    assert 'demo@example.org' in pdf.pages[0].extract_text()
    assert '00123456' in pdf.pages[0].extract_text()
    template = PdfReader(io.BytesIO(client.get('/api/rne/template').content))
    assert pdf.pages[1].extract_text() == template.pages[1].extract_text()
    with ZipFile(io.BytesIO(client.get(base + '/export').content)) as archive:
        assert 'RNE-F005.pdf' in archive.namelist()


def test_correction_invalidates_pdf_and_human_confirmation(client):
    base = new(client)
    ready(client, base)
    assert turn(client, base, action='prepare').status_code == 200
    changed = turn(client, base, action='edit', key='declarant_id', value='00987654').json()
    assert not changed['values']['declarant_id']['confirmed']
    assert changed['values']['representative_id']['value'] == '00987654'
    assert not changed['values']['representative_id']['confirmed']
    assert client.get(base + '/rne/pdf').status_code == 409
    assert turn(client, base, action='prepare').status_code == 422


def test_stale_and_retried_requests_cannot_overwrite(client):
    base = new(client)
    body = {'revision': 0, 'request_id': str(uuid4()), 'action': 'select_modification', 'modification': 'seat_address'}
    first = client.post(base + '/rne/turn', json=body).json()
    again = client.post(base + '/rne/turn', json=body).json()
    assert first['revision'] == again['revision'] == 1
    assert first['messages'] == again['messages']
    body.update(request_id=str(uuid4()), modification='branch_address')
    assert client.post(base + '/rne/turn', json=body).status_code == 409
    assert client.get(base + '/rne').json()['modification'] == 'seat_address'


def test_representative_is_not_assumed_and_role_can_change(client):
    base = new(client)
    turn(client, base, action='edit', key='declarant_name', value='أحمد بن صالح')
    assert 'representative_name' not in client.get(base + '/rne').json()['values']
    turn(client, base, action='edit', key='same_person', value='yes')
    assert turn(client, base, action='edit', key='representative_name', value='محمد علي').status_code == 422
    changed = turn(client, base, action='edit', key='same_person', value='no').json()
    assert 'representative_name' not in changed['values']
    assert changed['values']['declarant_name']['value'] == 'أحمد بن صالح'


def test_branch_or_multiple_changes_cannot_generate_seat_form(client):
    base = new(client)
    ready(client, base)
    for modification in ('branch_address', 'other'):
        result = turn(client, base, action='select_modification', modification=modification)
        assert result.json()['stage'] == 'out_of_scope'
        assert turn(client, base, action='prepare').status_code == 422
        assert turn(client, base, action='confirm').status_code == 422


def test_incomplete_and_invalid_form_never_confirmed(client):
    base = new(client)
    assert turn(client, base, action='confirm').status_code == 422
    for key, value in [('declarant_id', '123'), ('email', 'bad'), ('same_person', 'perhaps'), ('declarant_name', 'Invented Latin Name')]:
        assert turn(client, base, action='edit', key=key, value=value).status_code == 422
    assert client.get(base + '/rne').json()['revision'] == 0


def test_no_ai_does_not_fake_conversation_or_identity(client):
    base = new(client)
    assert turn(client, base, action='message', message='Je déménage').status_code == 503
    assert upload(client, base).status_code == 201
    assert turn(client, base, action='extract_cin').status_code == 503
    assert client.get(base + '/rne').json()['values'] == {}


def test_identity_evidence_and_human_correction_survive_reanalysis(client, monkeypatch):
    base = new(client)
    upload(client, base)
    monkeypatch.setattr(config, 'azure_ready', lambda: True)
    async def fake(*args):
        fields = [IdentityField(key='first_name', value='أحمد', page=1, evidence='الاسم أحمد'), IdentityField(key='last_name', value='صالح', page=1, evidence='اللقب صالح'), IdentityField(key='cin_number', value='00123456', page=1, evidence='رقم 00123456')]
        return fields, [{'page': 1, 'text': 'الاسم أحمد\nاللقب صالح\nرقم 00123456'}], 'fake_ocr'
    monkeypatch.setattr(rne_agent, 'extract_cin', fake)
    result = turn(client, base, action='extract_cin')
    assert result.status_code == 200, result.text
    fact = result.json()['values']['declarant_id']
    assert fact['value'] == '00123456' and not fact['confirmed']
    assert fact['evidence'][0]['page'] == 1
    turn(client, base, action='edit', key='declarant_id', value='00987654')
    turn(client, base, action='extract_cin')
    assert client.get(base + '/rne').json()['values']['declarant_id']['value'] == '00987654'
    assert 'representative_id' not in client.get(base + '/rne').json()['values']


def test_ambiguous_intent_then_answering_question_keeps_state(client, monkeypatch):
    base = new(client)
    monkeypatch.setattr(config, 'azure_ready', lambda: True)
    async def ambiguous(state, message):
        return Proposal(reply='L’adresse du siège ou celle d’une succursale ?', candidates=['seat_address', 'branch_address'], reason='Le mot local ne permet pas de distinguer les deux.', source_ids=['f005-choices'])
    monkeypatch.setattr(rne_agent, 'propose', ambiguous)
    result = turn(client, base, action='message', message='Je change de local').json()
    assert result['stage'] == 'clarification'
    assert result['modification'] is None
    assert len(result['candidates']) == 2
    ready(client, base)
    turn(client, base, action='prepare')
    async def explanation(state, message):
        return Proposal(reply='Le formulaire demande les données en arabe ; le français est facultatif.', source_ids=['f005-instructions'])
    monkeypatch.setattr(rne_agent, 'propose', explanation)
    result = turn(client, base, action='message', message='Pourquoi en arabe ?').json()
    assert result['stage'] == 'prepared'
    assert result['modification'] == 'seat_address'
    assert client.get(base + '/rne/pdf').status_code == 200


def test_failed_agent_turn_is_atomic(client, monkeypatch):
    base = new(client)
    monkeypatch.setattr(config, 'azure_ready', lambda: True)
    async def failure(state, message):
        raise RuntimeError('Provider failure with private request detail')
    monkeypatch.setattr(rne_agent, 'propose', failure)
    response = turn(client, base, action='message', message='Bonjour')
    assert response.status_code == 502
    assert 'private request' not in response.text
    assert client.get(base + '/rne').json()['revision'] == 0


def test_replacing_cin_invalidates_derived_identity(client):
    base = new(client)
    ready(client, base)
    turn(client, base, action='prepare')
    assert upload(client, base).status_code == 201
    state = client.get(base + '/rne').json()
    assert 'declarant_id' not in state['values']
    assert 'representative_id' not in state['values']
    assert client.get(base + '/rne/pdf').status_code == 409


def test_case_state_isolation_and_review_lock(client):
    a, b = new(client), new(client)
    turn(client, a, action='edit', key='phone', value='22123456')
    assert client.get(b + '/rne').json()['values'] == {}
    case = store.get(a.split('/')[-1])
    case['status'] = 'submitted'
    store.save(case)
    assert turn(client, a, action='edit', key='phone', value='22987654').status_code == 409
    assert upload(client, a).status_code == 409
    assert client.get(a + '/rne').json()['locked'] is True
