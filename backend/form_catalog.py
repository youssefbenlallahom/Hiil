"""Field guidance for the supplied RNE F005 v1.1, checked 2026-09-12.

Explanations paraphrase the supplied form and official RNE references. They do
not claim that selecting a checkbox satisfies the associated filing procedure.
"""
FORM_URL = 'https://www.registre-entreprises.tn/rne-public/assets/pdfs/formulaires/RNE-F-005_declaration_modification_personne_morale.pdf'
PROCEDURES_URL = 'https://home.registre-entreprises.tn/formalites/'
SOURCES = {
    'form': {'title': 'Formulaire RNE F005, version 1.1', 'url': FORM_URL, 'detail': 'Pages 1 et 2 du PDF fourni, contrôlées visuellement.'},
    'services': {'title': 'RNE · services et certificats', 'url': 'https://home.registre-entreprises.tn/a-propos/', 'detail': 'Certificat de réservation de dénomination, nom commercial ou enseigne.'},
    'identity': {'title': 'RNE · identification de l’entreprise', 'url': 'https://home.registre-entreprises.tn/le-registre-national-des-entreprises-vers-le-full-digital/', 'detail': 'Identifiant unique / matricule fiscal et qualité de représentant légal.'},
    'procedures': {'title': 'RNE · répertoire des formalités', 'url': PROCEDURES_URL, 'detail': 'Intitulés des procédures de modification. Consulter la fiche applicable pour les pièces et conditions.'},
}


def field(key, label, arabic, step, required, maximum, help_text, where, example, tip, source='form', input_type='text', why='', how='', pitfalls='', law_ref='', badge=''):
    return dict(
        key=key, label=label, arabic=arabic, step=step, required=required, max_length=maximum,
        help=help_text, where=where, example=example, tip=tip, source=source, input_type=input_type,
        why=why, how=how, pitfalls=pitfalls, law_ref=law_ref, badge=badge,
    )


FIELDS = [
    field(
        'identifiant_unique',
        'Identifiant unique de l’entreprise',
        'المعرّف الوحيد',
        1, True, 8,
        'Numéro légal d’immatriculation attribué à la société au Registre National des Entreprises, correspondant au matricule fiscal.',
        'En haut de votre Extrait RNE récent (sous le code-barres) ou sur votre Déclaration d’existence fiscale (patente).',
        '1234567A',
        'Conservez les 7 chiffres et la lettre finale sans espace ni tiret. Ce champ identifie la société, pas le dirigeant.',
        source='identity',
        why='Indispensable pour que les services du RNE rattachent la déclaration au dossier juridique existant de votre société.',
        how='Renseignez les 7 chiffres suivis de la lettre de contrôle (ex: 1234567A). Sur le formulaire papier, chaque caractère occupe une case dédiée.',
        pitfalls='Ne confondez pas l’identifiant de la société avec le numéro de CIN du gérant ou avec le numéro de registre de commerce antérieur (RC).',
        law_ref='Loi n° 2018-52 du 29 octobre 2018, art. 8 & Décret gouvernemental n° 2019-357',
        badge='8 caractères (7 chiffres + 1 lettre)'
    ),
    field(
        'certificat_reservation',
        'N° du certificat de réservation',
        'رقم شهادة الحجز عند الاقتضاء',
        1, False, 14,
        'Référence officielle attestant de la réservation d’un nom commercial, d’une enseigne ou d’une dénomination sociale.',
        'Sur l’attestation de réservation remise par le RNE ou générée sur le portail en ligne du RNE.',
        'RES-2026-04891',
        'La mention « le cas échéant » indique que ce champ ne s’applique que si vous changez de nom ou réservez une enseigne. Laissez vide pour un simple changement d’adresse.',
        source='services',
        why='Prouve que la nouvelle dénomination sociale ou enseigne commerciale a été préalablement protégée et validée par le RNE.',
        how='Inscrivez la référence complète telle qu’elle apparaît sur votre certificat de réservation délivré dans les 6 mois.',
        pitfalls='Ne remplissez pas ce champ si votre formalité concerne uniquement le siège social, une succursale ou les dirigeants sans changement de nom.',
        law_ref='Loi n° 2018-52, art. 14 (Réservation préalable de dénomination)',
        badge='Optionnel (si changement de nom)'
    ),
    field(
        'rib',
        'RIB en cas de modification',
        'المعرّف البنكي في حالة تغييره',
        1, False, 20,
        'Relevé d’identité bancaire officiel du compte bancaire de la société en Tunisie (20 chiffres).',
        'Sur une attestation de RIB délivrée par votre agence bancaire ou sur le carnet de chèques de l’entreprise.',
        '08012012345678901234',
        'Exactement 20 chiffres sans espaces ni lettres. À renseigner uniquement si vous déclarez un nouveau compte bancaire professionnel.',
        source='form',
        why='Permet au RNE de tenir à jour les coordonnées bancaires officielles de la personne morale pour les tiers autorisés.',
        how='Structure à 20 chiffres : Code banque (2) + Code agence/guichet (3) + N° de compte (13) + Clé RIB (2).',
        pitfalls='Ne saisissez jamais un numéro de carte bancaire (16 chiffres) ni le RIB personnel d’un associé. Le compte doit être au nom de l’entreprise.',
        law_ref='Décret gouvernemental n° 2019-357, art. 12',
        badge='20 chiffres (si changement de banque)'
    ),
    field(
        'representant_legal',
        'Nom du représentant légal',
        'الممثل القانوني',
        2, True, 80,
        'La personne physique investie des pouvoirs d’administration et d’engagement de la société (Gérant, PDG ou Directeur Général).',
        'Sur les statuts constitutifs, le PV d’assemblée générale de nomination ou l’extrait RNE à jour.',
        'سامي بن علي (ou Sami Ben Ali)',
        'L’usage officiel du RNE privilégie l’écriture en langue arabe conforme à la CIN. Évitez les formules vagues comme « Le gérant ».',
        source='identity',
        why='Identifie la personne légalement responsable des engagements de la société et habilitée à signer les actes engageant la société.',
        how='Prénom et nom de famille complets. Si vous utilisez l’arabe, respectez l’orthographe exacte de la carte d’identité.',
        pitfalls='Ne mettez pas le nom de la société ici, ni seulement le prénom. Si la société a plusieurs cogérants, mentionnez le gérant statutaire principal.',
        law_ref='Code des Sociétés Commerciales, art. 112 (SARL) et art. 208 (SA)',
        badge='Gérant, PDG ou Directeur Général'
    ),
    field(
        'identite_representant',
        'N° d’identité du représentant',
        'رقم الهوية',
        2, True, 11,
        'Numéro de la carte d’identité nationale (CIN) pour les Tunisiens, ou carte de séjour / passeport pour les étrangers.',
        'Sur la carte d’identité nationale (CIN) du représentant légal (8 chiffres sous « بطاقة التعريف الوطنية »).',
        '01234567',
        'Conservez impérativement le zéro initial si le numéro de CIN commence par 0. Les 8 chiffres s’insèrent dans les cases cyan du formulaire.',
        source='form',
        why='Garantit l’identification formelle et univoque du dirigeant dans les registres administratifs nationaux.',
        how='Saisissez les 8 chiffres sans espace ni tiret. Pour les résidents étrangers, indiquez le numéro de carte de séjour.',
        pitfalls='Attention aux cartes commençant par 0 : ne supprimez pas le zéro de tête. Ne confondez pas avec la date de délivrance.',
        law_ref='Loi n° 2018-52, art. 11 & Loi n° 93-27 relative à la carte d’identité nationale',
        badge='8 chiffres (CIN tunisienne)'
    ),
    field(
        'nom_declarant',
        'Nom du déclarant',
        'اسم ولقب المصرح',
        2, True, 80,
        'La personne qui accomplit et signe cette déclaration au guichet : le dirigeant lui-même ou un mandataire autorisé.',
        'Pièce d’identité de la personne qui effectue la démarche, accompagnée d’une procuration si distinct du gérant.',
        'آمنة بن عمر (ou Amna Ben Amor)',
        'Si le gérant déclare lui-même, cochez l’option « Cette personne fait aussi la déclaration » pour reporter automatiquement son identité.',
        source='form',
        why='Détermine l’identité du signataire physique qui engage sa responsabilité sur l’exactitude des déclarations souscrites.',
        how='Prénom et nom complets. Si vous agissez sous mandat (avocat, comptable, formaliste), inscrivez vos coordonnées personnelles.',
        pitfalls='Si le déclarant n’est pas le représentant légal, une procuration légalisée originale doit impérativement accompagner le dossier papier.',
        law_ref='Loi n° 2018-52, art. 23 (Dépôt et procuration)',
        badge='Dirigeant ou Mandataire habilité'
    ),
    field(
        'identite_declarant',
        'N° d’identité du déclarant',
        'رقم بطاقة هوية المصرح',
        2, True, 20,
        'Numéro de la pièce d’identité (CIN, carte de séjour ou passeport) de la personne qui dépose la déclaration.',
        'Sur la carte CIN du déclarant ou sa pièce d’identité officielle en cours de validité.',
        '01234567',
        'Doit correspondre exactement à la personne désignée dans le champ « Nom du déclarant ».',
        source='form',
        why='Permet la vérification de conformité de la signature portée en page 2 lors du dépôt au centre d’affaires du RNE.',
        how='8 chiffres pour une CIN tunisienne, avec zéro initial préservé.',
        pitfalls='Le numéro de pièce doit être celui de la personne physique qui signe en page 2, pas celui de la société.',
        law_ref='Loi n° 93-27 & Notice officielle RNE F005',
        badge='8 chiffres (CIN du signataire)'
    ),
    field(
        'email',
        'Adresse e-mail de contact',
        'البريد الإلكتروني',
        3, True, 70,
        'Adresse électronique officielle pour le suivi du dossier et la réception des notifications du RNE.',
        'Boîte de messagerie professionnelle de l’entreprise ou de la personne chargée du suivi juridique de la formalité.',
        'contact@entreprise.tn',
        'Assurez-vous de pouvoir consulter cette boîte : les notifications de rejet ou de validation y sont transmises sous 48h.',
        source='form',
        input_type='email',
        why='Rendue obligatoire par la notice du RNE pour accélérer le traitement dématérialisé et les notifications de recevabilité.',
        how='Format email standard sans espace : contact@domaine.tn. Les minuscules sont recommandées.',
        pitfalls='Évitez les adresses temporaires ou mal orthographiées. Un refus de dépôt pour pièce manquante vous sera notifié par ce canal.',
        law_ref='Notice officielle RNE F 005 v1.1, page 1',
        badge='Format: contact@societe.tn'
    ),
    field(
        'gsm',
        'Téléphone mobile de contact',
        'الهاتف الجوال',
        3, True, 25,
        'Numéro de téléphone mobile joignable en Tunisie pour les échanges rapides et alertes SMS du RNE.',
        'Ligne mobile de la personne suivant directement la formalité auprès du RNE.',
        '+216 58 873 878',
        'Numéro à 8 chiffres pour un opérateur tunisien (Orange, Ooredoo, Tunisie Telecom), avec ou sans indicatif +216.',
        source='form',
        input_type='tel',
        why='Permet au guichetier du RNE de joindre directement le déclarant en cas de doute sur une pièce avant rejet formel.',
        how='Saisissez les 8 chiffres du numéro mobile (ex: 58873878). L’indicatif +216 est accepté et normalisé.',
        pitfalls='Ne mettez pas un numéro de téléphone fixe : le service envoie souvent des notifications SMS automatiques.',
        law_ref='Notice officielle RNE F 005 v1.1, page 1',
        badge='Numéro mobile tunisien'
    ),
    field(
        'date',
        'Date de la déclaration',
        'التاريخ',
        3, True, 10,
        'Date à laquelle la déclaration modificative F005 est signée et formalisée avant son dépôt.',
        'La date du jour où vous finalisez et imprimez le document pour signature.',
        '12/09/2026 (ou 2026-09-12)',
        'Sur la page 2 du formulaire papier, le format est imprimé de droite à gauche : Jour / Mois / Année.',
        source='form',
        input_type='date',
        why='Fait courir les délais légaux de déclaration modificative (délai d’un mois à compter de l’acte modificatif).',
        how='Sélectionnez la date du jour ou la date d’établissement de la déclaration.',
        pitfalls='Attention au délai légal : en droit tunisien, les modifications doivent être déclarées au RNE dans le mois suivant l’acte.',
        law_ref='Loi n° 2018-52, art. 15 (Délai légal de déclaration modificative : 1 mois)',
        badge='Format JJ/MM/AAAA'
    ),
]

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
    return dict(version='RNE F005 · v1.1', checked_at='2026-09-12', fields=FIELDS,
                modifications=MODIFICATIONS, guidance=GUIDANCE, sources=SOURCES)
