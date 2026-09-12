"""Retrieve from the actual versioned form, alongside reviewed interpretation notes."""
import hashlib
from functools import lru_cache
from pypdf import PdfReader
from backend.rne_knowledge import REFERENCES
from backend.rne_pdf import TEMPLATE, TEMPLATE_SHA256
from backend.sources import normalize


@lru_cache(maxsize=1)
def form_pages():
    if hashlib.sha256(TEMPLATE.read_bytes()).hexdigest() != TEMPLATE_SHA256:
        raise ValueError('La version du formulaire doit être revue avant consultation.')
    return [{'page': i + 1, 'text': p.extract_text() or ''} for i, p in enumerate(PdfReader(TEMPLATE).pages)]


def retrieve_reference(topic):
    terms = set(normalize(topic).split())
    notes = sorted(REFERENCES, key=lambda r: len(terms & set(normalize(r['title'] + ' ' + r['text']).split())), reverse=True)
    return {'source': {'title': 'RNE F005, version 1.1 fournie', 'url': '/api/rne/template',
        'sha256': TEMPLATE_SHA256, 'reviewed_at': '2026-09-12'},
        'form_pages': form_pages(), 'interpretation_notes': notes,
        'scope': 'Le texte du formulaire fait foi pour ses rubriques. Les notes de conception ne sont pas des obligations réglementaires. Aucune liste exhaustive des justificatifs n’est déduite du formulaire.'}
