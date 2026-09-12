import json
import sqlite3
import threading
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path, PurePosixPath, PureWindowsPath
from backend.config import DATA

LOCK = threading.RLock()


def document_path(document):
    """Resolve uploads within the current data folder, including pre-handoff paths."""
    stored = document['file_path']
    path = Path(stored)
    if PurePosixPath(stored).is_absolute() or PureWindowsPath(stored).is_absolute():
        # Older versions stored the colleague's absolute filesystem path.
        filename = PureWindowsPath(stored).name if '\\' in stored else path.name
        path = Path('uploads') / filename
    resolved = (DATA / path).resolve()
    if not resolved.is_relative_to(DATA.resolve()):
        raise ValueError('Le chemin de la pièce sort du répertoire des données.')
    return resolved

def now():
    return datetime.now(timezone.utc).isoformat()

def event(case, label, actor='Entreprise', detail=''):
    case['events'].append({'id': uuid4().hex, 'label': label, 'actor': actor, 'detail': detail, 'at': now()})
    case['updated_at'] = now()

def connect():
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATA / 'dossier.sqlite')
    conn.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    return conn

def save(case):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO cases VALUES (?, ?)', (case['id'], json.dumps(case, ensure_ascii=False)))

def get(case_id):
    with connect() as db:
        row = db.execute('SELECT payload FROM cases WHERE id = ?', (case_id,)).fetchone()
    return json.loads(row[0]) if row else None

def all_cases():
    with connect() as db:
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM cases ORDER BY rowid')]

def new_case(company, sample=False, case_id=None):
    return {'id': case_id or 'DOS-' + uuid4().hex[:6].upper(), 'company': company, 'title': 'Changement d’adresse', 'sample': sample, 'status': 'draft', 'documents': [], 'confirmations': {}, 'events': [], 'created_at': now(), 'updated_at': now()}

def seed():
    with LOCK:
        if all_cases():
            return
        case = new_case('Atlas Studio SARL', True, 'DOS-026')
        for index, (name, kind, address) in enumerate([
            ('Déclaration de modification', 'declaration', '20, rue du Lac — Tunis'),
            ('Décision de transfert', 'decision', '22, rue du Lac — Tunis'),
            ('Extrait de registre', 'registry', '8, avenue de la Liberté — Tunis'),
        ]):
            address_key = 'current_address' if kind == 'registry' else 'new_address'
            address_label = 'Adresse actuelle' if kind == 'registry' else 'Nouvelle adresse'
            text = f'DOCUMENT FICTIF — DÉMONSTRATION\n{name}\nEntreprise : Atlas Studio SARL\nIdentifiant : DEMO-ATLAS\n{address_label} : {address}\nAucune valeur officielle.'
            fields = [
                {'key': 'company_name', 'value': 'Atlas Studio SARL', 'page': 1, 'evidence': 'Entreprise : Atlas Studio SARL'},
                {'key': 'company_id', 'value': 'DEMO-ATLAS', 'page': 1, 'evidence': 'Identifiant : DEMO-ATLAS'},
                {'key': address_key, 'value': address, 'page': 1, 'evidence': f'{address_label} : {address}'},
            ]
            case['documents'].append({'id': f'demo-{index}', 'name': name, 'kind': kind, 'filename': name + '.txt', 'status': 'extracted', 'method': 'sample_fixture', 'text': text, 'pages': [{'page': 1, 'text': text}], 'fields': fields, 'file_path': None, 'content_type': 'text/plain', 'sample': True})
        event(case, 'Documents de démonstration ajoutés')
        event(case, 'Écart d’adresse détecté', 'Vérification', 'Deux adresses proposées différentes. L’ancienne adresse du registre est conservée séparément.')
        save(case)
