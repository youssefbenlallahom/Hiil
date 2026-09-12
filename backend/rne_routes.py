import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from backend import ai, config, store
from backend.rne_flow import DeclarationFlow, load_state, view, invalidate
from backend.rne_knowledge import blockers
from backend.rne_models import Evidence, Message, RneRequest
from backend.rne_pdf import TEMPLATE, render_f005
from backend.evidence import report

router = APIRouter(prefix='/api')
SLOTS = asyncio.Semaphore(2)


def case_for(case_id, editing=False):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, 'Dossier introuvable.')
    if editing and case['status'] in ('submitted', 'reviewed'):
        raise HTTPException(409, 'Le dossier est en revue. Demandez une correction avant de le modifier.')
    return case


def response_for(case):
    state = load_state(case)
    doc = next((d for d in case['documents'] if d['id'] == state.cin_document_id), None)
    evidence_case = {**case, 'rne': state.model_dump()}
    return {**view(state), 'ai_configured': config.azure_ready(), 'report': report(evidence_case),
            'sample': case.get('demo_scenario') is not None,
            'institution': {k: v for k, v in case.get('institution', {}).items() if k not in ('snapshot', 'report', 'history')},
            'cin_document_name': doc['name'] if doc else None,
            'locked': case['status'] in ('submitted', 'reviewed')}


@router.get('/rne/template')
def template():
    return FileResponse(TEMPLATE, media_type='application/pdf', filename='RNE-F005-v1.1.pdf', content_disposition_type='inline')


@router.get('/cases/{case_id}/rne')
def rne_detail(case_id: str):
    return response_for(case_for(case_id))


@router.post('/cases/{case_id}/rne/turn')
async def rne_turn(case_id: str, body: RneRequest):
    with store.LOCK:
        case = case_for(case_id, editing=True)
        state = load_state(case)
        if body.request_id in state.processed_requests:
            return response_for(case)
        if body.revision != state.revision:
            raise HTTPException(409, 'Le dossier a changé dans un autre onglet. Rechargez le récapitulatif avant de continuer.')
    if body.action in ('message', 'extract_cin') and not config.azure_ready():
        raise HTTPException(503, 'Azure est indisponible. Vous pouvez sélectionner la modification et compléter les rubriques manuellement.')
    try:
        flow = DeclarationFlow(state, body, case)
        async with SLOTS:
            async with asyncio.timeout(210):
                await flow.kickoff_async()
    except ValueError as error:
        # Only explicit domain messages reach the client; Pydantic/provider payloads do not.
        from pydantic import ValidationError
        if isinstance(error, ValidationError):
            raise HTTPException(502, 'La lecture du modèle n’est pas exploitable. Vos informations restent enregistrées ; corrigez les rubriques ou réessayez.') from error
        raise HTTPException(422, str(error)) from error
    except Exception as error:
        raise HTTPException(502, 'Le traitement IA est indisponible. Votre dossier est conservé. Vous pouvez réessayer ou compléter les rubriques à la main.') from error
    with store.LOCK:
        latest = case_for(case_id, editing=True)
        current = load_state(latest)
        if body.request_id in current.processed_requests:
            return response_for(latest)
        if current.revision != body.revision:
            raise HTTPException(409, 'Une réponse plus récente a modifié le dossier. Rechargez le récapitulatif ; ce résultat n’a pas remplacé vos données.')
        latest['rne'] = flow.state.model_dump()
        if body.action == 'extract_cin':
            updated = next(d for d in case['documents'] if d['id'] == flow.state.cin_document_id)
            doc = next(d for d in latest['documents'] if d['id'] == flow.state.cin_document_id)
            for key in ('pages', 'text', 'method', 'identity_fields'):
                doc[key] = updated[key]
        store.event(latest, {'prepare': 'Formulaire RNE F005 préparé', 'confirm': 'Rubriques F005 confirmées'}.get(body.action, 'Parcours F005 mis à jour'), 'Assistant F005', 'Révision ' + str(flow.state.revision))
        store.save(latest)
    return response_for(latest)


@router.post('/cases/{case_id}/rne/cin', status_code=201)
async def cin_upload(case_id: str, file: UploadFile = File(...), revision: int = Form(..., ge=0), request_id: str = Form(..., min_length=8, max_length=80, pattern=r'^[a-zA-Z0-9-]+$')):
    case_for(case_id, editing=True)
    content = await file.read(12 * 1024 * 1024 + 1)
    if not content or len(content) > 12 * 1024 * 1024:
        raise HTTPException(413, 'Joignez une CIN non vide de moins de 12 Mo.')
    if content.startswith(b'%PDF-'):
        mime = 'application/pdf'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'):
        mime = 'image/png'
    elif content.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    else:
        raise HTTPException(415, 'Joignez la CIN en PDF, PNG ou JPEG.')
    try:
        pages = await asyncio.to_thread(ai.read_pages, content, mime)
        if len(pages) > 2:
            raise ValueError('La pièce CIN de ce parcours accepte au plus deux pages (recto et verso).')
    except Exception as error:
        raise HTTPException(422, 'Utilisez un document lisible, non chiffré, de deux pages maximum.') from error
    name = Path((file.filename or 'CIN').replace('\\', '/')).name
    with store.LOCK:
        case = case_for(case_id, editing=True)
        state = load_state(case)
        if request_id in state.processed_requests:
            return response_for(case)
        if state.revision != revision:
            raise HTTPException(409, 'Le dossier a changé. Rechargez le récapitulatif avant de joindre la CIN.')
        if len(case['documents']) >= 12:
            raise HTTPException(422, 'Limite de 12 pièces par dossier atteinte.')
        document_id = uuid4().hex
        path = config.DATA / 'uploads' / document_id
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        case['documents'].append({'id': document_id, 'name': name, 'filename': name, 'content_type': mime,
            'file_path': 'uploads/' + document_id, 'sample': False, 'kind': 'other', 'purpose': 'rne_cin',
            'status': 'pending', 'method': 'not_analyzed', 'pages': pages,
            'text': '\n\n'.join(p['text'] for p in pages), 'fields': []})
        # A replacement identity document invalidates data derived from the previous one.
        if state.cin_document_id:
            for key in ('declarant_name', 'declarant_id'):
                state.values.pop(key, None)
            if state.values.get('same_person') and state.values['same_person'].value == 'yes':
                state.values.pop('representative_name', None)
                state.values.pop('representative_id', None)
        state.cin_document_id, state.cin_status = document_id, 'uploaded'
        invalidate(state)
        state.messages.append(Message(id=str(uuid4()), role='assistant', at=store.now(), text='La CIN est jointe au dossier. Lancez sa lecture pour proposer le nom et le numéro, ou recopiez ces informations dans le récapitulatif.', source_ids=['pilot-scope']))
        state.revision += 1
        state.processed_requests = (state.processed_requests + [request_id])[-100:]
        case['rne'] = state.model_dump()
        store.event(case, 'CIN jointe au parcours F005')
        store.save(case)
    return response_for(case)


@router.get('/cases/{case_id}/rne/pdf')
def rne_pdf(case_id: str):
    state = load_state(case_for(case_id))
    if state.pdf_revision != state.revision or blockers(state):
        raise HTTPException(409, 'Confirmez les informations puis préparez le formulaire. Une modification invalide le PDF précédent.')
    try:
        content = render_f005(state)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition': f'inline; filename="{case_id}-RNE-F005.pdf"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
