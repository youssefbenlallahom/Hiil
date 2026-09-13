"""Declarative mapping of the supplied form. Guidance explains fields, not legal eligibility."""
import json
from pathlib import Path

FORM_URL = 'https://www.registre-entreprises.tn/rne-public/assets/pdfs/formulaires/RNE-F-005_declaration_modification_personne_morale.pdf'
PROCEDURES_URL = 'https://home.registre-entreprises.tn/formalites/'
SOURCES = {
    'form': {'title': 'Formulaire RNE F005 fourni', 'url': FORM_URL, 'detail': 'Les libellés et emplacements proviennent du PDF fourni. Les conseils de saisie ne constituent pas une validation juridique.'},
    'procedures': {'title': 'Répertoire officiel des formalités', 'url': PROCEDURES_URL, 'detail': 'Consultez la procédure correspondant à votre situation.'},
}
DEFINITION = json.loads((Path(__file__).parent / 'assets' / 'f005-fields.json').read_text(encoding='utf-8-sig'))
FIELDS = DEFINITION['fields']

# Checkbox centers measured from the actual PDF. Columns run right to left.
# Guidance is a plain-language explanation of the label, not an exhaustive legal checklist.
_ROWS = [
    [('denomination', 'Nom de l’entreprise', 'تغيير التسمية الاجتماعية أو الاسم التجاري أو الشارة', 'Changer la dénomination sociale, le nom commercial ou l’enseigne.', 'Identité', 571.71, 362.95),
     ('activite', 'Activité', 'تغيير أو إضافة أو حذف نشاط', 'Déclarer une activité ajoutée, modifiée ou supprimée.', 'Identité', 374.75, 366.87),
     ('suspension', 'Suspension ou reprise du registre', 'تعليق السجل أو إيقاف التعليق', 'Déclarer une suspension ou sa levée selon la situation de l’entreprise.', 'Vie de l’entreprise', 238.37, 366.87),
     ('restrictions', 'Saisies ou restrictions conservatoires', 'إدراج عقل / قيود احتياطية', 'Inscrire une saisie ou une restriction conservatoire fondée sur l’acte applicable.', 'Vie de l’entreprise', 105.83, 366.87)],
    [('beneficiaire', 'Bénéficiaire effectif', 'إيداع المستفيد الحقيقي', 'Déposer les informations relatives au bénéficiaire effectif. Cette case ne remplace pas sa déclaration dédiée.', 'Documents', 571.75, 329.13),
     ('ouverture', 'Ouverture d’une succursale', 'فتح فرع', 'Déclarer la création d’un établissement secondaire.', 'Adresse', 374.75, 329.04),
     ('fermeture', 'Fermeture d’une succursale', 'غلق فرع', 'Déclarer la fermeture d’un établissement secondaire.', 'Adresse', 238.37, 329.04),
     ('succursale', 'Adresse d’une succursale', 'تغيير عنوان الفرع', 'Une agence, un bureau ou un autre établissement secondaire change d’adresse.', 'Adresse', 105.87, 329.04)],
    [('siege', 'Adresse du siège social', 'تغيير عنوان المقر الاجتماعي', 'L’adresse principale officielle de la société change. La nouvelle adresse figure dans les pièces de la démarche, pas dans une zone dédiée de ce F005.', 'Adresse', 571.75, 296.46),
     ('commissaire', 'Commissaire aux comptes', 'تعيين أو تجديد مراقب حسابات', 'Déclarer la nomination ou le renouvellement du commissaire aux comptes.', 'Personnes', 374.75, 294.13),
     ('financiers', 'États financiers', 'إيداع القوائم المالية', 'Déposer les états financiers de l’entreprise.', 'Documents', 238.37, 294.13),
     ('apports', 'Rapport du commissaire aux apports', 'إيداع تقرير مراقب الحصص العينية', 'Déposer le rapport relatif aux apports en nature lorsque cette procédure s’applique.', 'Documents', 105.87, 294.13)],
    [('gestion', 'Rapport de gestion et d’activité', 'إيداع تقرير التصرف والنشاط', 'Déposer le rapport de gestion et d’activité établi pour l’entreprise.', 'Documents', 571.75, 259.34),
     ('autres_actes', 'Autres actes ou documents', 'إيداع عقود أو وثائق أخرى', 'Déposer un acte ou un document relevant du registre qui n’a pas de case dédiée dans ce formulaire.', 'Documents', 374.75, 257.01),
     ('statuts', 'Statuts', 'تحيين القانون الأساسي', 'Déposer ou signaler une mise à jour des statuts de la société.', 'Identité', 238.37, 257.01),
     ('dirigeants', 'Dirigeants', 'إضافة أو تحيين المسيرين', 'Ajouter un dirigeant ou actualiser les informations relatives aux dirigeants.', 'Personnes', 105.87, 257.01)],
    [('associes', 'Associés ou actionnaires', 'تحيين الشركاء أو المساهمين', 'Mettre à jour les informations sur les associés ou les actionnaires.', 'Personnes', 571.75, 217.53),
     ('cession', 'Cession de parts ou d’actions', 'إحالة الحصص أو إحالة الأسهم', 'Déclarer une cession de parts sociales ou d’actions.', 'Capital', 374.75, 215.20),
     ('forme', 'Forme juridique', 'تغيير الشكل القانوني', 'Déclarer la transformation de la forme juridique de la société.', 'Identité', 238.37, 215.20),
     ('duree', 'Durée de la société', 'التمديد في مدة الشركة', 'Déclarer une prorogation de la durée de la société.', 'Vie de l’entreprise', 105.87, 215.20)],
    [('projet_fusion', 'Projet de fusion ou de scission', 'إيداع مشروع الاندماج والانقسام', 'Déposer le projet avant l’opération. À distinguer de la fusion ou de la scission réalisée.', 'Capital', 571.75, 178.03),
     ('scission', 'Scission', 'الانقسام', 'Déclarer l’opération de scission de la société.', 'Capital', 374.75, 175.70),
     ('capital', 'Projet d’augmentation de capital', 'إيداع مشروع الترفيع في رأس المال', 'Déposer le projet d’augmentation de capital correspondant au libellé de cette case.', 'Capital', 238.37, 175.70),
     ('fusion', 'Fusion', 'الاندماج', 'Déclarer une opération de fusion. Ne pas la confondre avec le dépôt du projet.', 'Capital', 105.87, 175.70)],
    [('banque', 'Compte bancaire', 'تغيير الحساب البنكي', 'Déclarer le changement du compte bancaire de l’entreprise et renseigner le RIB correspondant.', 'Coordonnées', 571.75, 141.53),
     ('cloture_exercice', 'Clôture de l’exercice', 'تغيير تاريخ قفل الموازنة', 'Modifier la date de clôture de l’exercice comptable.', 'Vie de l’entreprise', 374.75, 139.20),
     ('dissolution', 'Dissolution et liquidation', 'الحل والتصفية', 'Déclarer la dissolution et l’entrée en liquidation de la société.', 'Liquidation', 238.37, 139.20),
     ('radiation', 'Radiation', 'التشطيب', 'Demander la radiation du registre selon la procédure applicable. À distinguer d’une suspension.', 'Liquidation', 105.87, 139.20)],
    [('liquidateur', 'Liquidateur', 'تعيين / تجديد مهام / تغيير المصفي', 'Déclarer la nomination, le renouvellement du mandat ou le changement du liquidateur.', 'Liquidation', 571.75, 106.52),
     ('comptes_liquidation', 'Comptes de liquidation', 'إيداع ختم القوائم المالية للتصفية', 'Déposer les états financiers de clôture de liquidation.', 'Liquidation', 374.75, 104.20),
     ('fin_liquidation', 'Clôture de la liquidation', 'ختم أعمال التصفية', 'Déclarer la fin des opérations de liquidation.', 'Liquidation', 238.37, 104.20)],
]
MODIFICATIONS = [dict(key=k, label=label, arabic=ar, help=help_text, group=group, x=x, y=y, source='form')
                 for row in _ROWS for k, label, ar, help_text, group, x, y in row]
FIELD_MAP = {f['key']: f for f in FIELDS}
MOD_MAP = {m['key']: m for m in MODIFICATIONS}
GUIDANCE = {
    'language': 'La notice du F005 prévoit une saisie en arabe ; le français peut être ajouté. Reprenez l’orthographe des pièces, sans traduction automatique des noms.',
    'modifications': 'Vous pouvez cocher plusieurs modifications sur la même déclaration. La notice indique une redevance distincte pour chaque modification ; ce parcours ne calcule pas ces frais.',
    'signature': 'Après relecture, le déclarant ou son mandataire signe à l’emplacement prévu en page 2. Le PDF produit ici reste non signé : le bouton de préparation ne constitue pas une signature électronique.',
    'documents': 'Le formulaire seul ne constitue pas le dossier complet. Consultez la formalité RNE correspondant aux modifications choisies pour les pièces et conditions de dépôt.',
}


def catalog():
    return dict(version=DEFINITION['version'], fields=FIELDS,
                modifications=MODIFICATIONS, guidance=GUIDANCE, sources=SOURCES)
