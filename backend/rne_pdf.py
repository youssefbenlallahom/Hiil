"""Fixed coordinates for the supplied, flat RNE F005 v1.1. No model coordinates."""
import hashlib
import io
from pathlib import Path
import re
import threading

import arabic_reshaper
from bidi.algorithm import get_display
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from backend.rne_knowledge import blockers
from backend.rne_models import RneState

ASSETS = Path(__file__).parent / 'assets'
TEMPLATE = ASSETS / 'rne-f005-v1.1.pdf'
TEMPLATE_SHA256 = 'ef9fcf5544e3bf20b3148fd46dce94005e7570e9fe583e435b2e4ef2e6c567fb'
FONT_LOCK = threading.Lock()


def render_f005(state: RneState) -> bytes:
    if problems := blockers(state):
        raise ValueError(' '.join(problems))
    source = TEMPLATE.read_bytes()
    if hashlib.sha256(source).hexdigest() != TEMPLATE_SHA256:
        raise ValueError('Le modèle F005 a changé : le placement des rubriques doit être revérifié.')
    with FONT_LOCK:
        if 'RneAmiri' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('RneAmiri', str(ASSETS / 'Amiri-Regular.ttf')))
    reader = PdfReader(io.BytesIO(source))
    width, height = float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height)
    layer = io.BytesIO()
    pdf = canvas.Canvas(layer, pagesize=(width, height))
    pdf.setFillColorRGB(0.04, 0.10, 0.16)

    def text(key, x, y, max_width, size=11):
        value = state.values[key].value
        arabic = bool(re.search(r'[\u0600-\u06ff]', value))
        drawn = get_display(arabic_reshaper.reshape(value)) if arabic else value
        font = 'RneAmiri' if arabic else 'Helvetica'
        needed = pdfmetrics.stringWidth(drawn, font, size)
        size = min(size, size * max_width / max(needed, 1))
        if size < 8:
            raise ValueError('La valeur de ' + key + ' ne tient pas dans la rubrique ; une vérification manuelle du formulaire est nécessaire.')
        pdf.setFont(font, size)
        (pdf.drawRightString if arabic else pdf.drawString)(x + max_width if arabic else x, y, drawn)

    def boxes(key, start, step, y):
        pdf.setFont('Helvetica', 12)
        for i, char in enumerate(state.values[key].value):
            pdf.drawCentredString(start + i * step, y, char)

    # Coordinates in PDF points (origin bottom left), measured against the original.
    boxes('company_id', 193.5, 28.7, 685)
    text('representative_name', 127, 543, 355, 13)
    boxes('representative_id', 203, 18.3, 514)
    text('email', 60, 489, 427)
    text('phone', 68, 466, 415)
    text('declarant_name', 125, 444, 345, 13)
    text('declarant_id', 158, 421, 300, 12)
    # تغيير عنوان المقر الاجتماعي, right column, third checkbox.
    pdf.setStrokeColorRGB(0.04, 0.10, 0.16)
    pdf.setLineWidth(1.6)
    pdf.line(565, 291, 575, 301)
    pdf.line(565, 301, 575, 291)
    pdf.showPage()
    pdf.save()
    overlay = PdfReader(io.BytesIO(layer.getvalue()))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.pages[0].merge_page(overlay.pages[0])
    writer.add_metadata({'/Title': 'RNE F005 - Declaration preparee', '/Subject': 'Donnees confirmees par le declarant. Signature et date a completer. Aucun depot officiel.'})
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
