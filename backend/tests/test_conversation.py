from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import config, flow, store
from backend.main import app

BASE = '/api/cases/DOS-026'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'DATA', tmp_path)
    with TestClient(app) as client:
        yield client


def use_agent(monkeypatch, turn):
    calls = []

    class Agent:
        async def kickoff_async(self, messages, response_format):
            calls.append(messages)
            assert response_format is flow.AgentTurn
            if isinstance(turn, Exception):
                raise turn
            return SimpleNamespace(pydantic=flow.AgentTurn.model_validate(turn))

    monkeypatch.setattr(flow, 'configured', lambda: True)
    monkeypatch.setattr(flow, 'create_agent', Agent)
    return calls


def complete_state():
    state = flow.get_session('DOS-026')
    state.scenario_key = 'changement_siege'
    state.collected_fields.update({
        'identifiant_unique': '9988776A', 'representant_legal': 'Sami Ben Amor',
        'identite_representant': '01234567', 'email': 'sami@example.tn',
        'gsm': '+216 22123456', 'nom_declarant': 'Sami Ben Amor',
        'identite_declarant': '01234567', 'date': '12 / 09 / 2026',
    })
    flow._evaluate(state)
    flow.save_session(state)
    return state


def test_multi_field_turn_uses_agent_output_and_real_message_roles(client, monkeypatch):
    client.get(BASE + '/conversation')
    message = 'C’est une succursale. Le gérant est Sami Ben Amor, CIN 09876543 ; mon GSM : 22123456.'
    calls = use_agent(monkeypatch, {
        'reply': 'Noté pour la succursale et les coordonnées. Qui sera le déclarant ?',
        'scenario_key': 'changement_succursale', 'scenario_evidence': 'C’est une succursale',
        'updates': [
            {'key': 'representant_legal', 'value': 'Sami Ben Amor', 'evidence': 'Le gérant est Sami Ben Amor'},
            {'key': 'identite_representant', 'value': '09876543', 'evidence': 'CIN 09876543'},
            {'key': 'gsm', 'value': '22123456', 'evidence': 'mon GSM : 22123456'},
        ],
    })
    result = client.post(BASE + '/conversation', json={'message': message}).json()
    assert result['mode'] == 'llm'
    assert result['progress']['scenario'] == 'changement_succursale'
    assert result['collected']['representant_legal'] == 'Sami Ben Amor'
    assert result['collected']['identite_representant'] == '09876543'
    assert result['collected']['gsm'] == '+216 22123456'
    assert 'nom_declarant' not in result['collected']
    assert calls[0][-1] == {'role': 'user', 'content': message}
    assert sum(m['content'] == message for m in calls[0]) == 1
    assert any(m['role'] == 'assistant' for m in calls[0])
    reloaded = client.get(BASE + '/conversation').json()
    assert reloaded['history'] == result['history']
    assert flow.get_session('DOS-026').collected_fields == result['collected']


@pytest.mark.parametrize('message', [
    'Je ne confirme pas, expliquez-moi le déclarant.',
    'Oui, mais je ne veux pas encore générer.',
    'Quelle différence entre siège social et succursale ?',
    'Je ne sais pas qui est le représentant légal.',
])
def test_questions_and_negation_do_not_fill_or_generate(client, monkeypatch, message):
    state = complete_state()
    use_agent(monkeypatch, {'reply': 'Le déclarant est la personne qui réalise la formalité.', 'updates': []})
    result = client.post(BASE + '/conversation', json={'message': message}).json()
    assert result['collected'] == state.collected_fields
    assert result['form_path'] is None
    assert result['status'] == 'confirming'
    assert not (config.DATA / 'generated').exists()


def test_correction_invalidates_pdf_and_requires_new_confirmation(client, monkeypatch):
    complete_state()
    generated = client.post(BASE + '/form/fill')
    assert generated.status_code == 200, generated.text
    assert generated.json()['status'] == 'done'
    assert client.get(BASE + '/form').headers['content-type'] == 'application/pdf'
    use_agent(monkeypatch, {'reply': 'Adresse e-mail corrigée. Relisez le récapitulatif.', 'updates': [
        {'key': 'email', 'value': 'nouveau@example.tn', 'evidence': 'Mon email est nouveau@example.tn'},
    ]})
    result = client.post(BASE + '/conversation', json={'message': 'Mon email est nouveau@example.tn'}).json()
    assert result['collected']['email'] == 'nouveau@example.tn'
    assert result['form_path'] is None
    assert result['status'] == 'confirming'
    assert client.get(BASE + '/form').status_code == 404
    regenerated = client.post(BASE + '/form/fill').json()
    assert regenerated['status'] == 'done'
    assert regenerated['history'][-1]['text'] == regenerated['reply']


def test_agent_failure_is_visible_and_does_not_run_fallback(client, monkeypatch, caplog):
    before = client.get(BASE + '/conversation').json()['collected']
    use_agent(monkeypatch, RuntimeError('PROVIDER_SECRET_MUST_NOT_LEAK'))
    result = client.post(BASE + '/conversation', json={'message': 'email: test@example.tn'}).json()
    assert result['mode'] == 'unavailable'
    assert result['error_code'] == 'llm_runtimeerror'
    assert result['collected'] == before
    assert 'PROVIDER_SECRET_MUST_NOT_LEAK' not in caplog.text
    assert 'PROVIDER_SECRET_MUST_NOT_LEAK' not in str(result)


def test_rejects_invented_value_and_invalid_email(client, monkeypatch):
    before = client.get(BASE + '/conversation').json()['collected']
    use_agent(monkeypatch, {'reply': 'Tout est enregistré.', 'updates': [
        {'key': 'email', 'value': 'faux', 'evidence': 'email: faux'},
        {'key': 'representant_legal', 'value': 'Personne inventée', 'evidence': 'email: faux'},
    ]})
    result = client.post(BASE + '/conversation', json={'message': 'email: faux'}).json()
    assert result['collected'] == before
    assert 'Tout est enregistré' not in result['reply']
    assert 'précision' in result['reply']


def test_can_change_scenario_and_remove_field(client, monkeypatch):
    complete_state()
    message = 'En fait une succursale. Retirez mon email, il est incorrect.'
    use_agent(monkeypatch, {'reply': 'Démarche corrigée. Quelle adresse e-mail souhaitez-vous utiliser ?',
        'scenario_key': 'changement_succursale', 'scenario_evidence': 'En fait une succursale',
        'updates': [{'key': 'email', 'value': None, 'evidence': 'Retirez mon email'}]})
    result = client.post(BASE + '/conversation', json={'message': message}).json()
    assert result['progress']['scenario'] == 'changement_succursale'
    assert 'email' not in result['collected']
    assert result['status'] == 'gathering'
    assert result['can_generate'] is False
    assert client.post(BASE + '/form/fill').status_code == 422


def test_shared_identity_is_explicit_and_uses_known_values(client, monkeypatch):
    state = complete_state()
    state.collected_fields.pop('nom_declarant')
    state.collected_fields.pop('identite_declarant')
    flow.save_session(state)
    message = 'Le représentant légal est également le déclarant.'
    use_agent(monkeypatch, {'reply': 'Les deux rôles sont attribués à Sami Ben Amor.', 'updates': [
        {'key': 'nom_declarant', 'value': 'Sami Ben Amor', 'copy_from': 'representant_legal', 'evidence': message},
        {'key': 'identite_declarant', 'value': '01234567', 'copy_from': 'identite_representant', 'evidence': message},
    ]})
    result = client.post(BASE + '/conversation', json={'message': message}).json()
    assert result['collected']['nom_declarant'] == 'Sami Ben Amor'
    assert result['collected']['identite_declarant'] == '01234567'


def test_ocr_observation_requires_role_confirmation_without_retyping(client, monkeypatch):
    async def fake_ocr(*args):
        return {'cin': '12345678', 'name': 'Amal Ben Ali', 'method': 'OCR test'}
    monkeypatch.setattr(flow.ai, 'extract_cin', fake_ocr)
    result = client.post(BASE + '/conversation/cin', files={'file': ('cin.pdf', b'%PDF-test', 'application/pdf')}).json()
    assert 'identite_representant' not in result['collected']
    assert not result['progress'].get('scenario')
    message = 'Oui, la lecture est correcte et cette carte appartient au déclarant.'
    calls = use_agent(monkeypatch, {'reply': 'Identité du déclarant enregistrée.', 'updates': [
        {'key': 'nom_declarant', 'value': 'Amal Ben Ali', 'from_ocr': 'name', 'evidence': message},
        {'key': 'identite_declarant', 'value': '12345678', 'from_ocr': 'cin', 'evidence': message},
    ]})
    result = client.post(BASE + '/conversation', json={'message': message}).json()
    assert result['collected']['nom_declarant'] == 'Amal Ben Ali'
    assert result['collected']['identite_declarant'] == '12345678'
    assert 'identite_representant' not in result['collected']
    assert 'pending_ocr' in calls[0][0]['content']


def test_guided_mode_is_explicit_and_does_not_treat_sentences_as_names(client):
    client.post(BASE + '/conversation', json={'message': 'Siège social'})
    result = client.post(BASE + '/conversation', json={'message': 'Je ne comprends pas du tout'}).json()
    assert result['mode'] == 'guided'
    assert 'sans LLM' in result['reply']
    assert 'representant_legal' not in result['collected']
    assert 'nom_declarant' not in result['collected']
    assert client.post(BASE + '/form/fill').status_code == 422


def test_reset_removes_persisted_history_and_stale_download(client):
    complete_state()
    client.post(BASE + '/form/fill')
    assert client.post(BASE + '/conversation/reset').status_code == 200
    result = client.get(BASE + '/conversation').json()
    assert len(result['history']) == 1
    assert result['form_path'] is None
    assert client.get(BASE + '/form').status_code == 404


def test_azure_v1_configuration_preserves_endpoint(monkeypatch):
    monkeypatch.setattr(config, 'BASE_URL', 'https://test.openai.azure.com/openai/v1/')
    monkeypatch.setattr(config, 'API_KEY', 'synthetic-key')
    monkeypatch.setattr(config, 'DEPLOYMENT', 'my-deployment')
    monkeypatch.setattr(flow, 'LLM', lambda **kwargs: kwargs)
    params = flow.get_llm()
    assert params['base_url'].endswith('/openai/v1/')
    assert params['model'] == 'openai/my-deployment'
