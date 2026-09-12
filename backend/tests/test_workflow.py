import io
import json
from zipfile import ZipFile
import pytest
from fastapi.testclient import TestClient
from backend import config, store
from backend.main import app
from backend.rules import checks

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    monkeypatch.setattr(config,'DATA',tmp_path)
    monkeypatch.setattr(config,'API_KEY','')
    monkeypatch.setattr(config,'BASE_URL','')
    monkeypatch.setattr(config,'DEPLOYMENT','')
    with TestClient(app) as c:
        yield c

def test_conflict_excludes_old_registry_address(client):
    case=client.get('/api/cases/DOS-026').json()
    assert case['checks']['open_count']==1
    issue=case['checks']['issues'][0]
    assert issue['key']=='new_address'
    assert len(issue['evidence'])==2
    assert all(e['document_id']!='demo-2' for e in issue['evidence'])

def test_review_lifecycle_and_immutable_evidence(client):
    base='/api/cases/DOS-026'
    original=client.get(base).json()['documents']
    assert client.post(base+'/submit').status_code==409
    corrected=client.post(base+'/confirm',json={'key':'new_address','value':'22, rue du Lac — Tunis'})
    assert corrected.status_code==200
    assert corrected.json()['documents']==original
    assert corrected.json()['checks']['open_count']==0
    assert client.post(base+'/submit').status_code==200
    assert client.post(base+'/confirm',json={'key':'new_address','value':'x'}).status_code==409
    assert client.post(base+'/review',json={'action':'request_correction','note':''}).status_code==422
    review=client.post(base+'/review',json={'action':'request_correction','note':'Merci de joindre la pièce corrigée.'})
    assert review.json()['status']=='correction_requested'
    assert client.post(base+'/submit').status_code==200
    assert client.post(base+'/review',json={'action':'reviewed','note':'Confirmations consultées.'}).json()['status']=='reviewed'
    assert client.post(base+'/review',json={'action':'reviewed'}).status_code==409

def test_no_ai_does_not_invent_extraction(client):
    case=client.post('/api/cases',json={'company':'Entreprise test'}).json()
    base='/api/cases/'+case['id']
    response=client.post(base+'/documents',files={'file':('piece.txt','Nouvelle adresse : 15, Tunis'.encode(),'text/plain')})
    doc=response.json()['documents'][0]
    assert doc['fields']==[]
    assert doc['status']=='pending'
    assert client.post(base+'/documents/'+doc['id']+'/analyze').status_code==503
    assert client.get(base).json()['documents'][0]['text']=='Nouvelle adresse : 15, Tunis'
    assert client.post(base+'/submit').status_code==409

def test_export_contains_originals_and_confirmations(client):
    client.post('/api/cases/DOS-026/confirm',json={'key':'new_address','value':'22, rue du Lac — Tunis'})
    response=client.get('/api/cases/DOS-026/export')
    assert response.status_code==200
    with ZipFile(io.BytesIO(response.content)) as archive:
        data=json.loads(archive.read('dossier.json'))
        assert 'file_path' not in data['documents'][0]
        assert data['confirmations']['new_address']['value'].startswith('22,')
        assert '20, rue' in archive.read('pieces/01-demonstration.txt').decode()
        assert 'Aucun dépôt officiel' in archive.read('synthese.html').decode()

def test_upload_clears_stale_confirmation(client):
    client.post('/api/cases/DOS-026/confirm',json={'key':'new_address','value':'22, rue du Lac — Tunis'})
    result=client.post('/api/cases/DOS-026/documents',files={'file':('piece.txt',b'Nouvelle piece','text/plain')}).json()
    assert result['confirmations']=={}
    assert result['can_submit'] is False

def test_invalid_inputs_and_unknown_cases(client):
    assert client.get('/api/cases/unknown').status_code==404
    assert client.post('/api/cases',json={'company':'  '}).status_code==422
    assert client.post('/api/cases/DOS-026/confirm',json={'key':'new_address','value':' '}).status_code==422
    assert client.post('/api/cases/DOS-026/documents',files={'file':('payload.html',b'<script>alert(1)</script>','text/html')}).status_code==415
    assert client.post('/api/cases/DOS-026/documents',files={'file':('empty.txt',b'','text/plain')}).status_code==413

def test_assistant_explicit_demo(client):
    answer=client.post('/api/cases/DOS-026/assistant',json={'question':'Que dois-je faire ?'}).json()
    assert answer['mode']=='demo'
    assert 'aucune réponse LLM' in answer['text']

def test_normalized_values_do_not_raise_false_conflict(client):
    case=store.get('DOS-026')
    case['documents'][0]['fields'][-1]['value']='22, RUE DU LAC — TUNIS'
    assert checks(case)['open_count']==0
