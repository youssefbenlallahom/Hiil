import json
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from uuid import uuid4
from backend.config import DATA

LOCK = threading.RLock()

def now():
    return datetime.now(timezone.utc).isoformat()

def event(case, label, actor='Entreprise', detail=''):
    case['events'].append({'id': uuid4().hex, 'label': label, 'actor': actor, 'detail': detail, 'at': now()})
    case['updated_at'] = now()

def connect():
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATA / 'dossier.sqlite')
    conn.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS conversations (case_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    return conn


def load_conversation(case_id):
    with closing(connect()) as db:
        row = db.execute('SELECT payload FROM conversations WHERE case_id = ?', (case_id,)).fetchone()
    return json.loads(row[0]) if row else None


def save_conversation(case_id, state):
    with LOCK, closing(connect()) as db, db:
        db.execute('INSERT OR REPLACE INTO conversations VALUES (?, ?)', (case_id, json.dumps(state, ensure_ascii=False)))


def delete_conversation(case_id):
    with LOCK, closing(connect()) as db, db:
        db.execute('DELETE FROM conversations WHERE case_id = ?', (case_id,))

def save(case):
    with closing(connect()) as db, db:
        db.execute('INSERT OR REPLACE INTO cases VALUES (?, ?)', (case['id'], json.dumps(case, ensure_ascii=False)))

def get(case_id):
    with closing(connect()) as db:
        row = db.execute('SELECT payload FROM cases WHERE id = ?', (case_id,)).fetchone()
    return json.loads(row[0]) if row else None

def all_cases():
    with closing(connect()) as db:
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM cases ORDER BY rowid')]

def new_case(company, sample=False, case_id=None):
    return {'id': case_id or 'DOS-' + uuid4().hex[:12].upper(), 'company': company, 'title': 'Déclaration de modification', 'sample': sample, 'status': 'draft', 'documents': [], 'confirmations': {}, 'events': [], 'created_at': now(), 'updated_at': now()}

def seed():
    with LOCK:
        if get('DOS-026'):
            return
        case = new_case('Atlas Studio SARL', True, 'DOS-026')
        case['status'] = 'submitted'
        case['submitted_at'] = now()
        case['flagged'] = False

        doc1_text = (
            "RÉPUBLIQUE TUNISIENNE\n"
            "MINISTÈRE DES FINANCES — DIRECTION GÉNÉRALE DES IMPÔTS\n"
            "CARTE D'IDENTIFICATION FISCALE (PATENTE)\n"
            "Matricule fiscal : 1428593/A/M/000\n"
            "Dénomination sociale : Atlas Studio SARL\n"
            "Activité : Conseil en technologies de l'information et design numérique\n"
            "Adresse d'exploitation : 15, Avenue Habib Bourguiba, 1001 Tunis\n"
            "Régime fiscal : Réel\n"
            "Bureau de contrôle : Recette des Finances Tunis"
        )
        fields1 = [
            {'key': 'company_name', 'value': 'Atlas Studio SARL', 'page': 1, 'evidence': 'Dénomination sociale : Atlas Studio SARL'},
            {'key': 'company_id', 'value': '1428593/A/M/000', 'page': 1, 'evidence': 'Matricule fiscal : 1428593/A/M/000'},
            {'key': 'current_address', 'value': '15, Avenue Habib Bourguiba, 1001 Tunis', 'page': 1, 'evidence': "Adresse d'exploitation : 15, Avenue Habib Bourguiba, 1001 Tunis"},
        ]
        case['documents'].append({
            'id': 'demo-patente',
            'name': 'Carte d’identification fiscale (Patente DGI)',
            'kind': 'registry',
            'filename': 'patente-dgi-atlas.txt',
            'status': 'extracted',
            'method': 'sample_fixture',
            'text': doc1_text,
            'pages': [{'page': 1, 'text': doc1_text}],
            'fields': fields1,
            'file_path': None,
            'content_type': 'text/plain',
            'sample': True
        })

        doc2_text = (
            "RÉPUBLIQUE TUNISIENNE\n"
            "REGISTRE NATIONAL DES ENTREPRISES (RNE)\n"
            "EXTRAIT DU REGISTRE DE COMMERCE — IMMATRICULATION PRINCIPALE\n"
            "Identifiant unique : 1428593A\n"
            "Dénomination : Atlas Studio SARL\n"
            "Forme juridique : Société à Responsabilité Limitée (SARL)\n"
            "Capital social : 20 000 TND\n"
            "Gérant / Représentant légal : Mohamed Amine Ben Salem (CIN: 08765432)\n"
            "Adresse du siège social : 15, Avenue Habib Bourguiba, 1001 Tunis"
        )
        fields2 = [
            {'key': 'company_name', 'value': 'Atlas Studio SARL', 'page': 1, 'evidence': 'Dénomination : Atlas Studio SARL'},
            {'key': 'company_id', 'value': '1428593A', 'page': 1, 'evidence': 'Identifiant unique : 1428593A'},
            {'key': 'current_address', 'value': '15, Avenue Habib Bourguiba, 1001 Tunis', 'page': 1, 'evidence': 'Adresse du siège social : 15, Avenue Habib Bourguiba, 1001 Tunis'},
            {'key': 'representative', 'value': 'Mohamed Amine Ben Salem', 'page': 1, 'evidence': 'Gérant / Représentant légal : Mohamed Amine Ben Salem'},
        ]
        case['documents'].append({
            'id': 'demo-rne',
            'name': 'Extrait du Registre RNE',
            'kind': 'registry',
            'filename': 'extrait-rne-atlas.txt',
            'status': 'extracted',
            'method': 'sample_fixture',
            'text': doc2_text,
            'pages': [{'page': 1, 'text': doc2_text}],
            'fields': fields2,
            'file_path': None,
            'content_type': 'text/plain',
            'sample': True
        })

        doc3_text = (
            "ATLAS STUDIO SARL — AU CAPITAL DE 20 000 DT\n"
            "PROCÈS-VERBAL DE L'ASSEMBLÉE GÉNÉRALE EXTRAORDINAIRE\n"
            "Date de réunion : 20 août 2026\n"
            "Résolution n° 1 : Transfert du siège social de la société.\n"
            "Ancienne adresse : 15, Avenue Habib Bourguiba, 1001 Tunis\n"
            "Nouvelle adresse : 22, Rue du Lac Léman, Les Berges du Lac, 1053 Tunis\n"
            "Résolution n° 2 : Mise à jour des statuts et pouvoirs conférés au gérant Mohamed Amine Ben Salem."
        )
        fields3 = [
            {'key': 'company_name', 'value': 'Atlas Studio SARL', 'page': 1, 'evidence': 'ATLAS STUDIO SARL'},
            {'key': 'new_address', 'value': '22, Rue du Lac Léman, Les Berges du Lac, 1053 Tunis', 'page': 1, 'evidence': 'Nouvelle adresse : 22, Rue du Lac Léman, Les Berges du Lac, 1053 Tunis'},
            {'key': 'decision_date', 'value': '2026-08-20', 'page': 1, 'evidence': 'Date de réunion : 20 août 2026'},
            {'key': 'representative', 'value': 'Mohamed Amine Ben Salem', 'page': 1, 'evidence': 'pouvoirs conférés au gérant Mohamed Amine Ben Salem'},
        ]
        case['documents'].append({
            'id': 'demo-pv',
            'name': 'Procès-Verbal d’AGE (Transfert de siège)',
            'kind': 'decision',
            'filename': 'pv-age-transfert-siege.txt',
            'status': 'extracted',
            'method': 'sample_fixture',
            'text': doc3_text,
            'pages': [{'page': 1, 'text': doc3_text}],
            'fields': fields3,
            'file_path': None,
            'content_type': 'text/plain',
            'sample': True
        })

        case['confirmations'] = {
            'company_name': {'value': 'Atlas Studio SARL', 'at': now()},
            'company_id': {'value': '1428593/A/M/000', 'at': now()},
            'current_address': {'value': '15, Avenue Habib Bourguiba, 1001 Tunis', 'at': now()},
            'new_address': {'value': '22, Rue du Lac Léman, Les Berges du Lac, 1053 Tunis', 'at': now()},
            'representative': {'value': 'Mohamed Amine Ben Salem', 'at': now()},
            'decision_date': {'value': '2026-08-20', 'at': now()}
        }

        event(case, 'Dossier créé', 'Entreprise', 'Initialisation de la démarche de transfert de siège.')
        event(case, 'Pièces justificatives ajoutées', 'Entreprise', 'Patente DGI, Extrait RNE et PV d’AGE.')
        event(case, 'Analyse OCR terminée', 'Système IA', 'Extraction Azure Document Intelligence réussie.')
        event(case, 'Informations vérifiées et confirmées', 'Entreprise', 'Adresse de destination confirmée : 22, Rue du Lac Léman.')
        event(case, 'Dossier transmis à la revue', 'Entreprise', 'Soumis pour vérification par l’agent public.')
        save(case)

        # Seed F005 draft
        draft = {
            'revision': 1,
            'fields': {
                'identifiant_unique': '1428593A',
                'matricule_fiscal': '1428593/A/M/000',
                'denomination': 'Atlas Studio SARL',
                'representant_legal': 'Mohamed Amine Ben Salem',
                'identite_representant': '08765432',
                'nom_declarant': 'Mohamed Amine Ben Salem',
                'identite_declarant': '08765432',
                'adresse': '22, Rue du Lac Léman, Les Berges du Lac, 1053 Tunis',
                'email': 'contact@atlas-studio.tn',
                'gsm': '71890123',
                'date': '2026-08-20'
            },
            'modifications': ['siege_social'],
            'same_person': True,
            'step': 4,
            'generated_revision': 1,
            'imports': [],
            'provenance': {
                'denomination': {'document_id': 'demo-patente', 'page': 1, 'evidence': 'Dénomination sociale : Atlas Studio SARL', 'value': 'Atlas Studio SARL'},
                'matricule_fiscal': {'document_id': 'demo-patente', 'page': 1, 'evidence': 'Matricule fiscal : 1428593/A/M/000', 'value': '1428593/A/M/000'},
                'identifiant_unique': {'document_id': 'demo-rne', 'page': 1, 'evidence': 'Identifiant unique : 1428593A', 'value': '1428593A'},
                'representant_legal': {'document_id': 'demo-rne', 'page': 1, 'evidence': 'Gérant / Représentant légal : Mohamed Amine Ben Salem', 'value': 'Mohamed Amine Ben Salem'},
                'adresse': {'document_id': 'demo-pv', 'page': 1, 'evidence': 'Nouvelle adresse : 22, Rue du Lac Léman, Les Berges du Lac, 1053 Tunis', 'value': '22, Rue du Lac Léman, Les Berges du Lac, 1053 Tunis'}
            }
        }
        with closing(connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS f005_drafts (case_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO f005_drafts VALUES (?, ?)', ('DOS-026', json.dumps(draft, ensure_ascii=False)))

        # Pre-generate the PDF file
        try:
            from backend import form_pdf, form_routes
            pdf_bytes = form_pdf.render(form_routes.effective(draft), draft['modifications'])
            gen_folder = DATA / 'form-generated'
            gen_folder.mkdir(parents=True, exist_ok=True)
            (gen_folder / 'DOS-026.pdf').write_bytes(pdf_bytes)
        except Exception:
            pass

