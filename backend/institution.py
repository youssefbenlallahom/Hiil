"""Local institutional handoff: immutable submission snapshot and auditable decisions."""
import base64
import io
from uuid import uuid4
from typing import Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend import store
from backend.evidence import report, fingerprint
from backend.rne_flow import load_state
from backend.rne_knowledge import blockers, REFERENCES
from backend.rne_models import RneState
from backend.rne_pdf import render_f005

router = APIRouter(prefix='/api')


class Submission(BaseModel):
    revision: int = Field(ge=0)
    signature: str = Field(min_length=64, max_length=64)


class Decision(BaseModel):
    submission_id: str
    action: Literal['request_correction', 'reviewed']
    note: str = Field(min_length=5, max_length=2000)
    check_ids: list[str] = Field(default_factory=list, max_length=20)


def required(case_id):
    case = store.get(case_id)
    if not case or not case.get('rne'):
        raise HTTPException(404, 'Déclaration introuvable.')
    return case


def _qr_data_url(text: str) -> str:
    """Generate a small QR code as a data:image/png;base64 URL."""
    import qrcode
    img = qrcode.make(text, box_size=4, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def public_handoff(case):
    handoff = case.get('institution')
    if not handoff:
        return None
    result = {**handoff, 'case_id': case['id'], 'company': case['company'], 'status': case['status'], 'sample': case['sample']}
    # Attach QR code pointing to the verification page
    if handoff.get('submission_id'):
        result['qr_url'] = handoff.get('qr_url', '')
    return result


@router.get('/institution/queue')
def queue():
    return [public_handoff(c) for c in store.all_cases() if c.get('institution')]


@router.post('/cases/{case_id}/rne/submit')
def submit(case_id: str, body: Submission):
    with store.LOCK:
        case = required(case_id)
        state = load_state(case)
        if state.revision != body.revision or fingerprint(case) != body.signature:
            raise HTTPException(409, 'Les informations ont changé. Relisez le récapitulatif avant de transmettre.')
        if case['status'] == 'submitted' and case.get('institution', {}).get('signature') == body.signature:
            return public_handoff(case)
        if case['status'] in ('submitted', 'reviewed'):
            raise HTTPException(409, 'La déclaration est déjà en revue.')
        if blockers(state) or state.pdf_revision != state.revision:
            raise HTTPException(409, 'Confirmez les rubriques et préparez le F005 avant la revue.')
        evidence = report(case)
        if evidence['counts']['attention'] or evidence['counts']['cross_attention']:
            raise HTTPException(409, 'Résolvez les écarts signalés dans les preuves avant la revue.')
        if case.get('correction', {}).get('pending'):
            raise HTTPException(409, 'Répondez à la demande de correction avant de retransmettre.')
        previous = case.get('institution')
        history = (previous.get('history', []) + [{k: v for k, v in previous.items() if k != 'history'}]) if previous else []
        submission_id = 'REV-' + uuid4().hex[:10].upper()
        qr_url = _qr_data_url('/verify/' + submission_id)
        case['institution'] = {'submission_id': submission_id, 'submitted_at': store.now(),
            'revision': state.revision, 'signature': evidence['signature'],
            'snapshot': state.model_dump(exclude={'processed_requests', 'messages'}), 'report': evidence,
            'references': REFERENCES, 'decision': None, 'history': history, 'mode': 'local_simulation',
            'qr_url': qr_url}
        case['status'] = 'submitted'
        store.event(case, 'Déclaration F005 transmise à la revue locale', 'Entreprise', 'Instantané figé ' + submission_id)
        store.save(case)
    return public_handoff(case)


@router.post('/cases/{case_id}/rne/review')
def review(case_id: str, body: Decision):
    if len(body.note.strip()) < 5:
        raise HTTPException(422, 'Précisez votre observation.')
    with store.LOCK:
        case = required(case_id)
        handoff = case.get('institution')
        if not handoff or handoff['submission_id'] != body.submission_id or case['status'] != 'submitted':
            raise HTTPException(409, 'Cette version n’est plus en attente de revue. Actualisez la file.')
        allowed = {r['id'] for r in handoff['report']['rows'] + handoff['report']['cross_checks']}
        if not set(body.check_ids) <= allowed:
            raise HTTPException(422, 'La demande référence une rubrique inconnue.')
        if body.action == 'request_correction' and not body.check_ids:
            raise HTTPException(422, 'Sélectionnez au moins une rubrique à corriger.')
        handoff['decision'] = {'action': body.action, 'note': body.note.strip(), 'check_ids': body.check_ids,
            'at': store.now(), 'actor': 'Agent · simulation'}
        case['status'] = 'correction_requested' if body.action == 'request_correction' else 'reviewed'
        if body.action == 'request_correction':
            case['correction'] = {'note': body.note.strip(), 'at': store.now(), 'pending': True,
                'response': None, 'check_ids': body.check_ids, 'submission_id': body.submission_id}
        store.event(case, 'Correction ciblée demandée' if body.action == 'request_correction' else 'Revue de préparation terminée', 'Agent · simulation', body.note.strip())
        store.save(case)
    return public_handoff(case)


@router.get('/cases/{case_id}/rne/submissions/{submission_id}/pdf')
def submitted_pdf(case_id: str, submission_id: str):
    handoff = required(case_id).get('institution')
    versions = [handoff, *handoff.get('history', [])] if handoff else []
    version = next((v for v in versions if v['submission_id'] == submission_id), None)
    if not version:
        raise HTTPException(404, 'Version transmise introuvable.')
    content = render_f005(RneState.model_validate(version['snapshot']))
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition': f'inline; filename="{version["submission_id"]}-F005.pdf"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


@router.get('/institution/verify/{submission_id}')
def verify(submission_id: str):
    """Lightweight public verification — no CIN, no documents, no personal data."""
    for case in store.all_cases():
        handoff = case.get('institution')
        if not handoff:
            continue
        versions = [handoff, *handoff.get('history', [])]
        version = next((v for v in versions if v.get('submission_id') == submission_id), None)
        if version:
            decision = version.get('decision')
            return {
                'submission_id': submission_id,
                'company': case['company'],
                'status': case['status'],
                'submitted_at': version.get('submitted_at'),
                'revision': version.get('revision'),
                'signature': version.get('signature'),
                'engine_version': version.get('report', {}).get('engine_version'),
                'counts': version.get('report', {}).get('counts'),
                'scope': version.get('report', {}).get('scope'),
                'decision': {'action': decision['action'], 'note': decision['note'], 'at': decision['at']} if decision else None,
                'mode': 'local_simulation',
            }
    raise HTTPException(404, 'Aucune déclaration ne correspond à cet identifiant.')
