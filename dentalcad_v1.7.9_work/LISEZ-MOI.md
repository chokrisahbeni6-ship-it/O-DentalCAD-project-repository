# DentalCAD v1.7.9 — banc d'essai de planification implantaire

**Statut : OUTIL DE RECHERCHE ET D'APPRENTISSAGE. Ne jamais l'utiliser pour décider d'un geste sur un patient.**
Aucune validation clinique, aucune certification (dispositif médical, marquage CE), guide non utilisable en bouche.
Pour un patient réel : un logiciel de planification certifié (par exemple RealGUIDE).

---

## 1. Ce que contient cette version (v1.7.9)

| Étape | Fonction | État |
|---|---|---|
| 1 | Import du CBCT (DICOM) | **Fait.** Choix automatique de la plus grande série du dossier ; refus des fichiers non DICOM ; limites de taille |
| 2 | Orientation, panoramique | **Très partiel.** Coupes axiale, coronale, sagittale seulement (visualiseur). Pas de panoramique |
| 3 | Segmentation de l'os | **Partiel.** Seuil unique réglable + seuil d'Otsu suggéré (indicatif) + séparation manuelle des mâchoires à une coupe choisie |
| 4 | Nerf et sinus | **Pas de détection automatique** (volontaire : une détection non validée rassurerait à tort). **Règle de mesure** dans le visualiseur ; le repérage reste à votre charge |
| 5 | Calage scan de surface ↔ CBCT | **Partiel, non validé sur de vrais scans.** Vrai algorithme ICP, 24 départs, refus au-delà de 0,5 mm d'erreur, **refus si le résultat est instable** |
| 6 | Planification | **Partiel.** Axe d'implant (35° max), dent prévue facultative, rapport (écarts entre implants sur toute leur longueur, écart axe-dent). Pas de dent virtuelle |
| 7 | Bibliothèque d'implants | **Mécanisme fait, données absentes.** Seul le système `TEST` existe, marqué non vérifié. À remplir depuis les catalogues des fabricants |
| 8 | Guide | **Plaque de test uniquement.** Trous suivant l'axe, contrôles de paroi, de bord et de volume. Pas d'appui dentaire, pas de manchons |
| 9 | Export | STL de test téléchargeable. Aucun protocole de forage |

Sécurité du logiciel : comptes avec rôles, inscription réservée à l'administrateur, secrets dans `.env`, ports fermés au réseau
(127.0.0.1 seulement), données isolées par utilisateur, plans **versionnés** avec **validation obligatoire par le praticien**
(le guide n'est généré que depuis un plan validé et identique à celui en base), journal d'audit, effacement automatique des
résultats après 7 jours, sauvegarde `scripts\backup.ps1`.

---

## 2. Installation

**Prérequis** : Windows, Docker Desktop **lancé** (icône de baleine stable).

### Première installation
1. Dézippez dans `C:\dentalcad`.
2. Copiez `.env.example` en `.env` et remplissez-le (secrets aléatoires : commande indiquée dans le fichier ; `ADMIN_EMAIL` et
   `ADMIN_PASSWORD` de 12 caractères minimum). **Ne partagez jamais ce fichier.**
3. Dans PowerShell, dossier `C:\dentalcad` : `docker compose up -d --build` (5 à 15 minutes la première fois).
4. Contrôle : http://127.0.0.1:8010/health doit afficher `"version":"1.7.9"`.
5. Jeu de test synthétique (facultatif) :
   `docker compose exec backend python -m app.make_test_data` puis `docker compose cp backend:/tmp/testdata ./testdata`.
6. Ouvrez http://127.0.0.1:5173 et connectez-vous.

### Mise à jour depuis une version précédente — sauvegarde obligatoire
1. **Arrêtez-vous avant toute mise à jour** et faites une sauvegarde datée du dossier `C:\dentalcad` et de la base de données. Ne remplacez jamais l'unique copie.
2. Décompressez la nouvelle archive dans un dossier temporaire, par exemple `C:\dentalcad_update` — **pas directement dans `C:\` et sans option `-Force`**.
3. Comparez les fichiers et recopiez les fichiers applicatifs dans `C:\dentalcad` seulement après avoir vérifié que `.env`, les données `reel`/`testdata` et les volumes de base de données sont préservés.
4. Dans PowerShell, exécutez `docker compose up -d --build backend`, puis `docker compose ps` et vérifiez `/health`.
5. En cas d'erreur, arrêtez les conteneurs et restaurez la sauvegarde avant toute nouvelle tentative.

Ne lancez pas cette procédure sur des données patient réelles : cette version reste un banc de recherche non validé cliniquement.

### Après un redémarrage de l'ordinateur
Lancez Docker Desktop, attendez 1 à 2 minutes, puis `docker compose up -d`. La page vous déconnecte : reconnectez-vous.
Vos données sont conservées.

---

## 3. Utilisation de la page de test (http://127.0.0.1:5173)

1. **Connexion**, puis 2. **Patient et cas** : utilisez des codes **anonymes** (`REEL-001`), jamais de nom réel.
3. **Segmentation** : sélectionnez *tous* les fichiers DICOM (collez le chemin du dossier dans la barre d'adresse de la fenêtre,
   puis Ctrl+A). Seuil au choix ; coupe de séparation facultative (numéro lu dans le visualiseur, plan axial).
   Le résultat donne le volume osseux, un seuil suggéré, des avertissements.
4. **Calage** : mêmes DICOM + un STL de scan de surface. Le résultat est `ok` ou `rejected` (jamais de matrice si refusé).
   Même accepté, **contrôlez-le visuellement**.
5. **Plan d'implants** : chaque implant a `system_id` (voir « Voir la bibliothèque »), `diameter`, `length`, `position`
   (centre de la plateforme), et facultativement `axis` (direction vers l'apex) et `tooth` (dent prévue).
   « Enregistrer » crée une version et affiche le **rapport** ; lisez-le, puis « Je valide ce plan ».
6. **Guide** : STL de la gencive. Refusé si le plan n'est pas validé (409), si les implants sont trop proches (422), si les
   corps d'implants se chevauchent, ou si le contrôle de volume échoue. Résultat attendu pour le plan d'exemple : volume
   1406,555 mm³ (c'est celui obtenu lors des essais).
7. **Visualiseur** : coupes, seuils bas (jaune) et haut (rouge) en direct, règle (deux clics). « Effacer l'examen du serveur »
   quand vous avez fini : l'examen reste sinon 7 jours sur le disque du serveur.

---

## 4. Réglages (fichier `.env` ou variables du backend)

| Variable | Défaut | Rôle |
|---|---|---|
| `REG_MAX_RMS_MM` | 0,5 | erreur de calage au-delà de laquelle le résultat est refusé |
| `REG_MAX_SPREAD_MM` | 0,3 | instabilité de calage tolérée |
| `PROSTH_MIN_IMPLANT_GAP_MM` | 3 | alerte si deux implants sont plus proches (surface à surface) |
| `PROSTH_MAX_ANGLE_DEG` | 15 | alerte si l'axe de l'implant s'écarte de celui de la dent |
| `PROSTH_MAX_OFFSET_MM` | 1,5 | alerte si l'axe passe loin du centre de la dent |
| `RESULTS_RETENTION_DAYS` | 7 | conservation des résultats et examens chargés |

Les seuils `PROSTH_*` sont des **valeurs de départ prudentes** : remplacez-les par celles de votre protocole.

---

## 5. Ce qui a été testé, et ce qui ne l'a pas été

**Testé sur votre ordinateur** : démarrage complet ; connexion et création de cas ; segmentation du jeu synthétique et de
votre vrai CBCT (407 coupes, 0,32 mm : 236 cm³ à seuil 300, 148 cm³ à seuil 500) ; calage du jeu synthétique ; plan versionné
et validé ; guide du plan sain (volume vérifié à la main) ; **refus d'un plan non validé (409)** ; **refus d'implants trop
proches (422)**.

**Testé seulement par calcul isolé (pas dans le logiciel complet)** : visualiseur et règle, seuil d'Otsu, séparation des
mâchoires, test de stabilité du calage, bibliothèque d'implants, trous inclinés, rapport de plan.
Le premier lancement de ces fonctions est à faire sur des données **sans patient réel**, puis sur un examen anonymisé.

**Jamais testé** : calage sur un vrai scan de bouche ; guide sur un vrai scan intra-oral ; toute utilisation clinique.

---

## 6. Ce qui n'est pas résolu

1. Pas de HTTPS : acceptable tant que tout reste sur ce PC. Dès qu'un autre poste y accède : HTTPS et pare-feu.
2. Nerf alvéolaire inférieur et sinus : non détectés. Segmentation à seuil unique, non calibré (le CBCT n'est pas calibré en
   unités Hounsfield et varie selon l'appareil), dents et os non séparés.
3. Dimensions des implants : aucune donnée de fabricant fournie.
4. Guide ajusté aux dents/gencive, manchons de forage, dent virtuelle : absents.
5. Validation clinique : comparaison avec un logiciel certifié sur 20 à 30 cas, test du guide imprimé sur modèle.
6. Réglementaire : dispositif médical (MDR), RGPD / analyse d'impact, assureur, chiffrement du disque (BitLocker).
   Un examen contenant des données identifiantes est une donnée de santé : anonymisez avant import.
7. Dépendances : audit de sécurité à faire avec un développeur (`pip-audit`) ; FastAPI 0.110 et python-multipart 0.0.9
   ont des correctifs de sécurité non appliqués pour ne pas casser la compatibilité sans test.
8. Le journal d'audit est modifiable par un administrateur de la base (pas de signature cryptographique).

---

## 7. Dépannage rapide

| Symptôme | Cause probable et action |
|---|---|
| La page ne s'ouvre pas | Docker Desktop arrêté : le lancer, attendre, `docker compose up -d` |
| `failed to connect to the docker API` | Docker Desktop non démarré |
| « Volume 3D invalide » | fichiers DICOM incomplets sélectionnés : tout sélectionner (Ctrl+A dans le dossier) |
| `422 — …` sur le guide | champ manquant (fichier gencive, version) ou refus de sécurité : lire le message |
| `409 — Version introuvable ou déjà validée` | la version n'existe pas ou est déjà validée : enregistrer une nouvelle version |
| Rien ne s'affiche après un clic | Ctrl+F5, reconnexion ; sinon `docker compose logs backend --tail 80` |
| Backend « unhealthy » | `docker compose logs backend --tail 80` |


## Validation métrologique synthétique — premier résultat

Un banc d'essai indépendant est fourni dans `research/validation/benchmark_registration.py`.
Il utilise un nuage asymétrique de 1 200 points, une transformation rigide connue et un bruit gaussien de 0,03 mm ajouté au nuage cible. Les résultats calculés sont enregistrés dans `benchmark_registration_results.json`.

**Attention :** ce banc d’essai valide le calcul géométrique de référence dans un scénario synthétique contrôlé. Il ne constitue pas à lui seul une validation du pipeline d’enregistrement de production et ne démontre aucune précision clinique. Le module `app.registration` est utilisé par le backend ; ses performances doivent être vérifiées dans l’environnement backend complet, avec des jeux synthétiques et des acquisitions représentatives, puis complétées par des essais avec bruit, valeurs aberrantes et recouvrement partiel.

## Installation Windows sécurisée (script fourni)

Le fichier `INSTALLER.bat` vérifie Docker Compose, ne supprime pas le dossier
existant, ne remplace pas un `.env` présent et crée une copie horodatée du dossier
avant reconstruction. La copie locale **n'inclut pas les volumes Docker** : elle ne
remplace donc pas une sauvegarde PostgreSQL/Orthanc. Vérifiez ces sauvegardes séparément.
Le script ne crée pas automatiquement le compte administrateur et n'affiche aucun mot
de passe. L'API doit être vérifiée et les journaux examinés en cas d'échec.

Cette procédure n'a pas encore été validée sur une machine Windows/Docker réelle dans
cet environnement. Une réponse HTTP `/health` ne prouve ni la validité des plans
implantaires ni la sécurité clinique du logiciel.

### Sécurité et exploitation (R3)
- Les paramètres principaux sont centralisés dans `backend/app/settings.py`.
- Les journaux backend sont structurés en JSON via `backend/app/json_logging.py`.
- Une chaîne d'audit JSONL est ajoutée à `AUDIT_CHAIN_FILE` (par défaut `/data/results/audit-chain.jsonl`). Protégez ce fichier par permissions système et sauvegardes; cette chaîne locale n'est pas une signature externe et ne protège pas contre un administrateur capable de réécrire tout le fichier.
- Le limiteur HTTP est **par processus et par adresse IP**. Avant un déploiement multi-worker ou public, utilisez un limiteur partagé (reverse proxy ou Redis) et définissez `MAX_REQUESTS_PER_MINUTE` selon les besoins.
- `Caddyfile` donne un exemple de reverse proxy HTTPS pour un nom DNS public. Configurez `DENTALCAD_HOST`, DNS, pare-feu et certificats avant usage; ce fichier seul ne prouve pas que HTTPS est déployé.
- `.github/workflows/security.yml` exécute `pip-audit` et les tests à chaque push/PR et sur un calendrier hebdomadaire.


### R5 — limites de sécurité et déploiement
- Le rate-limiting HTTP utilise Redis et une fenêtre glissante atomique partagée. Si Redis est indisponible, l'API répond 503 (fail-closed). La limite par adresse IP dépend du fait que le proxy fournisse correctement l'adresse cliente; configurez explicitement les proxy headers et ne faites pas confiance à des en-têtes client arbitraires.
- La chaîne d'audit locale associe SHA-256 et HMAC avec `AUDIT_HMAC_KEY`; l'append refuse une chaîne dont l'intégrité ne se vérifie pas. Gardez la clé hors du volume de données et sauvegardez les événements vers un stockage distant append-only/WORM pour résister à un administrateur de l'hôte. Si la clé est accessible au même administrateur, le HMAC ne suffit pas.
- Caddyfile route `/api/*` et `/health` vers le backend local et le reste vers le frontend. Le HTTPS exige un DNS public, ports 80/443 ouverts, Caddy installé/exécuté sur l'hôte et `DENTALCAD_HOST` configuré. Aucun déploiement HTTPS réel n'est déclaré dans cette archive.
- Vérification locale: `cd backend && PYTHONPATH=. pytest -q`; validation Compose: `docker compose config`.

### R8 — corrections de sécurité et tests d'API
- `save_dicom_uploads` applique explicitement le plafond cumulé `MAX_UPLOAD_BYTES` à toute la série et supprime les fichiers partiels si un fichier échoue ou si la limite est dépassée. Tests d'intégration du helper d'upload ajoutés (série valide, DICOM invalide, limite cumulative).
- L'application refuse maintenant de démarrer si `AUDIT_HMAC_KEY` comporte moins de 64 caractères. Générer une clé aléatoire forte et la conserver hors du dépôt et des volumes de données.
- L'adresse utilisée pour le rate limit est `request.client.host`. `X-Forwarded-For` n'est volontairement pas utilisé : il peut être falsifié si le proxy de confiance n'est pas configuré. En déploiement Caddy, le backend doit rester accessible uniquement via loopback/réseau privé; ne publiez pas le port 8010 sur Internet. Si un proxy supplémentaire est introduit, configurer une liste explicite de proxies de confiance avant de faire confiance aux en-têtes transmis.
- Les tests API upload sont ajoutés, mais le test d'intégration complet via HTTP avec Postgres/Redis/Caddy doit être exécuté dans l'environnement Docker de déploiement.

## Destination d'utilisation — LABORATOIRE / NON CLINIQUE
DentalCAD est un outil expérimental destiné exclusivement à la recherche, au développement et aux essais techniques en laboratoire. Privilégier les fantômes numériques, les volumes synthétiques et les jeux de données de recherche contrôlés.

Il n'est pas destiné au diagnostic, à la planification ou à la conduite d'un acte sur un patient, à la fabrication d'un dispositif destiné à un patient, ni à une décision thérapeutique. Les sorties et mesures sont expérimentales, limitées aux scénarios effectivement testés, et ne constituent ni une validation clinique ni une certification réglementaire.

Les boutons de validation dans l'interface ne signifient qu'un état de test logiciel et ne constituent aucune validation clinique. Toute mention de "cas" ou de "plan" désigne un cas de laboratoire simulé.
