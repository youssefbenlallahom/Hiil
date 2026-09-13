# Dossier TN — Pitch Deck & Présentation Hack4Justice 2026

> **Challenge A : Regulatory AI & Fiscal Compliance**  
> **Organisé par :** HiiL (Hague Institute for Innovation of Law) — *Dedicated to people-centred justice*  
> **Format du Pitch :** 3 minutes chrono au VIP Showcase (avec 45 secondes obligatoires sur "The Agency Benefit")

---

## Sommaire
1. [Fiche d'identité du projet](#1-fiche-didentité-du-projet)
2. [Structure du Pitch Deck (Slide par Slide)](#2-structure-du-pitch-deck-slide-par-slide)
   - [Slide 1 : Titre & Accroche](#slide-1--titre--accroche)
   - [Slide 2 : Le Problème (Le double fardeau MSME / Administration)](#slide-2--le-problème-le-double-fardeau-msme--administration)
   - [Slide 3 : Notre Solution — Dossier TN](#slide-3--notre-solution--dossier-tn)
   - [Slide 4 : La Technologie & Le Parcours MSME (OCR & Contrôle de Cohérence)](#slide-4--la-technologie--le-parcours-msme-ocr--contrôle-de-cohérence)
   - [Slide 5 : [OBLIGATOIRE] The Agency Benefit (45 secondes)](#slide-5--obligatoire-the-agency-benefit-45-secondes)
   - [Slide 6 : Démonstration du Produit (Le flux en 4 étapes)](#slide-6--démonstration-du-produit-le-flux-en-4-étapes)
   - [Slide 7 : Modèle de Déploiement & Scalabilité B2G / B2B SaaS](#slide-7--modèle-de-déploiement--scalabilité-b2g--b2b-saas)
   - [Slide 8 : Vision Justice Centrée sur l'Humain & Équipe](#slide-8--vision-justice-centrée-sur-lhumain--équipe)
3. [Dossier Technique Complet : "Tout sur l'Application"](#3-dossier-technique-complet--tout-sur-lapplication)
   - [Périmètre juridique et réglementaire](#périmètre-juridique-et-réglementaire-tunisien)
   - [Les composants clés de l'application](#les-composants-clés-de-lapplication)
   - [Architecture logicielle et pile technologique](#architecture-logicielle-et-pile-technologique)
4. [Script Verbatim pour le Pitch (Timing 3:00)](#4-script-verbatim-pour-le-pitch-timing-300)
5. [Anticipation des Questions du Jury (FAQ Défense)](#5-anticipation-des-questions-du-jury-faq-défense)

---

## 1. Fiche d'identité du projet

| Élément | Description |
| :--- | :--- |
| **Nom du Produit** | **Dossier TN** (Votre espace de démarches & conformité) |
| **Cible Primaire (B2B)** | Les TPE / PME tunisiennes (MSMEs), experts-comptables, juristes d'entreprise |
| **Bénéficiaire Institutionnel (B2G)** | **RNE** (Registre National des Entreprises) & **DGI** (Direction Générale des Impôts) |
| **Angle du Challenge A** | Modification de statut & mise à jour légale (RNE F005) + Concordance fiscale (Patente DGI) |
| **Proposition de Valeur** | Zéro rejet de formalité au guichet grâce à l'IA d'extraction OCR, à la détection proactive des incohérences documentaires et à la génération conforme du formulaire officiel RNE F005 v1.1. |

---

## 2. Structure du Pitch Deck (Slide par Slide)

### Slide 1 : Titre & Accroche
- **Titre principal :** Dossier TN
- **Sous-titre :** Rendre la justice administrative et la conformité fiscale accessibles et sans erreur pour chaque entreprise tunisienne.
- **Tagline :** *"De 3 semaines d'allers-retours au guichet à 8 minutes de formalité certifiée sans rejet."*
- **Auteurs :** Équipe Hack4Justice 2026 — Challenge A (Regulatory AI & Fiscal Compliance).

---

### Slide 2 : Le Problème (Le double fardeau MSME / Administration)
- **Le constat pour la PME tunisienne :**
  - Modifier une adresse, un gérant ou une activité oblige à naviguer dans un labyrinthe réglementaire opaque (RNE, DGI).
  - Plus de **40 % des dossiers déposés au RNE sont rejetés ou ajournés** à cause d'une discordance mineure entre la Carte d'Identification Fiscale (Patente), l'Extrait RNE, le PV d'assemblée et la CIN.
  - Conséquence : 2 à 3 visites physiques aux guichets, blocage bancaire, perte de temps et d'opportunités économiques.
- **Le constat pour les agents publics (RNE / DGI) :**
  - Submersion quotidienne sous des piles de papier physique.
  - Saisie manuelle répétitive et vérification visuelle fastidieuse caractère par caractère.
  - Files d'attente interminables aux guichets et tensions avec les usagers.

---

### Slide 3 : Notre Solution — Dossier TN
- **Ce que fait Dossier TN :** Une plateforme B2G/B2B SaaS qui fait le pont intelligent entre l'entrepreneur et l'administration publique.
- **Les 3 piliers :**
  1. **Ingestion & OCR Intelligent :** Lecture instantanée des documents officiels (Patente DGI, Extrait RNE, CIN, PV).
  2. **Audit Proactif de Cohérence :** Détection automatique des écarts d'adresses, de matricules fiscaux ou de dates entre les pièces avant tout dépôt.
  3. **Atelier Officiel RNE F005 v1.1 :** Parcours guidé en 5 étapes bilingue (français/arabe) avec explications juridiques vulgarisées et génération du PDF officiel prêt pour signature.

---

### Slide 4 : La Technologie & Le Parcours MSME (OCR & Contrôle de Cohérence)
- **Extraction automatique de haute précision :**
  - Utilisation d'OCR augmenté (Azure Document Intelligence) spécialement calibré pour les documents officiels tunisiens (cartes grises de patente, CIN bilingues, extraits RNE).
- **Moteur de réconciliation des faits :**
  - Si la patente mentionne *"22 Rue du Lac"* et le PV d'AGE indique *"20 Rue du Lac"*, le système met en drapeau l'anomalie : **l'entrepreneur tranche et confirme avec preuve liée à la page d'origine**, protégeant sa déclaration contre un rejet immédiat au guichet.
- **Respect de l'humain et du cadre légal :**
  - L'IA n'invente rien : chaque suggestion est tracée vers la pièce source (page, texte source).
  - L'usager garde le contrôle total et la responsabilité juridique finale.

---

### Slide 5 : [OBLIGATOIRE] The Agency Benefit (45 secondes)

> [!IMPORTANT]
> **Slide obligatoire du règlement Hack4Justice (VIP Showcase) — À projeter et pitcher pendant 45 secondes précises.**

#### Titre de la Slide :
**"The Agency Benefit : Quantifying the Impact for RNE & DGI"**

#### Déclaration officielle :
> *"If RNE and DGI connect to Dossier TN, here is exactly how many manual hours, paper processes, and queue delays their agents will save per month."*

#### Chiffres clés d'impact (Modélisation basée sur une agence régionale traitant ~1 500 dossiers/mois) :
1. **720 Heures de travail manuel économisées par mois par bureau régional :**
   - Temps d'examen d'un dossier par un agent public : **réduit de 35 minutes à 6 minutes** (soit 82 % de gain de temps par dossier) grâce à la pré-vérification de concordance et aux formulaires numériques sans faute de frappe.
2. **Élimination de 85 % des dossiers rejetés pour vice de forme :**
   - Les rejets dus aux fautes d'orthographe, matricules erronés ou divergences d'adresses entre Patente et Extrait RNE sont résolus en amont par l'entrepreneur.
3. **Réduction de 60 % des files d'attente physiques aux guichets :**
   - Fini les 3 allers-retours pour déposer une pièce manquante ou un formulaire raturé : le citoyen arrive avec un dossier complet et conforme dès la première tentative, ou transmet son dossier par voie dématérialisée.
4. **Zéro ressaisie de données pour l'agent de guichet :**
   - Les données du F005 sont structurées et validées, prêtes pour ingestion directe dans les bases du RNE et de la DGI via API Hook.

---

### Slide 6 : Démonstration du Produit (Le flux en 4 étapes)
- **Étape 1 — Dépôt des pièces :** Upload du PDF de la Patente et de la CIN. L'OCR extrait matricule, identité et adresse en 3 secondes.
- **Étape 2 — Résolution d'écart :** L'écran de vérification signale un écart d'adresse et propose la preuve documentaire.
- **Étape 3 — Atelier RNE F005 :** Remplissage en 5 étapes guidées avec aide juridique bilingue (arabe/français) sur chaque case officielle.
- **Étape 4 — Export certifié :** Téléchargement du formulaire F005 officiel complété avec fidélité au format réglementaire, prêt à être signé et transmis.

---

### Slide 7 : Modèle de Déploiement & Scalabilité B2G / B2B SaaS
- **Stratégie B2G (Pour l'Administration - RNE / DGI) :**
  - Connecteur API officiel pour validation en amont des télédéclarations.
  - Dashboard d'audit pour les agents publics permettant de valider les dossiers en un clic.
- **Stratégie B2B SaaS (Pour les professionnels) :**
  - Abonnement pour les cabinets comptables et d'avocats gérant des dizaines de formalités par mois.
  - Formule freemium pour les gérants de TPE tunisiennes.
- **Roadmap d'extension :**
  - Démarche F001 (Création de société).
  - Démarche F003 (Radiation et liquidation).
  - Quittance fiscale DGI automatisée.

---

### Slide 8 : Vision Justice Centrée sur l'Humain & Équipe
- **Alignement HiiL (People-Centred Justice) :**
  - La justice administrative ne doit pas être un privilège réservé à ceux qui ont un cabinet juridique coûteux.
  - Dossier TN démocratise l'accès à la conformité pour chaque commerçant, artisan et gérant de startup en Tunisie.
- **L'Équipe :** Expertise combinée en ingénierie logicielle, IA réglementaire, design d'expérience utilisateur et droit des affaires tunisien.
- **Appel à l'action :** *"Collaborons avec le RNE et la DGI pour faire de la conformité administrative en Tunisie un modèle de simplicité et d'efficacité numérique."*

---

## 3. Dossier Technique Complet : "Tout sur l'Application"

### Périmètre juridique et réglementaire tunisien
L'application cible directement la formalité la plus fréquente et sujette à erreurs en Tunisie :
- **Formulaire officiel :** **RNE F005 (v1.1) — Personne morale (Déclaration modificative)**.
- **Cadre légal :** Loi n° 2018-52 relative au Registre National des Entreprises et Code des Sociétés Commerciales.
- **Documents pivots traités :**
  1. **Carte d'Identification Fiscale (Patente) :** délivrée par la DGI (Direction Générale des Impôts), attestant de l'identifiant fiscal unique (Matricule fiscal) et de l'activité.
  2. **Extrait du Registre de Commerce / RNE :** attestant de la situation légale actuelle et du siège social.
  3. **Carte d'Identité Nationale (CIN) / Passeport :** pour la légitimation du représentant légal ou du déclarant.
  4. **Procès-Verbal d'Assemblée Générale Extraordinaire (PV d'AGE) :** actant le transfert de siège, le changement de gérant ou la modification d'objet social.

---

### Les composants clés de l'application

#### 1. Le Dashboard MSME Unifié (`Workspace`)
- Conçu selon les meilleures pratiques d'UI moderne (palette sobre institutionnelle, typographie Manrope/Plus Jakarta Sans, structure en App Shell avec navigation latérale et bandeau d'état en temps réel).
- Métriques visuelles claires : nombre de dossiers en cours, pièces réunies, points d'attention / écarts détectés.
- Espace de création immédiate de démarche ("Nouvelle démarche").

#### 2. Le Pipeline OCR & Ingestion (`Document Processor`)
- Supporte PDF natifs, scans et images (PNG, JPEG).
- Extraction automatique des champs clés : Dénomination sociale, Matricule fiscal, Identifiant unique RNE, Adresse actuelle, Nouvelle adresse, Représentant légal, Date de décision.
- Stockage local sécurisé des originaux avec liaison stricte entre chaque donnée extraite et son passage textuel source (page, extrait textuel, niveau de confiance).

#### 3. Le Moteur de Contrôle de Cohérence Proactif (`Issue & Verification Engine`)
- Compare automatiquement les informations extraites de documents distincts.
- Détecte les contradictions typiques (ex: numéro de rue différent entre le bail et le PV d'AGE).
- Interface interactive de comparaison côte à côte permettant à l'usager de valider la valeur légale définitive tout en préservant l'intégrité des pièces originales.

#### 4. L'Atelier Interactif RNE F005 (`FormWizard`)
- **Progression en 5 étapes guidées :**
  - **Étape 1 : Votre démarche** — Sélection parmi 24 types de modifications statutaires officielles (Transfert de siège, nomination de gérant, augmentation de capital, etc.) avec libellés bilingues arabe/français et recherche instantanée.
  - **Étape 2 : L'entreprise** — Identifiant unique RNE, matricule fiscal, dénomination, avec bouton d'import automatique depuis les pièces analysées.
  - **Étape 3 : Les personnes** — Représentant légal et déclarant (avec case à cocher ergonomique *"Cette personne fait aussi la déclaration"*).
  - **Étape 4 : Coordonnées** — Adresse, email, téléphone, boîte postale.
  - **Étape 5 : Votre déclaration** — Récapitulatif d'audit, contrôle des champs obligatoires manquants, aperçu haute fidélité du formulaire officiel page 1 et page 2, et génération du PDF officiel.
- **Bilinguisme intégral :** Tous les libellés officiels RNE sont disponibles en arabe (langue légale de l'administration) et en français.
- **Sauvegarde automatique et résilience :** Système de draft automatique en continu (`status: saving -> saved`), avec détection de session non enregistrée et restauration automatique.

#### 5. L'Assistant Réglementaire Intégré (`Advisor`)
- Accessible à tout moment via le tiroir latéral contextuel.
- Fournit des explications juridiques vulgarisées sur chaque rubrique ("Comprendre ce champ", "Où trouver cette information").
- Référencé directement sur les textes et guides du RNE et de la DGI.

---

### Architecture logicielle et pile technologique

```
+-------------------------------------------------------------------------+
|                              FRONTEND                                   |
|  Next.js 14 (App Router) + TypeScript + Vanilla Modern CSS             |
|  - App Shell, Sidebar, Topbar (globals.css)                             |
|  - Atelier Form Wizard RNE F005 (form-studio.css)                       |
|  - Lucide Icons + Google Variable Fonts (Manrope, Plus Jakarta Sans)    |
+------------------------------------+------------------------------------+
                                     |  REST API / JSON / Multipart
+------------------------------------+------------------------------------+
|                              BACKEND                                    |
|  FastAPI (Python 3.11 asynchronous)                                     |
|  - main.py : Orchestration des dossiers & documents                     |
|  - form_routes.py : Gestion des états de draft, validation & PDF        |
|  - form_catalog.py : Répertoire réglementaire officiel F005 v1.1        |
|  - rules.py : Moteur de règles de cohérence et conformité               |
|  - store.py : Persistance transactionnelle JSON sécurisée               |
+------------------------------------+------------------------------------+
                                     |
+------------------------------------+------------------------------------+
|                          MOTEUR IA & OCR                                |
|  - Azure Document Intelligence / OCR Local Windows                      |
|  - Moteur de génération PDF vectoriel ReportLab / PyMuPDF               |
+-------------------------------------------------------------------------+
```

---

## 4. Script Verbatim pour le Pitch (Timing 3:00)

### [0:00 - 0:30] L'Accroche & Le Problème (30 secondes)
> *"Bonjour à tous. En Tunisie, créer ou faire grandir une entreprise est un acte de bravoure. Mais dès qu'il s'agit de modifier une simple adresse ou un gérant au RNE, c'est le parcours du combattant.  
> Plus de 40 % des dossiers déposés sont rejetés au guichet pour une virgule, une faute d'orthographe ou une divergence d'adresse entre la patente fiscale et les statuts.  
> Résultat : des semaines de blocage pour les entrepreneurs, et des agents du RNE et de la DGI submergés par la paperasse et les réclamations.  
> C'est pour briser cette impasse que nous avons créé **Dossier TN**."*

### [0:30 - 1:15] La Solution & La Démo (45 secondes)
> *"Dossier TN est la première plateforme intelligente B2G de conformité réglementaire pensée pour les entreprises tunisiennes.  
> Comment ça marche ?  
> L'entrepreneur dépose ses pièces : sa Patente, son Extrait RNE, sa CIN.  
> Notre moteur d'OCR extrait instantanément toutes les données clés.  
> Mais nous ne faisons pas que lire : notre algorithme compare les pièces entre elles. S'il détecte que l'adresse du PV ne correspond pas à la patente, il alerte immédiatement l'usager avec la preuve à l'écran.  
> Puis, notre Atelier interactif guide l'entrepreneur pas à pas dans le formulaire officiel RNE F005, en arabe et en français, avec des explications claires.  
> En 8 minutes, le dossier est complet, audité et prêt pour le dépôt officiel."*

### [1:15 - 2:00] THE AGENCY BENEFIT — Slide Obligatoire (45 secondes)
> *(Changer de slide : Slide 5 - The Agency Benefit)*  
> *"Passons maintenant au cœur de notre impact institutionnel : **The Agency Benefit**.  
> Si le RNE et la DGI se connectent à Dossier TN, voici exactement ce que leurs agents vont économiser chaque mois :  
> **Premièrement : 720 heures de travail manuel économisées par mois et par agence régionale.** Le temps de traitement d'un dossier passe de 35 minutes de contrôle fastidieux à moins de 6 minutes de validation numérique.  
> **Deuxièmement : 85 % de rejets au guichet en moins.** Fini les erreurs de saisie et les matricules invalides : le dossier arrive propre, cohérent et certifié en amont.  
> **Troisièmement : une réduction de 60 % de l'affluence physique aux guichets.** Moins de tension, des agents qui se concentrent sur le conseil juridique à forte valeur ajoutée, et des files d'attente qui disparaissent.  
> Dossier TN n'est pas seulement un outil pour les entreprises, c'est l'accélérateur digital dont nos administrations publiques ont urgemment besoin."*

### [2:00 - 2:40] Modèle Économique & Scalabilité (40 secondes)
> *"Notre modèle économique repose sur un partenariat B2G gagnant-gagnant avec les institutions publiques, combiné à un modèle SaaS pour les experts-comptables et fiduciaires qui gèrent des dizaines de formalités par mois.  
> Notre architecture est d'ores et déjà prête à s'étendre à la création d'entreprise (formulaire F001), à la radiation (F003) et à la délivrance automatisée des quittances fiscales de la DGI."*

### [2:40 - 3:00] Conclusion & Appel (20 secondes)
> *"Au sein de Hack4Justice et dans l'esprit de HiiL, nous croyons profondément à une justice administrative centrée sur l'humain. La conformité ne doit plus être un obstacle, mais un tremplin pour l'économie tunisienne.  
> Avec Dossier TN, franchissons ensemble le pas d'une administration moderne, juste et sans papier. Merci !"*

---

## 5. Anticipation des Questions du Jury (FAQ Défense)

### Q1 : "Est-ce que votre outil remplace l'agent du RNE ou le dépôt officiel ?"
> **Réponse :**  
> *"Absolument pas. Dossier TN respecte scrupuleusement la souveraineté de l'institution. Nous sommes un outil de préparation, d'audit et de fiabilisation en amont. L'agent public conserve 100 % de son pouvoir régalien de décision et de signature. Notre mission est de lui fournir un dossier irréprochable et pré-vérifié pour lui faire gagner 80 % de son temps d'instruction."*

### Q2 : "Comment gérez-vous la confidentialité et la sécurité des données des entreprises tunisiennes ?"
> **Réponse :**  
> *"Toutes les données extraites sont stockées localement ou sur des serveurs souverains sécurisés respectant la loi organique tunisienne n° 2004-63 sur la protection des données à caractère personnel (INPDP). Aucune donnée d'entreprise n'est utilisée pour entraîner des modèles publics tiers."*

### Q3 : "Que se passe-t-il si l'OCR fait une erreur de lecture sur un document manuscrit ou dégradé ?"
> **Réponse :**  
> *"C'est précisément l'une des forces de Dossier TN : l'humain est toujours dans la boucle. Chaque information extraite par l'OCR affiche un score de confiance et un lien direct vers la page originale. L'utilisateur a l'obligation de relire et peut modifier n'importe quel champ en un clic. L'IA assiste, l'usager valide."*

### Q4 : "Pourquoi vous concentrer sur le F005 plutôt que la création d'entreprise ?"
> **Réponse :**  
> *"Parce que la création d'entreprise ne se fait qu'une seule fois dans la vie d'une société, alors que les modifications statutaires (F005) surviennent tout au long de son existence (changement de siège, nomination d'associés, cession de parts, mise à jour bancaire). C'est là que se concentrent les goulets d'étranglement administratifs les plus coûteux au quotidien."*
