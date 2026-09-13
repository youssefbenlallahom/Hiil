import asyncio
import io
import json
import re
import threading
import hashlib
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
    provenance: dict[str, dict] = Field(default_factory=dict, max_length=10)


class GenerateInput(BaseModel):
    revision: int = Field(ge=0)
    reviewed: Literal[True]


def require_case(case_id):
    if not store.get(case_id):
        raise HTTPException(404, 'Dossier introuvable.')


def require_editable(case_id):
    require_case(case_id)
    if store.get(case_id)['status'] in ('submitted', 'reviewed'):
        raise HTTPException(409, 'Ce dossier est en revue. Une demande de correction est nécessaire avant modification.')


def connection():
    db = store.connect()
    db.execute('CREATE TABLE IF NOT EXISTS f005_drafts (case_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    return db


def load(case_id):
    with closing(connection()) as db:
        row = db.execute('SELECT payload FROM f005_drafts WHERE case_id = ?', (case_id,)).fetchone()
    return json.loads(row[0]) if row else dict(revision=0, fields={}, modifications=[],
        same_person=False, step=0, generated_revision=None, imports=[], provenance={})


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
        applicable = not f.get('visible_when') or bool(set(f['visible_when']) & set(modifications))
        if not applicable:
            continue
        needed = f['required'] or bool(set(f.get('required_when', [])) & set(modifications))
        if not value:
            if needed:
                errors[key] = 'Ce renseignement est nécessaire.'
            continue
        if len(value) > f['max_length'] or '\n' in value or '\r' in value:
            errors[key] = f'Utilisez au maximum {f["max_length"]} caractères sur une ligne.'
        elif key == 'identifiant_unique' and not re.fullmatch(r'[0-9]{7}[A-Za-z]', value):
            errors[key] = 'Recopiez les 7 chiffres suivis de la lettre figurant sur votre pièce.'
        elif key.startswith('identite_') and not re.fullmatch(r'[A-Za-z0-9]+', value):
            errors[key] = 'Recopiez les chiffres et lettres du numéro de la pièce, sans espaces.'
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
            'provenance': draft.get('provenance', {}),
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
    draft = public(load(case_id))
    draft['locked'] = store.get(case_id)['status'] in ('submitted', 'reviewed')
    return draft


@router.post('/api/cases/{case_id}/f005')
def update_draft(case_id: str, body: DraftInput):
    require_editable(case_id)
    if set(body.fields) - FIELD_MAP.keys() or set(body.modifications) - MOD_MAP.keys():
        raise HTTPException(422, 'Champ ou type de modification inconnu.')
    if any(len(value) > 200 for value in body.fields.values()):
        raise HTTPException(422, 'Une valeur dépasse la longueur autorisée.')
    with store.LOCK:
        require_editable(case_id)
        draft = load(case_id)
        if body.revision != draft['revision']:
            raise HTTPException(409, 'Ce formulaire a changé dans une autre fenêtre. Rechargez la page avant de continuer.')
        fields = {k: v.strip() for k, v in body.fields.items()}
        for key, f in FIELD_MAP.items():
            if f.get('visible_when') and not set(f['visible_when']) & set(body.modifications):
                fields.pop(key, None)
        modifications = list(dict.fromkeys(body.modifications))
        changed = fields != draft['fields'] or modifications != draft['modifications'] or body.same_person != draft['same_person']
        verified_provenance = {}
        case = store.get(case_id)
        for key, proof in body.provenance.items():
            doc = next((d for d in case['documents'] if d['id'] == proof.get('document_id')), None)
            page = next((p for p in (doc or {}).get('pages', []) if p['page'] == proof.get('page')), None)
            evidence = proof.get('evidence', '')
            value = fields.get(key, '')
            if page and value and evidence and form_ocr.norm(evidence) in form_ocr.norm(page['text']) and form_ocr.norm(value) in form_ocr.norm(evidence):
                verified_provenance[key] = {'document_id': doc['id'], 'page': page['page'], 'evidence': evidence, 'value': value}
        draft.update(fields=fields, modifications=modifications, same_person=body.same_person, provenance=verified_provenance,
                     step=body.step, revision=draft['revision'] + int(changed),
                     generated_revision=None if changed else draft['generated_revision'])
        save(case_id, draft)
    return public(draft)


@router.post('/api/cases/{case_id}/f005/ocr')
async def read_ocr(case_id: str, file: UploadFile = File(...), kind: str = Form(...)):
    require_editable(case_id)
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
    return await analyze_upload(case_id, content, mime, name, kind)


async def analyze_upload(case_id, content, mime, name, kind, document_id=None):
    require_editable(case_id)
    digest = hashlib.sha256(content).hexdigest()
    # Store once before the provider call: a provider failure must not lose the upload.
    with store.LOCK:
        case = store.get(case_id)
        doc = next((d for d in case['documents'] if d['id'] == document_id or d.get('sha256') == digest), None)
        if not doc:
            if len(case['documents']) >= 24:
                raise HTTPException(422, 'La limite de 24 pièces par dossier est atteinte.')
            doc_id = uuid4().hex
            folder = config.DATA / 'uploads'
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / doc_id
            path.write_bytes(content)
            doc = dict(id=doc_id, name=name, filename=name, content_type=mime, file_path=str(path), sample=False,
                       sha256=digest, kind=kind, status='pending', method='not_analyzed', pages=[], text='', fields=[])
            case['documents'].append(doc)
            store.event(case, 'Pièce ajoutée', detail=name)
            store.save(case)
        document_id = doc['id']
    try:
        async with OCR_SLOTS:
            result = await form_ocr.extract(content, mime, kind, scope=case_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    except Exception:
        raise HTTPException(502, 'La lecture a échoué. Réessayez avec une image nette ou remplissez les champs à la main.') from None
    batch_id = uuid4().hex
    batch = dict(id=batch_id, document_id=document_id, name=name, kind=kind, mime=mime, **result)
    with store.LOCK:
        require_editable(case_id)
        case = store.get(case_id)
        doc = next(d for d in case['documents'] if d['id'] == document_id)
        previous_facts = list(doc['fields'])
        doc.update(pages=result['pages'], text='\n\n'.join(p['text'] for p in result['pages']), method=result['method'],
                   status='extracted' if result['candidates'] or result.get('facts') else 'needs_review', kind=kind,
                   form_candidates=result['candidates'], warnings=result['warnings'], duration_ms=result['duration_ms'])
        mapping = {'identifiant_unique': 'company_id', 'representant_legal': 'representative'}
        fact_keys = {f['key'] for f in result.get('facts', [])}
        preserved = [f for f in doc['fields'] if f['key'] not in mapping.values() and f['key'] not in fact_keys]
        doc['fields'] = preserved + [{**f, 'key': mapping[f['key']]} for f in result['candidates'] if f['key'] in mapping]
        doc['fields'].extend(result.get('facts', []))
        for key in list(case['confirmations']):
            before = sorted(f['value'] for f in previous_facts if f['key'] == key)
            after = sorted(f['value'] for f in doc['fields'] if f['key'] == key)
            if before != after:
                del case['confirmations'][key]
        store.event(case, 'Lecture de la pièce terminée', detail=f"{name} · {len(result['candidates'])} suggestion(s)")
        store.save(case)
        draft = load(case_id)
        draft['imports'] = (draft['imports'] + [batch])[-10:]
        save(case_id, draft)  # OCR does not alter fields or their revision.
    return batch


class ExistingDocumentInput(BaseModel):
    document_id: str
    kind: str


@router.post('/api/cases/{case_id}/f005/import')
async def import_document(case_id: str, body: ExistingDocumentInput):
    require_editable(case_id)
    if body.kind not in form_ocr.ALLOWED:
        raise HTTPException(422, 'Type de pièce inconnu.')
    doc = next((d for d in store.get(case_id)['documents'] if d['id'] == body.document_id), None)
    if not doc or not doc.get('file_path'):
        raise HTTPException(422, 'Ajoutez une pièce originale pour la lire dans le formulaire.')
    return await analyze_upload(case_id, Path(doc['file_path']).read_bytes(), doc['content_type'], doc['name'], body.kind, doc['id'])


@router.get('/api/cases/{case_id}/f005/ocr/{batch_id}')
def original_upload(case_id: str, batch_id: str):
    require_case(case_id)
    batch = next((b for b in load(case_id)['imports'] if b['id'] == batch_id), None)
    if not batch:
        raise HTTPException(404, 'Document introuvable.')
    if batch.get('document_id'):
        doc = next((d for d in store.get(case_id)['documents'] if d['id'] == batch['document_id']), None)
        if doc and doc.get('file_path'):
            return FileResponse(doc['file_path'], media_type=doc['content_type'], filename=doc['filename'], content_disposition_type='inline')
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
    cache_dir = config.DATA / 'form-previews' / case_id
    # Data revisions, never navigation, define the preview cache.
    template_version = hashlib.sha256(form_pdf.TEMPLATE.read_bytes()).hexdigest()[:12]
    cache_path = cache_dir / f'{draft["revision"]}-{page}-{template_version}-v2.png'
    if cache_path.is_file():
        return FileResponse(cache_path, media_type='image/png')
    with PDF_LOCK:
        import pypdfium2 as pdfium
        pdf = form_pdf.render(fields, draft['modifications'], draft=True)
        doc = pdfium.PdfDocument(pdf)
        image = doc[page - 1].render(scale=1.5).to_pil()
        data = io.BytesIO()
        image.save(data, format='PNG')
        image.close()
        doc.close()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(data.getvalue())
    return Response(data.getvalue(), media_type='image/png', headers={'Cache-Control': 'no-store'})


@router.post('/api/cases/{case_id}/f005/generate')
def generate(case_id: str, body: GenerateInput):
    require_editable(case_id)
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
