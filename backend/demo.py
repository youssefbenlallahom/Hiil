"""Explicit, isolated, pre-analysed fictional case for a reproducible showcase."""
from uuid import uuid4
from fastapi import APIRouter
from backend import store
from backend.rne_models import RneState, Value, Evidence, Message

router = APIRouter(prefix='/api')


def demo_case():
    case = store.new_case('Jasmin Services · démonstration', sample=True)
    case['title'] = 'Transfert du siège · F005'
    case['demo_scenario'] = 'identity-mismatch-and-address-timeline-v1'
    identity = 'EXEMPLE FICTIF — AUCUNE VALEUR OFFICIELLE\nFiche de données simulant une lecture de CIN\nNom : أحمد بن صالح\nNuméro fictif : 00123456'
    docs = [
        ('cin', 'Identité fictive · données préanalysées', 'other', identity, []),
        ('registry', 'Extrait RNE fictif · siège actuel', 'registry', 'DOCUMENT FICTIF\nIdentifiant : 1234567A\nAdresse actuelle : 8, avenue de la Liberté, Tunis', [('company_id', '1234567A', 'Identifiant : 1234567A'), ('current_address', '8, avenue de la Liberté, Tunis', 'Adresse actuelle : 8, avenue de la Liberté, Tunis')]),
        ('decision', 'Décision fictive · nouveau siège', 'decision', 'DOCUMENT FICTIF\nIdentifiant : 1234567A\nNouvelle adresse : 22, rue du Lac, Tunis', [('company_id', '1234567A', 'Identifiant : 1234567A'), ('new_address', '22, rue du Lac, Tunis', 'Nouvelle adresse : 22, rue du Lac, Tunis')]),
    ]
    for doc_id, name, kind, text, fields in docs:
        case['documents'].append({'id': doc_id, 'name': name, 'filename': name + '.txt', 'kind': kind,
            'purpose': 'rne_cin' if doc_id == 'cin' else 'supporting_document',
            'content_type': 'text/plain', 'sample': True, 'status': 'extracted', 'method': 'sample_fixture',
            'file_path': None, 'text': text, 'pages': [{'page': 1, 'text': text}],
            'fields': [{'key': k, 'value': v, 'page': 1, 'evidence': e} for k, v, e in fields]})
    state = RneState(cin_document_id='cin', cin_status='extracted', candidates=['seat_address', 'branch_address'])
    for key, value in {'company_id': '1234568A', 'declarant_name': 'أحمد بن صالح', 'declarant_id': '00123456',
        'representative_name': 'أحمد بن صالح', 'representative_id': '00123456', 'same_person': 'yes',
        'email': 'demo@example.org', 'phone': '22123456'}.items():
        document = key in ('declarant_name', 'declarant_id', 'representative_name', 'representative_id')
        quote = ('Nom : أحمد بن صالح' if key.endswith('name') else 'Numéro fictif : 00123456') if document else key + ' : ' + value
        state.values[key] = Value(value=value, evidence=[Evidence(origin='document' if document else 'user',
            reference_id='cin' if document else 'demo-entry', page=1 if document else None, quote=quote)])
    state.messages = [
        Message(id=str(uuid4()), role='assistant', at=store.now(), text='Démonstration préanalysée : les personnes, les documents et cet échange initial sont fictifs. Les contrôles, corrections et le formulaire sont calculés par l’application.', source_ids=['pilot-scope']),
        Message(id=str(uuid4()), role='user', at=store.now(), text='J’ai changé de local et je souhaite mettre ma société à jour.'),
        Message(id=str(uuid4()), role='assistant', at=store.now(), text='Le changement concerne-t-il l’adresse du siège social ou celle d’une succursale ? Le F005 distingue ces deux rubriques. Précisons ce point, puis vérifions l’identifiant de la société.', source_ids=['f005-choices']),
    ]
    case['rne'] = state.model_dump()
    store.event(case, 'Démonstration fictive créée', 'Jeu de démonstration', 'Données préanalysées ; aucune extraction IA en direct annoncée.')
    return case


@router.post('/demo', status_code=201)
def create_demo():
    with store.LOCK:
        case = demo_case()
        store.save(case)
    return {'case_id': case['id']}
