# Docker et secrets — DentalCAD

## Fichiers
- `backend/Dockerfile` construit le backend Python/FastAPI.
- `.env.example` est un modèle sans secrets. Copiez-le en `.env` puis remplissez les variables obligatoires.
- `.dockerignore` exclut les secrets, sauvegardes, bases locales et fichiers DICOM du contexte de construction.

## Secrets requis
`POSTGRES_PASSWORD`, `ORTHANC_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`. Utilisez des valeurs uniques et fortes. Pour générer une valeur aléatoire avec Docker :

```powershell
docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Générez une valeur distincte pour chaque secret. `JWT_SECRET_KEY` doit contenir au moins 32 caractères. Ne transmettez jamais `.env` et ne l'ajoutez pas à une archive destinée au partage.

## Contrôle préalable
Dans PowerShell, depuis le dossier `dentalcad` :

```powershell
Copy-Item .env.example .env  # uniquement si .env n'existe pas
notepad .env
docker compose config -q
docker compose build backend
docker compose up -d
docker compose ps
curl.exe http://127.0.0.1:8010/health
```

Ne lancez pas `Copy-Item` si un `.env` existe déjà : conservez votre configuration. Ne faites pas `docker compose down -v`, car cela supprimerait les volumes de données. Avant toute mise à jour, sauvegardez le dossier ET exportez la base PostgreSQL et les données Orthanc selon une procédure vérifiée.

## Limites des vérifications
La présence des fichiers ne prouve pas que l'image construit ou que l'application fonctionne. Exécutez les commandes ci-dessus sur la machine cible et conservez les journaux. Une réponse `/health` confirme seulement un contrôle technique, pas la validité clinique des résultats.
