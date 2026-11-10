# DentalCAD R8 — correctifs demandés

## Correctifs
1. Upload DICOM : plafond cumulatif explicite par série (`MAX_UPLOAD_BYTES`) et nettoyage des fichiers partiels en cas d'erreur. Tests d'intégration du helper d'upload.
2. Audit : clé HMAC courte/absente bloquante au démarrage, avant l'initialisation de la base.
3. Rate limit derrière proxy : politique explicite sans confiance en `X-Forwarded-For`; l'adresse socket cliente est utilisée. Le backend doit être privé derrière Caddy.
4. Tests : tests asynchrones de la fonction réelle `save_dicom_uploads`, incluant limite cumulée et nettoyage.

## Résultats observés dans cet environnement
- Tests existants (en excluant le nouveau module d’intégration qui importe l’application) : **31 passed, 3 skipped**.
- Compilation Python et vérification syntaxique JavaScript : réussies.
- Le nouveau module `test_api_upload_integration.py` n’a pas pu être collecté ici : dépendance `bcrypt` absente dans l’environnement. Ses tests ne sont donc pas comptés comme réussis.

## Limites de validation
- Les tests d’intégration nécessitent les dépendances de production complètes.
- Aucun test réseau complet Docker/Postgres/Redis/Caddy n'est déclaré sans environnement de déploiement actif.
- Le banc reste un projet de recherche non validé cliniquement.
