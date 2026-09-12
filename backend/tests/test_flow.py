import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend import config, store
from backend.main import app
from backend.form_schema import get_scenario, missing_fields, all_fields
from backend.tools import GetCaseDataTool, LookupFormTool, FillRNEF005Tool
from backend.flow import get_session, clear_session, conversation_turn, AddressChangeFlow


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'API_KEY', '')
    monkeypatch.setattr(config, 'BASE_URL', '')
    monkeypatch.setattr(config, 'DEPLOYMENT', '')
    with TestClient(app) as c:
        yield c


def test_form_schema_definitions():
    scenarios = ['changement_siege', 'changement_succursale']
    for s_key in scenarios:
        s = get_scenario(s_key)
        assert s is not None
        assert len(s.required_fields) >= 7

    fields = all_fields()
    assert any(f.key == 'identifiant_unique' for f in fields)
    assert any(f.key == 'representant_legal' for f in fields)
    assert any(f.key == 'email' for f in fields)


def test_tools_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'DATA', tmp_path)
    store.seed()

    # 1. GetCaseDataTool
    case_tool = GetCaseDataTool()
    res = case_tool._run('DOS-026')
    assert 'Atlas Studio SARL' in res
    assert 'Documents' in res

    # 2. LookupFormTool
    lookup_tool = LookupFormTool()
    scenarios_list = lookup_tool._run()
    assert 'changement_siege' in scenarios_list
    details = lookup_tool._run('changement_siege')
    assert 'Identifiant unique' in details

    # 3. FillRNEF005Tool
    fill_tool = FillRNEF005Tool()
    pdf_out = fill_tool._run(
        case_id='DOS-TEST-FLOW',
        scenario_key='changement_siege',
        fields={
            'identifiant_unique': '9988776A',
            'representant_legal': 'Sami Ben Amor',
            'identite_representant': '01234567',
            'email': 'sami@test.tn',
            'gsm': '98765432',
            'nom_declarant': 'Sami Ben Amor',
            'identite_declarant': '01234567',
            'date': '12 / 09 / 2026',
        }
    )
    assert Path(pdf_out).exists()
    assert Path(pdf_out).stat().st_size > 1000


@pytest.mark.anyio
async def test_flow_conversation_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    monkeypatch.setattr(config, 'DATA', tmp_path)
    store.seed()
    case_id = 'DOS-026'
    clear_session(case_id)

    # Turn 1: User says they moved
    r1 = await conversation_turn(case_id, "J'ai changé de local, je veux mettre mes papiers à jour.")
    assert 'siège social' in r1['reply'].lower()
    assert r1['status'] in ('greeting', 'clarifying')

    # Turn 2: User asks what the difference is
    r2 = await conversation_turn(case_id, "Je ne comprends pas la différence.")
    assert 'siège social' in r2['reply'].lower()
    assert 'succursale' in r2['reply'].lower()

    # Turn 3: User clarifies it's the headquarters
    r3 = await conversation_turn(case_id, "Siège social")
    assert r3['progress']['scenario'] == 'changement_siege'

    # Turn 4: User provides details
    r4 = await conversation_turn(case_id, "email: contact@atlas.tn; gsm: 98123456")
    assert r4['collected'].get('email') == 'contact@atlas.tn'
    assert '98123456' in r4['collected'].get('gsm', '')

    # Turn 5: User provides CIN
    r5 = await conversation_turn(case_id, "identite_representant: 08876543; nom_declarant: Sami Ben Amor")
    assert r5['collected'].get('identite_representant') == '08876543'
    assert r5['collected'].get('nom_declarant') is not None


def test_api_conversation_endpoints(client, monkeypatch):
    case_id = 'DOS-026'
    clear_session(case_id)

    # Initial conversation GET
    res = client.get(f'/api/cases/{case_id}/conversation')
    assert res.status_code == 200
    data = res.json()
    assert 'reply' in data

    # Post user message
    res2 = client.post(
        f'/api/cases/{case_id}/conversation',
        json={'message': "Siège social"}
    )
    assert res2.status_code == 200
    assert res2.json()['progress'].get('scenario') == 'changement_siege'

    # Upload CIN photo
    async def fake_ocr(*args):
        return {'cin': '14776423', 'name': 'Sami Ben Amor', 'method': 'OCR test'}
    monkeypatch.setattr('backend.ai.extract_cin', fake_ocr)
    pdf_content = b'%PDF-1.4 mocked OCR input'
    res_cin = client.post(
        f'/api/cases/{case_id}/conversation/cin',
        files={'file': ('cin_card.pdf', pdf_content, 'application/pdf')}
    )
    assert res_cin.status_code == 200
    cin_data = res_cin.json()
    assert 'identite_representant' not in cin_data['collected']
    assert '14776423' in cin_data['reply']
    assert cin_data['history'][-1]['text'] == cin_data['reply']

    # Reset
    res_reset = client.post(f'/api/cases/{case_id}/conversation/reset')
    assert res_reset.status_code == 200
    assert res_reset.json()['status'] == 'reset'

    # Download form
    res_form = client.get(f'/api/cases/{case_id}/form')
    assert res_form.status_code == 404
