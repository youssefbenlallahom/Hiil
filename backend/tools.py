"""Custom CrewAI tools for the F005 address-change flow.

Three tools:
1. GetCaseDataTool   — reads case data from the existing store
2. LookupFormTool    — returns form requirements for a scenario
3. FillRNEF005Tool   — generates a pre-filled PDF
"""

from __future__ import annotations

import copy
import io
import re
from datetime import date
from pathlib import Path
from typing import Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from backend import store
from backend.form_schema import (
    SCENARIOS,
    all_fields,
    get_field,
    get_modification_type,
    get_scenario,
    missing_fields,
)


# ── 1. Get case data ───────────────────────────────────────────────

class GetCaseDataInput(BaseModel):
    case_id: str = Field(description='The case identifier, e.g. DOS-026.')


class GetCaseDataTool(BaseTool):
    name: str = 'get_case_data'
    description: str = (
        'Retrieve the current state of a case (dossier): '
        'company name, documents, extracted fields, and confirmations. '
        'Use this to see what information is already available.'
    )
    args_schema: type[BaseModel] = GetCaseDataInput

    def _run(self, case_id: str) -> str:
        case = store.get(case_id)
        if not case:
            return f'Dossier {case_id} introuvable.'
        # Build a summary the agent can read
        lines = [
            f'Dossier: {case["id"]}',
            f'Entreprise: {case["company"]}',
            f'Statut: {case["status"]}',
            f'Documents ({len(case["documents"])}):',
        ]
        for doc in case['documents']:
            fields_summary = ', '.join(
                f'{f["key"]}={f["value"]}' for f in doc['fields']
            )
            lines.append(
                f'  - {doc["name"]} ({doc["kind"]}, {doc["status"]})'
                + (f' → champs: {fields_summary}' if fields_summary else '')
            )
        if case['confirmations']:
            lines.append('Confirmations:')
            for key, conf in case['confirmations'].items():
                lines.append(f'  - {key}: {conf["value"]}')
        return '\n'.join(lines)


# ── 2. Lookup form requirements ────────────────────────────────────

class LookupFormInput(BaseModel):
    scenario_key: str = Field(
        default='',
        description=(
            'The scenario key (e.g. "changement_siege" or "changement_succursale"). '
            'Leave empty to list all available scenarios.'
        ),
    )
    collected_fields: dict[str, str] = Field(
        default_factory=dict,
        description='Fields already collected, as key→value pairs.',
    )


class LookupFormTool(BaseTool):
    name: str = 'lookup_form_requirements'
    description: str = (
        'Look up the fields required for a specific F005 modification scenario. '
        'Returns which fields are still missing and their descriptions. '
        'Call with an empty scenario_key to see all available scenarios.'
    )
    args_schema: type[BaseModel] = LookupFormInput

    def _run(
        self,
        scenario_key: str = '',
        collected_fields: dict[str, str] | None = None,
    ) -> str:
        collected = collected_fields or {}
        if not scenario_key:
            lines = ['Scénarios disponibles :']
            for s in SCENARIOS:
                lines.append(f'  - {s.key}: {s.label_fr}')
            return '\n'.join(lines)

        scenario = get_scenario(scenario_key)
        if not scenario:
            raise ValueError(f'Scénario inconnu : {scenario_key}')

        mod = get_modification_type(scenario.modification_type)
        lines = [
            f'Scénario : {scenario.label_fr}',
            f'Case à cocher : {mod.label_fr if mod else "?"}',
            '',
            'Champs requis :',
        ]
        still_missing = missing_fields(collected, scenario_key)
        for f in all_fields():
            if f.key in scenario.required_fields:
                status = '✓' if f.key in collected else '○'
                lines.append(
                    f'  {status} {f.label_fr} ({f.key})'
                    + (f' — {f.explanation}' if f.explanation else '')
                )

        if still_missing:
            lines.append(f'\n{len(still_missing)} champ(s) manquant(s).')
        else:
            lines.append('\nTous les champs sont remplis.')

        return '\n'.join(lines)


# ── 3. Fill the RNE F005 PDF ──────────────────────────────────────

class FillFormInput(BaseModel):
    case_id: str = Field(description='The case identifier.')
    scenario_key: str = Field(description='The scenario key.')
    fields: dict[str, str] = Field(
        description='Confirmed field values to write onto the form.'
    )


class FillRNEF005Tool(BaseTool):
    name: str = 'fill_rne_f005'
    description: str = (
        'Generate a pre-filled RNE F005 PDF with the confirmed data. '
        'The PDF overlays text on the original blank form. '
        'Returns the path to the generated file.'
    )
    args_schema: type[BaseModel] = FillFormInput

    def _run(
        self,
        case_id: str,
        scenario_key: str,
        fields: dict[str, str],
    ) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        from backend.config import DATA

        scenario = get_scenario(scenario_key)
        if not scenario:
            raise ValueError(f'Scénario inconnu : {scenario_key}')

        # Output path
        output_dir = DATA / 'generated'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'{case_id}_F005.pdf'

        # Create a PDF overlay
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        page_width, page_height = A4  # 595.3 × 841.9

        # Register Unicode font for French & Arabic text
        font_name = 'Helvetica'
        for font_candidate in ['C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/Arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
            if Path(font_candidate).exists():
                try:
                    pdfmetrics.registerFont(TTFont('UnicodeFont', font_candidate))
                    font_name = 'UnicodeFont'
                    break
                except Exception:
                    pass

        def draw_checkmark(canvas_obj, cx: float, cy: float):
            canvas_obj.saveState()
            canvas_obj.setStrokeColorRGB(0.05, 0.15, 0.3)
            canvas_obj.setLineWidth(1.8)
            canvas_obj.setLineCap(1)  # round cap
            canvas_obj.setLineJoin(1)  # round join
            p = canvas_obj.beginPath()
            p.moveTo(cx - 4, cy)
            p.lineTo(cx - 1, cy - 3.5)
            p.lineTo(cx + 4.5, cy + 4)
            canvas_obj.drawPath(p, stroke=1, fill=0)
            canvas_obj.restoreState()

        def render_field(canvas_obj, form_field, val: str):
            canvas_obj.setFont(font_name, form_field.font_size)
            display = str(val)[:form_field.max_chars].strip()
            if not display:
                return

            if form_field.is_boxed and form_field.box_centers:
                clean_chars = re.sub(r'[\s\-]', '', display)
                if not clean_chars:
                    clean_chars = display
                centers = form_field.box_centers
                if len(clean_chars) <= len(centers):
                    for i, ch in enumerate(clean_chars):
                        canvas_obj.drawCentredString(centers[i], form_field.y, ch)
                else:
                    x_start = centers[0]
                    x_end = centers[-1]
                    step = (x_end - x_start) / (len(clean_chars) - 1)
                    for i, ch in enumerate(clean_chars):
                        canvas_obj.drawCentredString(x_start + i * step, form_field.y, ch)
            elif form_field.key == 'date' and form_field.page == 2:
                parts = re.findall(r'\d+', display)
                if len(parts) == 3:
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        year, month, day = parts[0], parts[1], parts[2]
                    else:  # DD/MM/YYYY or DD-MM-YYYY
                        day, month, year = parts[0], parts[1], parts[2]
                    canvas_obj.drawCentredString(131.45, form_field.y, day.zfill(2))
                    canvas_obj.drawCentredString(107.60, form_field.y, month.zfill(2))
                    canvas_obj.drawCentredString(76.14, form_field.y, year)
                else:
                    if form_field.mask_dots:
                        w = canvas_obj.stringWidth(display, font_name, form_field.font_size)
                        canvas_obj.saveState()
                        canvas_obj.setFillColorRGB(1, 1, 1)
                        canvas_obj.rect(form_field.x - 2, form_field.y - 2.5, w + 4, form_field.font_size + 3.5, fill=1, stroke=0)
                        canvas_obj.restoreState()
                    canvas_obj.setFillColorRGB(0.05, 0.05, 0.1)
                    canvas_obj.drawString(form_field.x, form_field.y, display)
            else:
                if form_field.mask_dots:
                    w = canvas_obj.stringWidth(display, font_name, form_field.font_size)
                    canvas_obj.saveState()
                    canvas_obj.setFillColorRGB(1, 1, 1)
                    canvas_obj.rect(form_field.x - 2, form_field.y - 2.5, w + 4, form_field.font_size + 3.5, fill=1, stroke=0)
                    canvas_obj.restoreState()
                canvas_obj.setFillColorRGB(0.05, 0.05, 0.1)
                canvas_obj.drawString(form_field.x, form_field.y, display)

        # ── Page 1: fill text fields & modification checkbox ──
        for field_key, value in fields.items():
            form_field = get_field(field_key)
            if not form_field or form_field.page != 1:
                continue
            render_field(c, form_field, value)

        mod = get_modification_type(scenario.modification_type)
        if mod:
            draw_checkmark(c, mod.check_x, mod.check_y)

        c.showPage()

        # ── Page 2: date and signature area ──
        for field_key, value in fields.items():
            form_field = get_field(field_key)
            if not form_field or form_field.page != 2:
                continue
            render_field(c, form_field, value)

        c.showPage()
        c.save()

        # Merge overlay with original PDF
        try:
            from pypdf import PdfReader, PdfWriter
            original_path = Path(__file__).parent / 'assets' / 'RNE-F-005.pdf'
            if not original_path.exists():
                raise FileNotFoundError('Le formulaire RNE F005 original est absent.')

            original = PdfReader(str(original_path))
            overlay = PdfReader(buf)
            writer = PdfWriter()

            for i, page in enumerate(original.pages):
                if i < len(overlay.pages):
                    page.merge_page(overlay.pages[i])
                writer.add_page(page)

            with open(output_path, 'wb') as f:
                writer.write(f)
        except Exception:
            raise RuntimeError('Impossible de fusionner les données avec le formulaire original.') from None

        return str(output_path)
