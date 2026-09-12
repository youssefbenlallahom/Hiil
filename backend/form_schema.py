"""RNE F005 form field definitions and modification-type reference.

Based on visual inspection of the official RNE F 005 v1.1 (2 pages).
This schema describes the fields the conversational agent must collect,
their positions on the PDF, and explanatory notes for the user.

The PDF is static (no interactive fields).  The fill tool places text
at the absolute coordinates listed below.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

# ── Coordinate system ──────────────────────────────────────────────
# Origin is bottom-left of the A4 page (595.3 × 841.9 pt).
# All x/y values are in PDF points (1 pt = 1/72 inch).

# ── Page 1 fields ──────────────────────────────────────────────────

@dataclass
class FormField:
    key: str
    label_fr: str
    label_ar: str
    required: bool
    page: int
    x: float
    y: float
    font_size: float = 10.0
    max_chars: int = 60
    explanation: str = ''
    is_boxed: bool = False
    box_centers: list[float] = field(default_factory=list)
    mask_dots: bool = False


# Fields on page 1 of the F005
PAGE1_FIELDS: list[FormField] = [
    FormField(
        key='identifiant_unique',
        label_fr='Identifiant unique',
        label_ar='المعرّف الوحيد',
        required=True,
        page=1,
        x=178.4, y=686.0,
        font_size=11,
        max_chars=20,
        is_boxed=True,
        box_centers=[193.40, 223.27, 251.93, 279.88, 308.33, 335.88, 364.15, 393.96],
        explanation='Numéro unique attribué par le RNE lors de l\'immatriculation.',
    ),
    FormField(
        key='certificat_reservation',
        label_fr='N° certificat de réservation (le cas échéant)',
        label_ar='رقم شهادة الحجز عند الإقتضاء',
        required=False,
        page=1,
        x=105, y=633,
        font_size=10,
        max_chars=20,
        explanation='Numéro de réservation de la dénomination, si applicable.',
    ),
    FormField(
        key='rib',
        label_fr='RIB en cas de modification',
        label_ar='المعرف البنكي في حالة تغييره',
        required=False,
        page=1,
        x=45, y=573,
        font_size=10,
        max_chars=24,
        explanation='Relevé d\'identité bancaire, uniquement si le compte change.',
    ),
    FormField(
        key='representant_legal',
        label_fr='Représentant légal',
        label_ar='الممثل القانوني',
        required=True,
        page=1,
        x=126.0, y=534.5,
        font_size=10,
        max_chars=60,
        mask_dots=True,
        explanation='Nom complet du représentant légal de la société.',
    ),
    FormField(
        key='identite_representant',
        label_fr='N° Identité',
        label_ar='رقم الهوية',
        required=True,
        page=1,
        x=193.7, y=512.5,
        font_size=11,
        max_chars=15,
        is_boxed=True,
        box_centers=[202.68, 220.64, 238.64, 256.64, 275.14, 293.64, 311.64, 329.64, 347.64, 366.14, 385.27],
        explanation='Numéro de carte d\'identité nationale (CIN) du représentant légal.',
    ),
    FormField(
        key='email',
        label_fr='E-mail',
        label_ar='البريد الإلكتروني',
        required=True,
        page=1,
        x=58.0, y=481.5,
        font_size=10,
        max_chars=50,
        mask_dots=True,
        explanation='Adresse e-mail pour le suivi du dossier. Obligatoire.',
    ),
    FormField(
        key='gsm',
        label_fr='N° GSM',
        label_ar='الهاتف الجوال',
        required=True,
        page=1,
        x=64.0, y=459.5,
        font_size=10,
        max_chars=25,
        mask_dots=True,
        explanation='Numéro de téléphone mobile pour le suivi du dossier. Obligatoire.',
    ),
    FormField(
        key='nom_declarant',
        label_fr='Nom du déclarant',
        label_ar='إسم و لقب المصرح',
        required=True,
        page=1,
        x=118.0, y=436.5,
        font_size=10,
        max_chars=60,
        mask_dots=True,
        explanation=(
            'Le déclarant peut être différent du représentant légal. '
            'Si vous êtes le gérant et que vous déclarez vous-même, '
            'indiquez votre nom dans les deux champs.'
        ),
    ),
    FormField(
        key='identite_declarant',
        label_fr='N° Identité du déclarant',
        label_ar='رقم بطاقة هوية المصرح',
        required=True,
        page=1,
        x=156.0, y=412.5,
        font_size=10,
        max_chars=20,
        mask_dots=True,
        explanation='Numéro CIN du déclarant.',
    ),
]

# ── Page 2 fields ──────────────────────────────────────────────────

PAGE2_FIELDS: list[FormField] = [
    FormField(
        key='date',
        label_fr='Date',
        label_ar='التاريخ',
        required=True,
        page=2,
        x=65.0, y=483.0,
        font_size=10,
        max_chars=20,
        explanation='Date de la déclaration au format JJ / MM / AAAA.',
    ),
]


# ── Modification type checkboxes ───────────────────────────────────
# The form has a grid of checkboxes for 28 modification types.
# For the address-change scenario, two are relevant:
#   - تغيير عنوان المقر الإجتماعي (Changement d'adresse du siège social)
#   - تغيير عنوان الفرع (Changement d'adresse de la succursale)

@dataclass
class ModificationType:
    key: str
    label_fr: str
    label_ar: str
    # Checkbox center coordinates on page 1
    check_x: float
    check_y: float
    explanation: str = ''


MODIFICATION_TYPES: list[ModificationType] = [
    ModificationType(
        key='changement_denomination',
        label_fr='Changement de la dénomination sociale, du nom commercial ou de l\'enseigne',
        label_ar='تغيير التسمية الإجتماعية أو الإسم التجاري أو الشارة',
        check_x=571.7, check_y=362.9,
    ),
    ModificationType(
        key='changement_adresse_siege',
        label_fr='Changement d\'adresse du siège social',
        label_ar='تغيير عنوان المقر الإجتماعي',
        check_x=571.8, check_y=296.5,
        explanation=(
            'Le siège social est l\'adresse officielle de la société, '
            'celle qui figure sur l\'extrait du Registre National des Entreprises. '
            'C\'est l\'adresse principale de la société.'
        ),
    ),
    ModificationType(
        key='ouverture_succursale',
        label_fr='Ouverture d\'une succursale',
        label_ar='فتح فرع',
        check_x=374.8, check_y=329.0,
    ),
    ModificationType(
        key='changement_adresse_succursale',
        label_fr='Changement d\'adresse de la succursale',
        label_ar='تغيير عنوان الفرع',
        check_x=105.9, check_y=329.0,
        explanation=(
            'Une succursale est un établissement secondaire — '
            'un bureau, un atelier ou un local commercial rattaché à la société, '
            'mais situé à une adresse différente du siège social.'
        ),
    ),
    ModificationType(
        key='changement_activite',
        label_fr='Changement, ajout ou suppression d\'activité',
        label_ar='تغيير أو إضافة أو حذف نشاط',
        check_x=374.8, check_y=366.9,
    ),
    ModificationType(
        key='fermeture_succursale',
        label_fr='Fermeture d\'une succursale',
        label_ar='غلق فرع',
        check_x=238.4, check_y=329.0,
    ),
]

# ── Scenario definitions ───────────────────────────────────────────

@dataclass
class Scenario:
    key: str
    label_fr: str
    modification_type: str          # key into MODIFICATION_TYPES
    required_fields: list[str]      # keys into PAGE1_FIELDS / PAGE2_FIELDS
    clarification_question: str     # question to ask when ambiguous
    clarification_explain: str      # explanation for the user


SCENARIOS = [
    Scenario(
        key='changement_siege',
        label_fr='Changement d\'adresse du siège social',
        modification_type='changement_adresse_siege',
        required_fields=[
            'identifiant_unique',
            'representant_legal',
            'identite_representant',
            'email',
            'gsm',
            'nom_declarant',
            'identite_declarant',
            'date',
        ],
        clarification_question=(
            'Ce changement concerne le siège social de votre société '
            'ou une succursale (un établissement secondaire) ?'
        ),
        clarification_explain=(
            'Le formulaire distingue ces deux types de changement. '
            'Le siège social est l\'adresse officielle de la société, '
            'inscrite au Registre National des Entreprises. '
            'Une succursale est un local ou bureau secondaire.'
        ),
    ),
    Scenario(
        key='changement_succursale',
        label_fr='Changement d\'adresse d\'une succursale',
        modification_type='changement_adresse_succursale',
        required_fields=[
            'identifiant_unique',
            'representant_legal',
            'identite_representant',
            'email',
            'gsm',
            'nom_declarant',
            'identite_declarant',
            'date',
        ],
        clarification_question=(
            'Confirmez que l\'adresse qui change est celle d\'une succursale '
            '(un établissement secondaire), pas celle du siège social.'
        ),
        clarification_explain=(
            'Le siège social est l\'adresse principale de la société. '
            'Si c\'est l\'adresse du siège qui change, choisissez '
            '"changement d\'adresse du siège social" à la place.'
        ),
    ),
]


def get_scenario(key: str) -> Scenario | None:
    return next((s for s in SCENARIOS if s.key == key), None)


def get_modification_type(key: str) -> ModificationType | None:
    return next((m for m in MODIFICATION_TYPES if m.key == key), None)


def get_field(key: str) -> FormField | None:
    for f in PAGE1_FIELDS + PAGE2_FIELDS:
        if f.key == key:
            return f
    return None


def all_fields() -> list[FormField]:
    return PAGE1_FIELDS + PAGE2_FIELDS


def missing_fields(collected: dict[str, str], scenario_key: str) -> list[FormField]:
    """Return form fields still needed for a scenario."""
    scenario = get_scenario(scenario_key)
    if not scenario:
        return []
    return [
        f for f in all_fields()
        if f.key in scenario.required_fields and not collected.get(f.key, '').strip()
    ]
