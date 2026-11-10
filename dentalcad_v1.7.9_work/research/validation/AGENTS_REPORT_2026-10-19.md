# DentalCAD R12 — rapport des deux agents (19-10-2026)

## Agent A — Coding Agent (inspection et corrections)
- Archive source extraite et son intégrité ZIP vérifiée.
- Copie de sauvegarde créée avant les exécutions.
- Dépendances et scripts de validation inspectés ; aucune modification d'authentification ni suppression de dépendance effectuée.
- Tests ciblés exécutés : `21 passed` en 1,02 s (`test_prosthetic.py`, `test_implant_plan_schema.py`, `test_registration_math.py`, `test_guide_ray_check.py`, `test_upload_helpers_source_isolated.py`).
- Benchmarks `benchmark_registration.py` et `benchmark_registration_matrix.py` terminés avec code 0.
- `node --check frontend/app.js` et vérifications de syntaxe Bash : code 0.

## Agent B — Validation Bot (contre-vérification indépendante)
- Deuxième groupe de tests exécuté séparément : `11 passed` en 1,71 s (`test_nonclinical_lab_label.py`, `test_viewer_geometry.py`, `test_viewer_orientation.py`, `test_metrology_benchmarks.py`).
- La matrice de recalage comporte 9 cas ; le JSON des résultats est conservé dans `agent_runs/coding_agent_registration_matrix.json`.
- Vérification de l'environnement : `bcrypt`, `pydicom`, `SimpleITK` et `redis` ne sont pas installés ; Docker n'est pas disponible.

## Résumé des résultats locaux
- 32 tests ciblés réussis au total dans les deux groupes (sans compter les benchmarks comme tests pytest).
- Les deux scripts de benchmark de recalage ont terminé avec code 0.
- JavaScript et scripts Bash syntaxiquement valides.
- La campagne stricte précédente reste `R12_STRICT_CAMPAIGN_FAIL`; ce rapport ne remplace pas ce statut.

## Limites et prochaine étape
Le chemin complet de production (authentification avec bcrypt, import DICOM avec pydicom/SimpleITK, Redis et Docker) n'a pas été validé dans cet environnement. Aucun PASS global n'est revendiqué. Prochaine étape : exécuter `bash research/validation/build_and_run_strict.sh` sur un hôte avec Docker Compose et accès au registre de paquets, puis conserver les logs et le statut exact.

Usage prévu : outil de recherche et d'ingénierie pour laboratoire dentaire. Résultats synthétiques uniquement ; ce rapport ne constitue pas une validation clinique.
