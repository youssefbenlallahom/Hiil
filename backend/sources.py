"""Small, explicitly scoped source notes. These are not a complete legal corpus."""
import re
import unicodedata

SOURCES = [
    {
        'id': 'rne-procedure', 'title': 'RNE · Transfert du siège social',
        'url': 'https://home.registre-entreprises.tn/formalites/',
        'type': 'Index officiel des procédures', 'checked_at': '2026-09-12',
        'text': 'Le tableau des formalités RNE identifie le transfert du siège social des sociétés sous le code RNE M 004.03. Cette note identifie la procédure. La liste détaillée de ses pièces justificatives n’a pas encore été vérifiée dans ce prototype. Ne pas déduire une liste exhaustive de documents de cet index.',
    },
    {
        'id': 'rne-form', 'title': 'RNE F 005 · Déclaration de modification',
        'url': 'https://www.registre-entreprises.tn/rne-public/assets/pdfs/formulaires/RNE-F-005_declaration_modification_personne_morale.pdf',
        'type': 'Formulaire officiel · version 1.1 publiée', 'checked_at': '2026-09-12',
        'text': 'Le formulaire RNE F 005 est une déclaration de modification d’une société ou d’un établissement public. Il contient notamment l’identifiant unique, le représentant légal, le nom du déclarant, son identité, son e-mail et son numéro GSM. Ses instructions demandent de remplir les données en arabe, avec le français en complément facultatif. Ce prototype ne remplit pas encore toutes les rubriques du formulaire et ne vérifie pas l’authenticité des pièces.',
    },
    {
        'id': 'dgi-docs', 'title': 'DGI · Base documentaire Jibaya',
        'url': 'https://jibaya.tn/documentation/',
        'type': 'Portail de documentation fiscale', 'checked_at': '2026-09-12',
        'text': 'Jibaya propose une base documentaire fiscale. Aucun régime, taux ou calcul fiscal n’est validé dans le corpus de ce prototype. Pour une question fiscale, renvoyer à la documentation et signaler que ce sujet nécessite une vérification complémentaire. Ne pas inventer une obligation fiscale associée à un changement d’adresse.',
    },
]

def normalize(text: str) -> str:
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c)).split())

def retrieve(question: str):
    # Small corpus: select complete source notes using normalized lexical overlap.
    tokens = set(re.findall(r'\w+', normalize(question)))
    ranked = sorted(SOURCES, key=lambda s: len(tokens & set(re.findall(r'\w+', normalize(s['text'] + ' ' + s['title'])))), reverse=True)
    return ranked[:3]
