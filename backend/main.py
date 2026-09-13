import asyncio
import html
import io
import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import os

from backend import ai, config, store
from backend.models import Confirmation, NewCase, Question, Review, ConversationMessage, ConversationResponse
from backend.flow import conversation_turn, process_cin_upload, get_session, clear_session, conversation_lock, generate_form
from backend.rules import can_submit, checks
from backend.sources import list_sources, refresh_sources
from backend import form_routes
from backend.form_routes import router as form_router


@asynccontextmanager
async def lifespan(app):
    await asyncio.to_thread(list_sources)
    yield

app = FastAPI(title='Dossier TN', lifespan=lifespan)
app.include_router(form_router)

app.add_middleware(CORSMiddleware, allow_origins=os.getenv('DOSSIER_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(','), allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
MODEL_SLOTS = asyncio.Semaphore(2)

def required(case_id):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, 'Dossier introuvable.')
    return case

def public(case):
    draft = form_routes.public(form_routes.load(case['id']))
    return {**case, 'documents': [{k: v for k, v in doc.items() if k != 'file_path'} for doc in case['documents']],
            'checks': checks(case), 'can_submit': can_submit(case),
            'form': {k: draft[k] for k in ('revision', 'has_pdf', 'ready', 'step', 'modifications', 'errors')}}

def editable(case):
    if case['status'] in ('submitted', 'reviewed'):
        raise HTTPException(409, 'Le dossier est en revue. Demandez une correction avant de le modifier.')

@app.get('/api/health')
def health():
    config.reload()
    return {'status': 'ok', 'ai_configured': config.azure_ready(), 'ocr_configured': bool(config.OCR_ENDPOINT and config.OCR_KEY),
            'ocr_provider': 'Azure Document Intelligence' if config.OCR_ENDPOINT and config.OCR_KEY else 'Azure Vision' if config.azure_ready() else 'OCR Windows' if os.name == 'nt' else None,
            'mode': 'local_workspace', 'institutional_connection': False}

@app.get('/api/sources')
def sources():
    return [{k: v for k, v in s.items() if k not in ('pages', 'local_asset')} for s in list_sources()]


@app.post('/api/sources/refresh')
async def refresh_references():
    return [{k: v for k, v in s.items() if k not in ('pages', 'local_asset')} for s in await refresh_sources()]


@app.get('/api/sources/{source_id}/snapshot')
def source_snapshot(source_id: str):
    item = next((s for s in list_sources() if s['id'] == source_id), None)
    if not item or not item.get('hash'):
        raise HTTPException(404, 'Aucune copie collectée de cette référence.')
    path = config.DATA / 'source-snapshots' / item['hash']
    return FileResponse(path, media_type=item['content_type'], filename=source_id + ('.pdf' if item['content_type'] == 'application/pdf' else '.html'), content_disposition_type='attachment')

@app.get('/api/cases')
def cases():
    return [public(case) for case in store.all_cases()]

@app.post('/api/cases', status_code=201)
def create(body: NewCase):
    company = body.company.strip()
    if len(company) < 2:
        raise HTTPException(422, 'Indiquez le nom de l’entreprise.')
    with store.LOCK:
        case = store.new_case(company)
        store.event(case, 'Dossier créé')
        store.save(case)
    return public(case)

@app.get('/api/cases/{case_id}')
def case_detail(case_id: str):
    return public(required(case_id))

@app.post('/api/cases/{case_id}/documents', status_code=201)
async def upload(case_id: str, file: UploadFile = File(...)):
    editable(required(case_id))
    content = await file.read(12 * 1024 * 1024 + 1)
    if not content or len(content) > 12 * 1024 * 1024:
        raise HTTPException(413, 'Ajoutez un document non vide de moins de 12 Mo.')
    name = Path((file.filename or 'document').replace('\\', '/')).name
    if content.startswith(b'%PDF-'):
        mime = 'application/pdf'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'):
        mime = 'image/png'
    elif content.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    elif name.lower().endswith('.txt'):
        mime = 'text/plain'
    else:
        raise HTTPException(415, 'Formats acceptés : PDF, PNG, JPEG ou texte UTF-8.')
    try:
        pages = await asyncio.to_thread(ai.read_pages, content, mime)
    except Exception as error:
        detail = str(error) if isinstance(error, ValueError) else 'Le document est illisible ou endommagé.'
        raise HTTPException(422, detail) from error
    with store.LOCK:
        case = required(case_id)
        editable(case)
        if len(case['documents']) >= 24:
            raise HTTPException(422, 'Limite : 24 documents par dossier.')
        import hashlib
        digest = hashlib.sha256(content).hexdigest()
        if any(d.get('sha256') == digest for d in case['documents']):
            return public(case)
        document_id = uuid4().hex
        uploads = config.DATA / 'uploads'
        uploads.mkdir(parents=True, exist_ok=True)
        path = uploads / document_id
        path.write_bytes(content)
        case['documents'].append({'id': document_id, 'sha256': digest, 'name': name, 'filename': name, 'content_type': mime, 'file_path': str(path), 'sample': False, 'kind': 'other', 'status': 'pending', 'method': 'not_analyzed', 'pages': pages, 'text': '\n\n'.join(p['text'] for p in pages), 'fields': []})
        case['confirmations'] = {}
        case['sample'] = False
        case['status'] = 'draft'
        store.event(case, 'Document ajouté', detail=name)
        store.save(case)
    return public(case)

@app.post('/api/cases/{case_id}/documents/{document_id}/analyze')
async def analyze(case_id: str, document_id: str):
    case = required(case_id)
    editable(case)
    doc = next((d for d in case['documents'] if d['id'] == document_id), None)
    if not doc:
        raise HTTPException(404, 'Document introuvable.')
    if doc['sample']:
        return public(case)
    if not config.azure_ready():
        raise HTTPException(503, 'Azure n’est pas configuré. Complétez .env puis redémarrez le backend. Votre document reste enregistré.')
    try:
        async with MODEL_SLOTS:
            result = await ai.extract(Path(doc['file_path']).read_bytes(), doc['content_type'], doc['pages'])
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except Exception as error:
        # Provider exceptions can contain request details. Never send them to the browser.
        raise HTTPException(502, 'L’analyse Azure a échoué. Vérifiez le déploiement, les droits, le quota et la compatibilité des sorties structurées. Le document est conservé.') from error
    with store.LOCK:
        latest = required(case_id)
        editable(latest)
        document = next(d for d in latest['documents'] if d['id'] == document_id)
        document.update(result)
        latest['confirmations'] = {}
        store.event(latest, 'Document analysé', 'Azure', doc['name'])
        store.save(latest)
    return public(latest)

@app.get('/api/cases/{case_id}/documents/{document_id}/file')
def document_file(case_id: str, document_id: str):
    doc = next((d for d in required(case_id)['documents'] if d['id'] == document_id), None)
    if not doc:
        raise HTTPException(404, 'Document introuvable.')
    if doc['file_path']:
        return FileResponse(doc['file_path'], media_type=doc['content_type'], filename=doc['filename'], content_disposition_type='inline', headers={'X-Content-Type-Options': 'nosniff'})
    return Response(doc['text'], media_type='text/plain; charset=utf-8')

@app.post('/api/cases/{case_id}/confirm')
def confirm(case_id: str, body: Confirmation):
    value = body.value.strip()
    if not value:
        raise HTTPException(422, 'Indiquez la valeur confirmée.')
    with store.LOCK:
        case = required(case_id)
        editable(case)
        if not any(f['key'] == body.key for d in case['documents'] for f in d['fields']):
            raise HTTPException(422, 'Aucune information extraite pour ce champ.')
        case['confirmations'][body.key] = {'value': value, 'at': store.now(), 'actor': 'Entreprise'}
        store.event(case, 'Information confirmée', detail=f'{body.key} : {value}. Les pièces originales sont conservées.')
        store.save(case)
    return public(case)

@app.post('/api/cases/{case_id}/submit')
def submit(case_id: str):
    with store.LOCK:
        case = required(case_id)
        editable(case)
        if not can_submit(case):
            raise HTTPException(409, 'Analysez les pièces et confirmez les écarts avant de transmettre à la revue.')
        case['status'] = 'submitted'
        store.event(case, 'Dossier transmis à la revue', detail='Revue locale du prototype. Aucun dépôt auprès du RNE.')
        store.save(case)
    return public(case)

@app.post('/api/cases/{case_id}/review')
def review(case_id: str, body: Review):
    with store.LOCK:
        case = required(case_id)
        if case['status'] != 'submitted':
            raise HTTPException(409, 'Ce dossier n’est pas en attente de revue.')
        if body.action == 'request_correction' and not body.note.strip():
            raise HTTPException(422, 'Précisez la correction à demander.')
        case['status'] = 'correction_requested' if body.action == 'request_correction' else 'reviewed'
        store.event(case, 'Correction demandée' if body.action == 'request_correction' else 'Revue terminée', 'Agent (simulation)', body.note.strip())
        store.save(case)
    return public(case)

@app.post('/api/cases/{case_id}/assistant')
async def assistant(case_id: str, body: Question):
    try:
        async with MODEL_SLOTS:
            draft = form_routes.public(form_routes.load(case_id))
            return await ai.answer(body.question, required(case_id), draft, body.field)
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except Exception as error:
        raise HTTPException(502, 'La réponse Azure est indisponible. Vérifiez la configuration du modèle et réessayez.') from error

@app.get('/api/cases/{case_id}/export')
def export(case_id: str):
    case = public(required(case_id))
    raw = required(case_id)
    escape = html.escape
    fields = ''.join(f'<li><strong>{escape(key)}</strong> : {escape(value["value"])}</li>' for key, value in case['confirmations'].items())
    evidence = ''.join(f'<h3>{escape(doc["name"])}</h3><pre>{escape(doc["text"])}</pre>' for doc in case['documents'])
    source_links = ''.join(f'<li><a href="{escape(s["url"], quote=True)}">{escape(s["title"])}</a></li>' for s in list_sources() if s.get('hash'))
    summary = f'<!doctype html><html lang="fr"><meta charset="utf-8"><title>Dossier {escape(case_id)}</title><style>body{{font:16px system-ui;max-width:900px;margin:48px auto;padding:24px;color:#172d35}}pre{{white-space:pre-wrap;background:#f3f5f5;padding:24px}}h1{{color:#075866}}</style><h1>{escape(case["company"])} — {escape(case_id)}</h1><p>Note de préparation. Aucun dépôt officiel. Contrôles de cohérence uniquement ; complétude réglementaire et authenticité non vérifiées.</p><h2>Informations confirmées</h2><ul>{fields or "<li>Aucune confirmation enregistrée.</li>"}</ul><h2>Pièces et texte extrait</h2>{evidence}<h2>Sources de référence</h2><ul>{source_links}</ul></html>'
    output = io.BytesIO()
    with ZipFile(output, 'w') as archive:
        archive.writestr('synthese.html', summary)
        archive.writestr('dossier.json', json.dumps(case, ensure_ascii=False, indent=2))
        draft = form_routes.public(form_routes.load(case_id))
        archive.writestr('declaration.json', json.dumps(draft, ensure_ascii=False, indent=2))
        pdf = config.DATA / 'form-generated' / f'{case_id}.pdf'
        if draft['has_pdf'] and pdf.is_file():
            archive.write(pdf, f'{case_id}-RNE-F005-a-signer.pdf')
        # Include old uploads as well as the shared document library, preserving existing dossiers.
        for batch in draft.get('imports', []):
            if not batch.get('document_id'):
                original = config.DATA / 'form-uploads' / case_id / batch['id']
                if original.is_file():
                    archive.write(original, 'pieces/formulaire-' + Path(batch['name']).name)
        for i, doc in enumerate(raw['documents']):
            if doc['file_path']:
                archive.write(doc['file_path'], f'pieces/{i + 1:02d}-{doc["filename"]}')
            else:
                archive.writestr(f'pieces/{i + 1:02d}-demonstration.txt', doc['text'])
    return Response(output.getvalue(), media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="{case_id}.zip"'})

@app.get('/api/cases/{case_id}/conversation', response_model=ConversationResponse)
async def get_case_conversation(case_id: str):
    required(case_id)
    return await conversation_turn(case_id, '')

@app.post('/api/cases/{case_id}/conversation', response_model=ConversationResponse)
async def post_case_conversation(case_id: str, body: ConversationMessage):
    required(case_id)
    async with MODEL_SLOTS:
        return await conversation_turn(case_id, body.message)

@app.post('/api/cases/{case_id}/conversation/cin', response_model=ConversationResponse)
async def upload_case_conversation_cin(case_id: str, file: UploadFile = File(...)):
    required(case_id)
    content = await file.read(12 * 1024 * 1024 + 1)
    if not content or len(content) > 12 * 1024 * 1024:
        raise HTTPException(413, 'Ajoutez un document ou une photo de moins de 12 Mo.')
    name = Path((file.filename or 'cin.jpg').replace('\\', '/')).name
    if content.startswith(b'%PDF-'):
        mime = 'application/pdf'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'):
        mime = 'image/png'
    elif content.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    elif content.startswith(b'RIFF') and b'WEBP' in content[:16]:
        mime = 'image/webp'
    else:
        mime = file.content_type or 'image/jpeg'
    async with MODEL_SLOTS:
        return await process_cin_upload(case_id, name, content, mime)

@app.post('/api/cases/{case_id}/conversation/reset')
async def reset_conversation(case_id: str):
    required(case_id)
    async with conversation_lock(case_id):
        clear_session(case_id)
    return {'status': 'reset'}

@app.post('/api/cases/{case_id}/form/fill', response_model=ConversationResponse)
async def fill_case_form(case_id: str):
    required(case_id)
    try:
        return await generate_form(case_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    except Exception:
        raise HTTPException(500, 'La génération du PDF a échoué. Les informations saisies sont conservées.') from None

@app.get('/api/cases/{case_id}/form')
def download_form(case_id: str):
    required(case_id)
    state = get_session(case_id)
    pdf_path = Path(state.form_path) if state.form_path else None
    if not pdf_path or not pdf_path.is_file():
        raise HTTPException(404, 'Formulaire non encore généré.')
    return FileResponse(str(pdf_path), media_type='application/pdf', filename=f'{case_id}_RNE_F005.pdf')
