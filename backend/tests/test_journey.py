from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from backend import ai, config, form_ocr, journey, main, store
from backend.journey import Intent, Suggestion


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'DATA', tmp_path)
    monkeypatch.setattr(main, 'list_sources', lambda: [])
    with TestClient(main.app) as client:
        yield client


def model(monkeypatch, intent):
    monkeypatch.setattr(config, 'azure_ready', lambda: True)
    parse = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=intent))]))
    monkeypatch.setattr(ai, 'client', lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=parse))))
    return parse


def create(client):
    return '/api/cases/' + client.post('/api/cases', json={'company':'TEST FICTIF'}).json()['id']


def test_proposal_requires_confirmation_and_persists(client, monkeypatch):
    base = create(client)
    model(monkeypatch, Intent(kind='prepare', modifications=[Suggestion(key='siege',value='',evidence='Je déplace le siège')],
        fields=[Suggestion(key='identifiant_unique',value='0000000A',evidence='identifiant 0000000A')]))
    response = client.post(base+'/journey',json={'message':'Je déplace le siège, identifiant 0000000A'}).json()
    assert response['state'] == 'proposed'
    assert client.get(base+'/f005').json()['fields'] == {}
    assert client.get(base+'/journey').json()[0]['id'] == response['id']
    confirmed = client.post(base+'/journey/'+response['id']+'/confirm',json={'revision':0})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['draft']['modifications'] == ['siege']
    assert confirmed.json()['draft']['fields']['identifiant_unique'] == '0000000A'
    assert client.get(base+'/journey').json()[0]['state'] == 'confirmed'
    assert client.post(base+'/journey/'+response['id']+'/confirm',json={'revision':1}).status_code == 409
    assert client.get(base).json()['events'][-1]['label'] == 'Proposition IA confirmée'


def test_invented_values_and_unknown_modifications_are_rejected():
    intent = Intent(kind='prepare', modifications=[Suggestion(key='invented',value='',evidence='change')],
        fields=[Suggestion(key='identifiant_unique',value='1234567A',evidence='change'),
                Suggestion(key='email',value='fake@test.tn',evidence='fake@test.tn')])
    assert journey.verified(intent, 'change') == ([], [])


def test_stale_proposal_cannot_overwrite_manual_edit(client, monkeypatch):
    base = create(client)
    model(monkeypatch, Intent(kind='prepare', modifications=[Suggestion(key='siege',value='',evidence='siège')],fields=[]))
    response = client.post(base+'/journey',json={'message':'siège'}).json()
    client.post(base+'/f005',json={'revision':0,'fields':{'identifiant_unique':'0000000A'},'modifications':['banque']})
    assert client.post(base+'/journey/'+response['id']+'/confirm',json={'revision':1}).status_code == 409
    assert client.get(base+'/f005').json()['modifications'] == ['banque']


def test_question_does_not_apply_proposed_fields(client, monkeypatch):
    base = create(client)
    model(monkeypatch, Intent(kind='question', modifications=[Suggestion(key='siege',value='',evidence='siège')],fields=[]))
    monkeypatch.setattr(ai, 'answer', AsyncMock(return_value={'text':'Réponse avec sources.','sources':[]}))
    response = client.post(base+'/journey',json={'message':'Comment changer le siège ?'}).json()
    assert response['state'] == 'answered'
    assert response['modifications'] == []
    assert client.get(base+'/f005').json()['revision'] == 0


def test_no_provider_is_explicit_and_keeps_draft(client):
    base = create(client)
    assert client.post(base+'/journey',json={'message':'Je change le siège'}).status_code == 503
    assert client.get(base+'/journey').json() == []
    assert client.get(base+'/f005').json()['revision'] == 0


def test_ocr_address_conflict_and_confirmation_invalidation(client, monkeypatch):
    base = create(client)
    async def extract(content, mime, kind, scope):
        value = content.decode()
        return {'candidates': [], 'facts':[{'key':'new_address','value':value,'evidence':value,'page':1}],
                'pages':[{'page':1,'text':value}],'method':'fixture','warnings':[], 'duration_ms':1}
    monkeypatch.setattr(form_ocr, 'extract', extract)
    first = client.post(base+'/f005/ocr',data={'kind':'auto'},files={'file':('decision.txt',b'10 rue TEST','text/plain')})
    assert first.status_code == 200, first.text
    second = client.post(base+'/f005/ocr',data={'kind':'auto'},files={'file':('declaration.txt',b'12 rue TEST','text/plain')})
    assert second.status_code == 200
    assert client.get(base).json()['checks']['open_count'] == 1
    assert client.post(base+'/confirm',json={'key':'new_address','value':'12 rue TEST'}).status_code == 200
    assert client.get(base).json()['checks']['open_count'] == 0
    client.post(base+'/f005/ocr',data={'kind':'auto'},files={'file':('third.txt',b'14 rue TEST','text/plain')})
    assert client.get(base).json()['checks']['open_count'] == 1
