# Audit Dossier TN — IA, sources et parcours

Audit du 13 septembre 2026 sur le code présent, y compris les modifications locales. Recommandations proposées ; le code applicatif n’a pas été modifié pendant cet audit.

La priorité est de rendre les résultats vérifiables et de réunir les pièces, le formulaire et la revue dans un même dossier. La stack Next.js / FastAPI / Azure convient à cet objectif.

## Vérifications effectuées

- Lecture des routes, des deux parcours d’extraction, des règles, du catalogue F005, des sources et des composants d’interface.
- Consultation de l’accueil, du F005 et du portail agent dans le navigateur. L’étape initiale du F005 a aussi été examinée sur mobile : après stabilisation, largeur du contenu de 390 px pour un viewport de 390 px ; pas de débordement horizontal observé.
- TypeScript : `node node_modules/typescript/bin/tsc --noEmit` réussit.
- Tests existants, fournisseurs réels désactivés et stockage temporaire : **25 réussis, 1 échoué**. `test_assistant_explicit_demo` attend `mode=demo`, alors que le nouveau fallback retourne `assistant_domain_intelligence`.
- Vérifications isolées : `retrieve('qzxv987')` retourne trois sources malgré l’absence de correspondance ; la simulation DGI retourne `pass` pour `ABCDEFGH` et une société fictive.
- L’application locale indique Azure non configuré. La précision et la latence réelles d’Azure/OCR n’ont donc pas été mesurées. La génération complète d’un nouveau F005 et la totalité du parcours mobile n’ont pas été retestées dans cet audit.

## 1. Corriger les promesses et les preuves — priorité immédiate

### Réponses réglementaires et citations

[backend/ai.py](C:/Users/youssef/Documents/ChatGPT/Hiil/backend/ai.py:113) contient un fallback par mots-clés donnant des listes de pièces, délais et obligations. Il peut rattacher les deux premières sources à une réponse lorsque les références attendues n’ont pas été retrouvées. Avec Azure, les réponses s’appuient également sur les cinq notes écrites dans [backend/sources.py](C:/Users/youssef/Documents/ChatGPT/Hiil/backend/sources.py:5), sans passage original conservé.

Un identifiant de source valide ne prouve pas que cette source soutient l’affirmation. Le catalogue ajoute aussi des précisions comme « notifications sous 48h » et certificat « délivré dans les 6 mois », sans passage justificatif attaché. Les références du délai diffèrent entre les fichiers : article 44 dans `sources.py`, article 15 dans `form_catalog.py`. Leur validité doit être vérifiée sur les textes, pas déduite de ces notes.

**Changement recommandé :** conserver chaque règle avec sa procédure, ses conditions, un passage exact, l’URL, la page ou section, la version et la date de vérification. Retirer des réponses les affirmations non vérifiées. En l’absence de preuve suffisante, indiquer ce qui manque et proposer la source à consulter. Garder les aides statiques déjà vérifiées disponibles sans LLM, avec un mode explicite.

Le [répertoire officiel des formalités](https://home.registre-entreprises.tn/formalites/) distingue les démarches et leurs délais ; il ne faut pas généraliser une règle de transfert de siège à toutes les modifications. L’ouverture directe a renvoyé HTTP 503 pendant l’audit, tandis que la recherche donnait accès au contenu indexé : prévoir un corpus local versionné est utile pour la démo.

**Acceptation :** une question hors corpus ne reçoit aucune citation décorative ; chaque délai ou pièce obligatoire affiché peut être retrouvé dans le passage original et son contexte.

### Indicateurs et simulation administrative

[backend/analytics.py](C:/Users/youssef/Documents/ChatGPT/Hiil/backend/analytics.py:72) fixe 45 minutes et 8 minutes ; les 82 % affichés ne sont pas mesurés dans l’application. Le nombre de confirmations est présenté comme des rejets prévenus. Le risque de rejet additionne des poids manuels, puis l’interface l’affiche en pourcentage. La simulation DGI valide seulement un format très permissif et produit pourtant une concordance confirmée.

**Changement recommandé :** afficher « temps cible estimé », « écarts confirmés » et « points à résoudre ». Pour la DGI, afficher « contrôle de format effectué » et « concordance externe non vérifiée ». Conserver une simulation clairement identifiée pour le jury. Une comparaison réelle entre une pièce fiscale et un extrait RNE importés est démontrable sans API institutionnelle.

Le texte « traité localement » de l’import CIN doit dépendre du fournisseur réellement utilisé : les branches Azure transmettent le document au service configuré. Le voyant « connecté au RNE » de l’atelier ne correspond à aucune connexion institutionnelle dans ces routes.

## 2. Améliorations IA à forte valeur

### Un seul service d’extraction avec provenance

Dans [backend/form_ocr.py](C:/Users/youssef/Documents/ChatGPT/Hiil/backend/form_ocr.py:119), une CIN passe d’abord par `read_document`, puis par `extract_cin`, qui peut relancer l’OCR et un appel LLM, puis par l’extraction structurée générale. Cette duplication ajoute des appels et peut produire des lectures contradictoires.

Le chemin CIN crée aussi des preuves telles que `Titulaire : <nom>` et fixe la page à 1. Ces chaînes reconstruites ne passent pas par la vérification de citation exacte utilisée pour les candidats structurés. Le lecteur spécialisé peut translittérer les noms avec un dictionnaire et des heuristiques.

**Pipeline proposé :** contrôle de lisibilité → texte natif exploitable, sinon OCR des pages concernées → classement du document → extraction structurée → validations → suggestions à confirmer. Réutiliser le même résultat OCR pour tous les extracteurs. Conserver le nom arabe original ; toute translittération éventuelle doit être séparée et identifiée comme suggestion.

Chaque valeur devrait conserver `document_id`, page, texte original, valeur normalisée, zone du document, méthode et état de confirmation. [Azure Document Intelligence Read](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/read?view=doc-intel-4.0.0) fournit les polygones et la confiance au niveau des mots ; `document_ocr` ne conserve aujourd’hui que les lignes de texte. Cette confiance mesure la lecture, pas la conformité juridique.

Afficher les champs incertains avec le recadrage de leur source. Si l’extraction LLM échoue après une lecture réussie, conserver le texte et les suggestions vérifiables, puis permettre la saisie manuelle.

**Acceptation :** une seule lecture par fichier/version d’OCR ; aucune valeur sans provenance présentée comme extraite ; une panne LLM ne fait pas perdre le résultat OCR disponible.

### Assistance consciente du formulaire

Le nouveau conseiller conserve les messages dans React, mais [askAssistant](C:/Users/youssef/Documents/ChatGPT/Hiil/components/form-wizard.tsx:186) envoie uniquement `{question}`. Le serveur reçoit des informations générales du dossier, sans historique de cette conversation, sans champs du F005, sans modifications choisies et sans champ actif.

**Changement recommandé :** charger côté serveur le brouillon autorisé et un historique court ; fournir procédure, étape, champ actif et erreurs utiles. Exemples : « Où trouver ce numéro ? », « Pourquoi ce champ apparaît ? », « Et si le déclarant est une autre personne ? ». Répondre avec explication, prochaine action et passage source. Garder le remplissage dans la pipeline guidée ; une éventuelle proposition de changement doit être revue avant application.

Pour les règles stables, utiliser des validations Python. Réserver le LLM à l’extraction, aux ambiguïtés de langage et aux explications contextualisées. Une recherche multilingue peut ensuite compléter le lexique français/arabe ; les identifiants doivent conserver une recherche exacte.

### Mesurer l’utilité avant d’étendre les modèles

Créer un premier jeu de 20 à 30 documents synthétiques ou autorisés : arabe/français, scan flou, rotation, zéro initial, deux identités, informations contradictoires, document non pertinent. Ajouter des questions dont la bonne réponse est une abstention.

Mesurer exactitude par champ, erreurs sur identifiants, taux de corrections humaines, pertinence des passages, affirmations sans preuve, latence p50/p95 et coût par dossier. Ce premier jeu servira aux régressions ; il est trop petit pour prouver une précision générale ou entraîner une probabilité de rejet.

## 3. Collecte des sources : proposition adaptée au budget

`scratch_test_rne.py` inspecte un bundle JavaScript dont le nom contient un hash. C’est un script exploratoire ; le dépôt ne contient pas encore de chaîne de collecte, de versionnement et d’indexation des sources réglementaires.

| Besoin | Choix proposé | Usage |
|---|---|---|
| Télécharger des pages et PDF publics | [HTTPX](https://www.python-httpx.org/async/) | Client partagé, délais, concurrence limitée par domaine, gestion des erreurs |
| Extraire le contenu HTML | [Trafilatura](https://trafilatura.readthedocs.io/en/latest/) | Corps du texte, métadonnées et liens ; vérifier séparément la fidélité des tableaux |
| Lire les PDF | `pypdf` déjà présent, puis OCR si nécessaire | Conserver les pages et les fichiers originaux |
| Lire une page publique rendue en JavaScript | [Playwright Python](https://playwright.dev/python/docs/library) | Seulement pour les pages nécessitant un navigateur |
| Rechercher dans le petit corpus | [SQLite FTS5](https://sqlite.org/fts5.html) | Recherche lexicale avec BM25 et filtres de procédure ; lexique arabe/français |

Commencer par 10 à 20 références nécessaires à la démonstration : F005, formalités des scénarios retenus, fiches détaillées disponibles, textes expressément cités et références fiscales correspondant aux contrôles proposés. Étendre la couverture après vérification.

La collecte devrait être un traitement séparé de la requête utilisateur : liste d’URL autorisées → récupération → conservation du HTML/PDF et de son hash → extraction → découpage par article/procédure → validation → publication dans l’index.

Conserver `fetched_at`, `checked_at`, date de publication, date d’effet lorsqu’elle est connue, langue, URL et hash. Une nouvelle récupération ne signifie pas qu’une règle a été validée. Utiliser ETag/Last-Modified lorsqu’ils existent, reprise avec attente sur 429/503 et dernière version validée en cas d’échec. Respecter les conditions et restrictions d’accès des sites ; un endpoint trouvé dans le JavaScript ne constitue pas une API publique stable.

Le RNE publie des [formulaires d’abonnement aux web services KYC et UBO](https://home.registre-entreprises.tn/echange_des_donnees/). Sa [documentation KYC](https://home.registre-entreprises.tn/wp-content/uploads/2026/03/Annexe-2-Descriptif-KYC.pdf) décrit notamment des contrôles d’abonnement, d’IP et de solde. La démo doit donc fonctionner avec les références publiques et les pièces importées, sans dépendre d’un accès institutionnel supposé gratuit.

Pour un corpus plus large, évaluer des embeddings multilingues et une recherche hybride sur le jeu de questions. [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview) est une option ultérieure ; le petit corpus initial peut rester dans SQLite.

## 4. Réunir et simplifier le parcours

### Un dossier, une bibliothèque de pièces, un export

Les documents du dossier et les imports OCR du F005 sont stockés séparément. Le [ZIP global](C:/Users/youssef/Documents/ChatGPT/Hiil/backend/main.py:204) exporte uniquement les documents du dossier ; il n’ajoute ni le F005 généré ni les pièces importées dans l’atelier. Les contrôles du dossier restent centrés sur le changement d’adresse, alors que le formulaire propose 31 modifications.

**Changement recommandé :** réunir les pièces et leurs extractions dans un modèle commun. Réutiliser explicitement les informations déjà confirmées ; ne pas choisir silencieusement la première occurrence d’un identifiant. Associer à chaque scénario une checklist vérifiée. Distinguer couverture des cases du formulaire et prise en charge d’un dossier complet pour cette démarche.

Parcours cible : **choisir la démarche → ajouter les pièces → confirmer/corriger → compléter les éléments manquants → télécharger et préparer la revue**. Le F005 devient un résultat de ce dossier.

**Acceptation :** un document importé une fois est disponible dans le formulaire, la revue et l’export ; l’export comprend le F005 correspondant aux données confirmées et sa version.

### Réduire l’effort de lecture

- Accueil : placer « Reprendre ma démarche » et les éléments manquants en premier. Déplacer les indicateurs de démonstration et les annonces « bientôt » vers une zone secondaire.
- Étape initiale mobile : les six grandes cartes rendent la page longue. Afficher d’abord les démarches réellement couvertes et une entrée compacte pour les autres. Garder l’action suivante accessible après sélection.
- Champs : afficher une explication courte et un exemple ; ouvrir les détails et la source à la demande. Masquer RIB et réservation de nom tant que la modification correspondante n’est pas choisie.
- Aide : regrouper le bouton Aide, l’accordéon, le panneau latéral et le conseiller dans une interaction cohérente. Sous 1200 px, [le panneau latéral disparaît](C:/Users/youssef/Documents/ChatGPT/Hiil/app/form-studio.css:2474), ainsi que son accès à l’aperçu et à la source. Prévoir une entrée visible pour l’aperçu sur toutes les tailles.
- Vocabulaire : « Préparer ma déclaration » est plus direct qu’« Atelier interactif RNE F005 v1.1 ». Les détails de calque vectoriel n’aident pas à choisir une action.

### Corriger les frictions fonctionnelles

- [Saisie des identités](C:/Users/youssef/Documents/ChatGPT/Hiil/components/form-wizard.tsx:534) : les caractères non numériques sont supprimés alors que l’aide accepte aussi un passeport ou une carte de séjour. Ajouter le type de pièce et une validation adaptée. Ne pas tronquer visuellement toutes les identités à huit cases.
- [Import CIN](C:/Users/youssef/Documents/ChatGPT/Hiil/components/form-wizard.tsx:1449) : les boutons ciblent le représentant ; aucun choix de rôle ne permet d’importer la CIN du déclarant distinct. Demander « À qui appartient cette pièce ? » ou placer un import dans chaque bloc.
- [Sauvegarde](C:/Users/youssef/Documents/ChatGPT/Hiil/components/form-wizard.tsx:254) : quitter avant le délai de 600 ms annule la sauvegarde en attente. Enregistrer avant navigation et protéger les modifications non sauvegardées.
- [Version du PDF](C:/Users/youssef/Documents/ChatGPT/Hiil/backend/form_routes.py:132) : tout changement d’étape invalide le PDF. Séparer progression de navigation et révision des données.
- [Aperçu](C:/Users/youssef/Documents/ChatGPT/Hiil/components/form-wizard.tsx:1401) : le conteneur cliquable avec `role=button` n’a pas de gestion Enter/Espace. Ajouter une vraie commande clavier. Relier les erreurs aux inputs avec `aria-describedby`, nommer le champ de question du conseiller et conserver un libellé accessible au retour mobile.

## 5. Ordre de réalisation recommandé

1. Corriger citations non justifiées, modes IA/simulation, indicateurs et promesses d’interface.
2. Réunir documents, valeurs confirmées, F005 et export ; stabiliser la sauvegarde.
3. Mutualiser l’OCR, conserver les preuves et corriger le choix représentant/déclarant.
4. Constituer le petit corpus vérifié et mettre en place la collecte hors requête utilisateur.
5. Contextualiser l’aide, réduire la densité mobile et ajouter les tests du nouveau parcours.

Optimisations suivantes : cache OCR par hash et version, aperçu PDF par révision des données, coût et latence par étape, nettoyage des anciens imports, retrait des routes et schémas du chatbot de génération devenu inutilisé. Avant exposition publique avec de vrais documents, ajouter authentification, droits entreprise/agent et contrôle d’accès sur les fichiers : les routes actuelles utilisent surtout l’existence du `case_id`.

La démonstration la plus convaincante : deux pièces avec une information contradictoire → source de chaque valeur visible → correction explicite → F005 et dossier complet exportés → revue administrative clairement simulée. Le jury peut constater chaque étape et son apport sans supposer une connexion à la DGI.
