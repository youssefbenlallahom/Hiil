"""Render a static, unsigned F005 on the original supplied form."""
import io
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from backend.form_catalog import MOD_MAP

TEMPLATE = Path(__file__).parent / 'assets' / 'RNE-F-005.pdf'


def font():
    if 'FormUnicode' in pdfmetrics.getRegisteredFontNames():
        return 'FormUnicode'
    for path in ['C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(path).is_file():
            pdfmetrics.registerFont(TTFont('FormUnicode', path))
            return 'FormUnicode'
    raise RuntimeError('Installez Arial ou DejaVu Sans pour générer le formulaire bilingue.')


def display_text(value):
    if re.search(r'[\u0600-\u06ff]', value):
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(value))
    return value


def render(fields, modifications, draft=False):
    original = PdfReader(TEMPLATE)
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(595.28, 841.89))
    face = font()
    c.setFillColorRGB(.12, .16, .29)
    c.setFont(face, 10)

    def boxed(key, left, right, count, y):
        raw = fields.get(key, '')
        value = re.sub(r'[\s\-]', '', raw)[:count]
        for i, char in enumerate(value):
            c.drawCentredString(left + (i + .5) * (right - left) / count, y, char)

    boxed('identifiant_unique', 178.4, 408.3, 8, 686.0)
    boxed('certificat_reservation', 98.4, 502.8, 14, 633.0)
    boxed('rib', 35.8, 557.9, 20, 573.0)
    boxed('identite_representant', 193.73, 394.89, 11, 512.5)

    for key, left, right, y in [
        ('representant_legal', 126, 486, 534.5),
        ('email', 58, 482, 481.5),
        ('gsm', 64, 490, 459.5),
        ('nom_declarant', 118, 478, 436.5),
        ('identite_declarant', 156, 457, 412.5),
    ]:
        raw_val = fields.get(key, '').strip()
        if not raw_val:
            continue
        value = display_text(raw_val)
        size = 10
        while pdfmetrics.stringWidth(value, face, size) > right - left and size > 6:
            size -= .25
        if pdfmetrics.stringWidth(value, face, size) > right - left:
            continue
        text_width = pdfmetrics.stringWidth(value, face, size)
        c.setFillColorRGB(1, 1, 1)
        if re.search(r'[\u0600-\u06ff]', raw_val):
            c.rect(right - text_width - 3, y - 2.5, text_width + 5, 12, fill=1, stroke=0)
        else:
            c.rect(left - 2, y - 2.5, text_width + 5, 12, fill=1, stroke=0)
        c.setFillColorRGB(.12, .16, .29)
        c.setFont(face, size)
        if re.search(r'[\u0600-\u06ff]', raw_val):
            c.drawRightString(right, y, value)
        else:
            c.drawString(left, y, value)

    c.setStrokeColorRGB(.05, .15, .30)
    c.setLineWidth(1.8)
    c.setLineCap(1)
    c.setLineJoin(1)
    for key in modifications:
        m = MOD_MAP.get(key)
        if not m:
            continue
        p = c.beginPath()
        p.moveTo(m['x'] - 4, m['y'])
        p.lineTo(m['x'] - 1, m['y'] - 3.5)
        p.lineTo(m['x'] + 4.5, m['y'] + 4)
        c.drawPath(p, stroke=1, fill=0)

    def draft_mark():
        if draft:
            c.saveState()
            c.setFillColorRGB(.35, .34, .58)
            c.setFont(face, 9)
            c.drawString(30, 65, 'APERÇU — BROUILLON NON SIGNÉ')
            c.restoreState()

    draft_mark()
    c.showPage()
    c.setFont(face, 10)
    c.setFillColorRGB(.12, .16, .29)
    value = fields.get('date', '').strip()
    if value:
        parts = re.findall(r'\d+', value)
        if len(parts) == 3:
            if len(parts[0]) == 4:
                year, month, day = parts[0], parts[1], parts[2]
            else:
                day, month, year = parts[0], parts[1], parts[2]
            for text, x in [(day.zfill(2), 131.45), (month.zfill(2), 107.60), (year, 76.14)]:
                c.drawCentredString(x, 483.0, text)
    draft_mark()
    c.showPage()
    c.save()
    out.seek(0)
    overlay = PdfReader(out)
    writer = PdfWriter(clone_from=original)
    for i, page in enumerate(writer.pages):
        page.merge_page(overlay.pages[i])
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()
