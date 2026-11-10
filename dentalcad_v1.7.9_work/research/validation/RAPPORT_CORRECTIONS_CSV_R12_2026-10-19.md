# DentalCAD R12 — correction ciblée après audit CSV

Date : 2026-10-19

## Correction appliquée

`backend/app/prosthetic.py` ne suppose plus que `tooth["center"]` est toujours présent et valide. Si le centre est absent, mal formé ou contient des valeurs non finies, le rapport continue, ajoute un avertissement explicite et marque la ligne prothétique comme incomplète (`incomplete_missing_center`) ou invalide (`invalid_center`). Les métriques prothétiques ne sont pas calculées dans ces cas.

Un test de régression `backend/tests/test_prosthetic.py` couvre : centre absent, coordonnées invalides et calcul nominal avec centre valide.

## Tests exécutés ici

- `PYTHONPATH=backend pytest -q backend/tests/test_prosthetic.py backend/tests/test_implant_plan_schema.py` : **5 passed**.
- `PYTHONPATH=backend pytest -q backend/tests` : **non exécuté intégralement** ; collecte interrompue parce que le module `bcrypt` est absent (`ModuleNotFoundError`). Trois tests ont été ignorés pendant la collecte.

## Limites restantes

- La correction est une gestion robuste des données incomplètes, pas une validation clinique du calcul prothétique.
- Les tests d'intégration et les tests de production/DICOM ne sont pas validés par cette exécution.
- Les dépendances de production et Docker/Podman doivent être disponibles pour une campagne complète.

## Sauvegarde

L'archive source originale a été conservée séparément sous `dentalcad_backups/dentalcad_v1.7.9_R12_corrected_strict_20261019_original.zip` dans l'environnement de travail. Cette archive de sauvegarde n'est pas incluse dans le ZIP corrigé.
