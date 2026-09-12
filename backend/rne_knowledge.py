"""Reviewed F005 facts and explicit product scope, not an exhaustive legal corpus."""
import re

FORM_URL = 'https://www.registre-entreprises.tn/rne-public/assets/pdfs/formulaires/RNE-F-005_declaration_modification_personne_morale.pdf'
REFERENCES = [
    {'id': 'rne-procedure-index', 'title': 'RNE · Procédure M 004.03', 'page': None, 'url': 'https://home.registre-entreprises.tn/formalites/',
     'checked_at': '2026-09-12', 'authority': 'Registre national des entreprises',
     'text': 'Le tableau officiel associe le transfert du siège social des sociétés au code RNE M 004.03. La ligne M 004.06 concerne le changement d’adresse d’une filiale. Cet index identifie les procédures ; sa consultation ne valide pas ici une liste exhaustive des justificatifs.'},
    {'id': 'f005-fields', 'title': 'RNE F005 · Rubriques', 'page': 1, 'url': '/api/rne/template',
     'text': 'La page 1 distingue identifiant unique, représentant légal et N° identité, e-mail, GSM, nom et N° identité du déclarant. Le numéro de certificat de réservation est conditionnel, le RIB concerne sa modification. Aucune zone ne détaille ancienne et nouvelle adresse.'},
    {'id': 'f005-choices', 'title': 'RNE F005 · Nature du changement', 'page': 1, 'url': '/api/rne/template',
     'text': 'Deux cases distinctes portent les libellés تغيير عنوان المقر الاجتماعي (changement de l’adresse du siège social) et تغيير عنوان الفرع (changement de l’adresse d’une succursale). Ne pas choisir entre elles à partir du seul mot « local ».'},
    {'id': 'f005-instructions', 'title': 'RNE F005 · Consignes', 'page': 2, 'url': '/api/rne/template',
     'text': 'Les consignes demandent des données en arabe, avec ajout facultatif du français. E-mail et GSM sont obligatoires. Plusieurs changements peuvent être déclarés ensemble. La signature appartient au déclarant ou à son mandataire.'},
    {'id': 'pilot-scope', 'title': 'Périmètre de ce premier parcours', 'page': None, 'url': None,
     'text': 'Choix de conception du prototype, sans valeur réglementaire : préparer seulement la case changement d’adresse du siège social sur F005. Demander la CIN du déclarant pour proposer son identité, sans authentifier la pièce ni son pouvoir de représentation. Les autres rubriques sont collectées auprès de l’utilisateur. La liste officielle exhaustive des pièces de transfert n’est pas encore vérifiée. Ne pas inventer obligations, justificatifs, tarifs ou délais. Si succursale, autre changement ou plusieurs changements : expliquer la limite et suspendre la préparation.'},
]
LABELS = {
    'company_id': 'Identifiant unique de la société',
    'declarant_name': 'Nom complet du déclarant (arabe)',
    'declarant_id': 'N° CIN du déclarant',
    'same_person': 'Le déclarant est-il le représentant légal ?',
    'representative_name': 'Nom du représentant légal (arabe)',
    'representative_id': 'N° identité du représentant légal',
    'email': 'E-mail de contact', 'phone': 'Numéro GSM',
}
MODIFICATIONS = [
    {'id': 'seat_address', 'label': 'Adresse du siège social', 'arabic': 'تغيير عنوان المقر الاجتماعي', 'supported': True},
    {'id': 'branch_address', 'label': 'Adresse d’une succursale', 'arabic': 'تغيير عنوان الفرع', 'supported': False},
    {'id': 'other', 'label': 'Autre ou plusieurs modifications', 'arabic': '', 'supported': False},
]


def field_error(key, value):
    value = value.strip()
    if not value:
        return 'Renseignez une valeur.'
    if key == 'same_person' and value not in ('yes', 'no'):
        return 'Choisissez oui ou non.'
    if key == 'declarant_id' and not re.fullmatch(r'[0-9]{8}', value):
        return 'La CIN de ce parcours doit contenir 8 chiffres, zéros initiaux compris.'
    if key == 'company_id' and not re.fullmatch(r'[A-Za-z0-9]{7,8}', value):
        return 'Recopiez l’identifiant unique (7 à 8 lettres/chiffres) dans les cases du formulaire.'
    if key == 'representative_id' and not re.fullmatch(r'[A-Za-z0-9]{5,11}', value):
        return 'Recopiez le numéro d’identité (5 à 11 lettres/chiffres, selon le document).'
    if key in ('representative_name', 'declarant_name') and not re.search(r'[\u0621-\u064a]', value):
        return 'Le formulaire demande le nom en arabe ; recopiez-le depuis la pièce.'
    if key in ('representative_name', 'declarant_name') and len(value) > 100:
        return 'Ce nom est trop long pour la rubrique du formulaire (100 caractères maximum).'
    if key == 'email' and (not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) or len(value) > 100):
        return 'Vérifiez l’adresse e-mail.'
    if key == 'phone' and not re.fullmatch(r'(?:\+216[ -]?)?[0-9](?:[ -]?[0-9]){7}', value):
        return 'Indiquez les 8 chiffres du GSM tunisien, avec +216 si souhaité.'
    return None


def blockers(state):
    problems = []
    if state.modification != 'seat_address':
        problems.append('Choisir le changement d’adresse du siège social pour ce premier parcours.')
    elif not state.modification_confirmed:
        problems.append('Confirmer la nature de la modification.')
    if not state.cin_document_id:
        problems.append('Joindre la CIN du déclarant pour ce parcours.')
    for key, label in LABELS.items():
        fact = state.values.get(key)
        if not fact:
            problems.append(label + ' : à compléter.')
        elif error := field_error(key, fact.value):
            problems.append(label + ' : ' + error)
        elif not fact.confirmed:
            problems.append(label + ' : à confirmer.')
    return problems


def stage(state):
    if state.modification is None:
        return 'clarification' if state.candidates else 'intent'
    if state.modification != 'seat_address':
        return 'out_of_scope'
    if not state.cin_document_id:
        return 'identity'
    if any(k not in state.values or field_error(k, state.values[k].value) for k in LABELS):
        return 'collecting'
    if blockers(state):
        return 'review'
    return 'prepared' if state.pdf_revision == state.revision else 'ready'
