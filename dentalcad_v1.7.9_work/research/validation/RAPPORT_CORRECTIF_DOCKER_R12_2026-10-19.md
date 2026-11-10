# DentalCAD R12 — correctifs et état d'exécution

Périmètre : recherche synthétique de laboratoire, non clinique.

## Correctifs inclus
- `Dockerfile.validation` présent et installe `requirements-validation.txt`, qui inclut `backend/requirements.txt`.
- `.dockerignore` renforcé pour exclure secrets, bases locales, données d'imagerie et maillages du contexte de build.
- Compose monte le répertoire des journaux, pas le fichier `CAMPAIGN_STATUS.txt` lui-même, évitant le piège fichier absent interprété comme répertoire.
- Les trois chemins de tests de production requis existent dans le dépôt.
- Le runner écrit `R12_STRICT_CAMPAIGN_RUNNING`, puis `R12_STRICT_CAMPAIGN_PASS` ou `R12_STRICT_CAMPAIGN_FAIL`; les skips/imports dans les tests de production déclenchent un échec.

## Vérifications réalisées ici
- `bash -n research/validation/run_synthetic_campaign.sh` : réussi.
- `python -m compileall -q backend/app backend/tests research/validation` : réussi.
- `node --check frontend/app.js` : réussi.
- Parse YAML Compose et vérification de l'absence de bind-mount individuel du statut : réussis.
- Exécution locale en mode strict : échec explicite, car les dépendances de production sont absentes.

## Non exécuté
Aucun moteur Docker/Podman n'est disponible dans cet environnement. L'image n'a pas été construite, Redis réel n'a pas été lancé et les tests de production dépendant de SimpleITK/pydicom/bcrypt/jose/redis ne sont pas déclarés réussis.

Le passage complet exige une exécution Docker sur Linux/WSL2, des journaux montrant les tests de production exécutés sans skip, et une revue des métriques du fantôme. Ce kit n'est ni une validation clinique ni une certification.
