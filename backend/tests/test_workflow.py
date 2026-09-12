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
    assert client.post(base+'/submit').status_code==409
    assert client.post(base+'/correction-response',json={'note':'La valeur confirmée est correcte ; voir la décision de transfert.'}).status_code==200
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


def test_missing_fields_block_incomplete_dossier(client):
    case=store.new_case('Entreprise test')
    sample=store.get('DOS-026')['documents'][0]
    sample['fields']=sample['fields'][:1]
    case['documents']=[sample]
    store.save(case)
    result=client.get('/api/cases/'+case['id']).json()
    assert {i['key'] for i in result['checks']['issues']}=={'company_id','current_address','new_address'}
    assert all(i['type']=='missing' for i in result['checks']['issues'])
    assert not result['can_submit']


def test_manual_upload_to_review_without_azure(client):
    case=client.post('/api/cases',json={'company':'Jasmin Services'}).json()
    base='/api/cases/'+case['id']
    content='Entreprise : Jasmin Services\nIdentifiant : TEST-001\nAdresse actuelle : Ancienne rue\nNouvelle adresse : Nouvelle rue'
    result=client.post(base+'/documents',files={'file':('piece.txt',content.encode(),'text/plain')}).json()
    doc=result['documents'][0]
    fields=[{'key':key,'value':value,'page':1,'evidence':evidence} for key,value,evidence in [
        ('company_name','Jasmin Services','Entreprise : Jasmin Services'),
        ('company_id','TEST-001','Identifiant : TEST-001'),
        ('current_address','Ancienne rue','Adresse actuelle : Ancienne rue'),
        ('new_address','Nouvelle rue','Nouvelle adresse : Nouvelle rue'),
    ]]
    reviewed=client.post(base+'/documents/'+doc['id']+'/review',json={'kind':'declaration','fields':fields})
    assert reviewed.status_code==200
    assert reviewed.json()['can_submit']
    assert reviewed.json()['documents'][0]['method']=='manual_review'
    assert client.get(base+'/documents/'+doc['id']+'/file').content==content.encode()
    assert client.post(base+'/submit').status_code==200
    assert client.post(base+'/documents/'+doc['id']+'/review',json={'kind':'other','fields':[]}).status_code==409
    assert client.post(base+'/review',json={'action':'reviewed','note':'Pièces consultées'}).json()['status']=='reviewed'


@pytest.mark.parametrize('patch',[
    {'page':99}, {'evidence':'Une source inventée : Valeur'}, {'value':'Autre valeur'}, {'value':' '}, {'evidence':' '}
])
def test_manual_evidence_validation_preserves_original(client,patch):
    base='/api/cases/DOS-026'
    original=client.get(base).json()['documents'][0]
    field={**original['fields'][0],**patch}
    response=client.post(base+'/documents/demo-0/review',json={'kind':'declaration','fields':[field]})
    assert response.status_code==422
    assert client.get(base).json()['documents'][0]==original


def test_manual_review_clears_confirmations_and_keeps_history(client):
    base='/api/cases/DOS-026'
    original=client.get(base).json()['documents'][0]
    client.post(base+'/confirm',json={'key':'new_address','value':'22, rue du Lac — Tunis'})
    response=client.post(base+'/documents/demo-0/review',json={'kind':'declaration','fields':original['fields']})
    assert response.status_code==200
    result=response.json()
    assert result['confirmations']=={}
    assert result['documents'][0]['field_history'][0]['fields']==original['fields']
    assert result['documents'][0]['text']==original['text']
    assert not result['can_submit']


def test_correction_survives_upload_and_requires_response(client):
    base='/api/cases/DOS-026'
    client.post(base+'/confirm',json={'key':'new_address','value':'22, rue du Lac — Tunis'})
    client.post(base+'/submit')
    client.post(base+'/review',json={'action':'request_correction','note':'Joindre la pièce corrigée.'})
    result=client.post(base+'/documents',files={'file':('piece.txt',b'Piece corrigee','text/plain')}).json()
    assert result['status']=='correction_requested'
    assert result['sample'] is True
    assert result['correction']['pending'] is True
    assert client.post(base+'/correction-response',json={'note':' '}).status_code==422
    assert client.post(base+'/correction-response',json={'note':'Pièce jointe'}).status_code==200
    assert client.post(base+'/correction-response',json={'note':'Pièce jointe'}).status_code==409
    assert client.post(base+'/submit').status_code==409  # New upload still needs review.


def test_declared_missing_fields_are_distinguished_from_evidence(client):
    base='/api/cases/DOS-026'
    response=client.post(base+'/confirm',json={'key':'representative','value':'Représentant test'})
    assert response.status_code==200
    field=next(f for f in response.json()['prepared_fields'] if f['key']=='representative')
    assert field['state']=='confirmed'
    assert field['evidence']==[]


def test_draft_includes_all_fields_and_flags_conflicts(client):
    base='/api/cases/DOS-026'
    result=client.get(base).json()
    proposed=next(f for f in result['prepared_fields'] if f['key']=='new_address')
    assert proposed['state']=='conflict' and proposed['value']==''
    response=client.get(base+'/draft')
    assert response.status_code==200
    assert 'Écart à résoudre' in response.text
    assert 'DEMO-ATLAS' in response.text  # Includes unconfirmed, non-conflicting extraction.
    assert 'Non renseigné' in response.text
    assert 'ne remplace pas le formulaire RNE' in response.text
    with ZipFile(io.BytesIO(client.get(base+'/export').content)) as archive:
        assert archive.read('brouillon-changement-adresse.html').decode()==response.text


def test_draft_escapes_user_content(client):
    base='/api/cases/DOS-026'
    client.post(base+'/confirm',json={'key':'new_address','value':'<script>alert(1)</script>'})
    draft=client.get(base+'/draft').text
    assert '<script>' not in draft
    assert '&lt;script&gt;' in draft


def test_all_extracted_fields_are_checked_for_conflicts(client):
    case=store.get('DOS-026')
    for doc,value in zip(case['documents'][:2],['Alice','Bob']):
        doc['fields'].append({'key':'representative','value':value,'page':1,'evidence':value})
    assert {'new_address','representative'}=={i['key'] for i in checks(case)['issues']}


@pytest.mark.parametrize('legacy', [False, 'C:\\Colleague\\Hiil\\.local-data\\uploads\\', '/home/colleague/Hiil/.local-data/uploads/'])
def test_uploads_survive_data_folder_handoff(client,tmp_path,monkeypatch,legacy):
    import shutil
    base='/api/cases/DOS-026'
    result=client.post(base+'/documents',files={'file':('piece.txt',b'Portable upload','text/plain')}).json()
    doc=result['documents'][-1]
    raw=store.get('DOS-026')
    assert raw['documents'][-1]['file_path']=='uploads/'+doc['id']
    if legacy:
        raw['documents'][-1]['file_path']=legacy+doc['id']
        store.save(raw)
    moved=tmp_path.parent/(tmp_path.name+'-moved')
    shutil.copytree(tmp_path,moved)
    monkeypatch.setattr(store,'DATA',moved)
    monkeypatch.setattr(config,'DATA',moved)
    assert client.get(base+'/documents/'+doc['id']+'/file').content==b'Portable upload'
    with ZipFile(io.BytesIO(client.get(base+'/export').content)) as archive:
        assert archive.read('pieces/04-piece.txt')==b'Portable upload'
