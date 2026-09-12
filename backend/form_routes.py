import asyncio
import io
import json
import re
import threading
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from backend import config, form_ocr, form_pdf, store
from backend.form_catalog import FIELD_MAP, MOD_MAP, catalog

router = APIRouter()
OCR_SLOTS = asyncio.Semaphore(2)
PDF_LOCK = threading.Lock()


class DraftInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=0)
    fields: dict[str, str] = Field(default_factory=dict, max_length=10)
    modifications: list[str] = Field(default_factory=list, max_length=31)
    same_person: bool = False
    step: int = Field(default=0, ge=0, le=4)


class GenerateInput(BaseModel):
    revision: int = Field(ge=0)
    reviewed: Literal[True]


def require_case(case_id):
    if not store.get(case_id):
        raise HTTPException(404, 'Dossier introuvable.')


def connection():
    db = store.connect()
    db.execute('CREATE TABLE IF NOT EXISTS f005_drafts (case_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    return db


def load(case_id):
    with closing(connection()) as db:
        row = db.execute('SELECT payload FROM f005_drafts WHERE case_id = ?', (case_id,)).fetchone()
    return json.loads(row[0]) if row else dict(revision=0, fields={'date': date.today().isoformat()}, modifications=[],
        same_person=False, step=0, generated_revision=None, imports=[])


def save(case_id, draft):
    with closing(connection()) as db, db:
        db.execute('INSERT OR REPLACE INTO f005_drafts VALUES (?, ?)', (case_id, json.dumps(draft, ensure_ascii=False)))


def effective(draft):
    fields = dict(draft['fields'])
    if draft['same_person']:
        fields['nom_declarant'] = fields.get('representant_legal', '')
        fields['identite_declarant'] = fields.get('identite_representant', '')
    return fields


def errors_for(fields, modifications):
    errors = {}
    if not modifications:
        errors['modifications'] = 'Choisissez au moins une modification.'
    for key, f in FIELD_MAP.items():
        value = fields.get(key, '').strip()
        needed = f['required'] or (key == 'rib' and 'banque' in modifications)
        if not value:
            if needed:
                errors[key] = 'Ce renseignement est nécessaire.'
            continue
        if len(value) > f['max_length'] or '\n' in value or '\r' in value:
            errors[key] = f'Utilisez au maximum {f["max_length"]} caractères sur une ligne.'
        elif key == 'identifiant_unique' and not re.fullmatch(r'[A-Za-z0-9]{8}', value):
            errors[key] = 'Recopiez les 8 caractères de l’identifiant dans les 8 cases du formulaire.'
        elif key == 'email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            errors[key] = 'Exemple de format : contact@entreprise.tn.'
        elif key == 'gsm' and not re.fullmatch(r'(?:\+216|00216)?[0-9]{8}', re.sub(r'[\s().-]', '', value)):
            errors[key] = 'Saisissez 8 chiffres, avec ou sans +216.'
        elif key == 'rib' and not re.fullmatch(r'[0-9]{20}', value.replace(' ', '')):
            errors[key] = 'Recopiez les 20 chiffres dans les cases du RIB.'
        elif key == 'date':
            try:
                date.fromisoformat(value)
            except ValueError:
                errors[key] = 'Choisissez une date valide.'
    return errors


def public(draft):
    fields = effective(draft)
    errors = errors_for(fields, draft['modifications'])
    return {**draft, 'fields': fields, 'errors': errors, 'ready': not errors,
            'has_pdf': draft['generated_revision'] == draft['revision']}


@router.get('/api/f005/catalog')
def get_catalog():
    return catalog()


@router.get('/api/f005/template')
def get_template():
    return FileResponse(form_pdf.TEMPLATE, media_type='application/pdf', filename='RNE-F-005-original.pdf')


@router.get('/api/cases/{case_id}/f005')
def get_draft(case_id: str):
    require_case(case_id)
    return public(load(case_id))


@router.post('/api/cases/{case_id}/f005')
def update_draft(case_id: str, body: DraftInput):
    require_case(case_id)
    if set(body.fields) - FIELD_MAP.keys() or set(body.modifications) - MOD_MAP.keys():
        raise HTTPException(422, 'Champ ou type de modification inconnu.')
    if any(len(value) > 200 for value in body.fields.values()):
        raise HTTPException(422, 'Une valeur dépasse la longueur autorisée.')
    with store.LOCK:
        draft = load(case_id)
        if body.revision != draft['revision']:
            raise HTTPException(409, 'Ce formulaire a changé dans une autre fenêtre. Rechargez la page avant de continuer.')
        draft.update(fields={k: v.strip() for k, v in body.fields.items()},
                     modifications=list(dict.fromkeys(body.modifications)), same_person=body.same_person,
                     step=body.step, revision=draft['revision'] + 1, generated_revision=None)
        save(case_id, draft)
    return public(draft)


@router.post('/api/cases/{case_id}/f005/ocr')
async def read_ocr(case_id: str, file: UploadFile = File(...), kind: str = Form(...)):
    require_case(case_id)
    if kind not in form_ocr.ALLOWED:
        raise HTTPException(422, 'Choisissez le type de pièce à lire.')
    content = await file.read(8 * 1024 * 1024 + 1)
    if not content or len(content) > 8 * 1024 * 1024:
        raise HTTPException(413, 'Choisissez un fichier non vide de 8 Mo maximum.')
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
        raise HTTPException(415, 'Formats acceptés : PDF, PNG, JPG ou texte UTF-8.')
    try:
        async with OCR_SLOTS:
            result = await form_ocr.extract(content, mime, kind)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    except Exception:
        raise HTTPException(502, 'La lecture a échoué. Réessayez avec une image nette ou remplissez les champs à la main.') from None
    batch_id = uuid4().hex
    folder = config.DATA / 'form-uploads' / case_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / batch_id).write_bytes(content)
    batch = dict(id=batch_id, name=name, kind=kind, mime=mime, **result)
    with store.LOCK:
        draft = load(case_id)
        draft['imports'] = (draft['imports'] + [batch])[-10:]
        save(case_id, draft)  # OCR does not alter fields or their revision.
    return batch


@router.get('/api/cases/{case_id}/f005/ocr/{batch_id}')
def original_upload(case_id: str, batch_id: str):
    require_case(case_id)
    batch = next((b for b in load(case_id)['imports'] if b['id'] == batch_id), None)
    if not batch:
        raise HTTPException(404, 'Document introuvable.')
    return FileResponse(config.DATA / 'form-uploads' / case_id / batch_id, media_type=batch['mime'],
                        filename=batch['name'], content_disposition_type='inline', headers={'X-Content-Type-Options': 'nosniff'})


@router.get('/api/cases/{case_id}/f005/preview/{page}')
def preview(case_id: str, page: int):
    require_case(case_id)
    if page not in (1, 2):
        raise HTTPException(404, 'Page introuvable.')
    draft = load(case_id)
    fields = effective(draft)
    invalid = errors_for(fields, draft['modifications'])
    fields = {k: v for k, v in fields.items() if k not in invalid}
    with PDF_LOCK:
        import pypdfium2 as pdfium
        pdf = form_pdf.render(fields, draft['modifications'], draft=True)
        doc = pdfium.PdfDocument(pdf)
        image = doc[page - 1].render(scale=1.5).to_pil()
        data = io.BytesIO()
        image.save(data, format='PNG')
        image.close()
        doc.close()
    return Response(data.getvalue(), media_type='image/png', headers={'Cache-Control': 'no-store'})


@router.post('/api/cases/{case_id}/f005/generate')
def generate(case_id: str, body: GenerateInput):
    require_case(case_id)
    with store.LOCK:
        draft = load(case_id)
        if body.revision != draft['revision']:
            raise HTTPException(409, 'Enregistrez les dernières modifications avant de générer le PDF.')
        if not public(draft)['ready']:
            raise HTTPException(422, 'Complétez ou corrigez les champs signalés avant de générer le PDF.')
        with PDF_LOCK:
            pdf = form_pdf.render(effective(draft), draft['modifications'])
        folder = config.DATA / 'form-generated'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{case_id}.pdf').write_bytes(pdf)
        draft['generated_revision'] = draft['revision']
        save(case_id, draft)
    return public(draft)


@router.get('/api/cases/{case_id}/f005/pdf')
def download(case_id: str):
    require_case(case_id)
    draft = load(case_id)
    path = config.DATA / 'form-generated' / f'{case_id}.pdf'
    if not public(draft)['has_pdf'] or not path.is_file():
        raise HTTPException(404, 'Préparez le PDF à partir de la dernière version du formulaire.')
    return FileResponse(path, media_type='application/pdf', filename=f'{case_id}-RNE-F005-a-signer.pdf')
