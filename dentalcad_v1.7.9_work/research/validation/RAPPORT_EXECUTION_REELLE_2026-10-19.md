# DentalCAD R12 — rapport d'exécution réel

Date : 2026-10-19. Périmètre : tests synthétiques de laboratoire non clinique.

## Verdict global

**CAMPAGNE COMPLÈTE NON VALIDÉE.** Les benchmarks mathématiques ciblés ont été exécutés dans cet environnement, mais les tests d'intégration API et les tests DICOM fondés sur SimpleITK n'ont pas pu tous être exécutés. Aucun moteur Docker/Podman n'est disponible. Ne pas assimiler les résultats de repli à une validation du pipeline de production.

## Tests exécutés avec résultats

- `research/validation/benchmark_registration.py` : exit 0. Erreur de translation = 0,0038267 mm ; erreur de rotation = 0,0096083° ; TRE moyen = 0,0041575 mm ; TRE P95 = 0,0061170 mm ; TRE max = 0,0072978 mm. Déterminant rotation ≈ 1 ; erreur d'orthogonalité ≈ 4,15e-15.
- `research/validation/benchmark_registration_matrix.py` : exit 0 ; 9 cas exécutés (bruit 0/0,03/0,1 mm et fractions d'outliers 0/15/30 %). Pire erreur de translation observée ≈ 0,006736 mm ; pire erreur rotation ≈ 0,06187° ; pire TRE P95 ≈ 0,02238 mm. Résultats sur nuages synthétiques, pas sur acquisitions CBCT réelles.
- `research/validation/benchmark_oblique_pipeline_fallback.py` : exit 0 ; grille source oblique synthétique, direction déterminant 1,0 ; maillage 5 928 sommets / 11 852 triangles ; erreur de frontière moyenne ≈ 0,3588 mm, P95 ≈ 0,5215 mm ; recalage connu pratiquement exact. Ce chemin de repli utilise SciPy/VTK, pas SimpleITK ni la chaîne de production DICOM.
- `backend/tests/test_upload_helpers_source_isolated.py` : 4 tests réussis.
- `backend/tests/test_real_geometry_integration.py` : 1 réussi, 2 ignorés.
- `node --check frontend/app.js` : réussi.
- `bash -n research/validation/run_synthetic_campaign.sh` : réussi.

## Tests bloqués / non réussis

- `backend/tests/test_api_upload_integration.py` : échec de collecte car `bcrypt` n'est pas installé (`ModuleNotFoundError`). Les tests API ne sont donc pas validés.
- `backend/tests/test_oblique_dicom_roundtrip.py` et `backend/tests/test_full_synthetic_dicom_to_registration.py` : chacun 1 test ignoré car SimpleITK/pydicom requis n'est pas disponible dans cet environnement.
- `benchmark_mesh.py` : dépasse le délai de 20 secondes lors de cette tentative ; ne pas considérer le benchmark maillage comme exécuté lors de cette passe.
- La campagne groupée n'a pas terminé dans le délai de cette session ; son résultat global est donc indéterminé/échec, pas PASS.
- Docker/Podman absent ; build d'image, service Redis réel et campagne dans le conteneur non exécutés.

## Dépendances absentes constatées

`SimpleITK`, `pydicom`, `redis`, `bcrypt`, `jose`. Présents : Python 3.13.5, pytest, NumPy, SciPy, VTK, FastAPI, SQLAlchemy, trimesh, httpx, python-multipart.

## Prochaines actions techniques

1. Exécuter sur Linux/Docker avec les versions épinglées de `backend/requirements.txt` (Python 3.11 recommandé par le kit).
2. Faire réussir l'installation complète des dépendances avant pytest.
3. Exécuter les tests API upload, round-trip DICOM oblique et pipeline complet sans skip.
4. Lancer l'export de surface de production puis comparer erreur de surface, coordonnées et recalage sur un fantôme unique avec repères connus.
5. Archiver les journaux Docker réels et vérifier qu'aucune étape requise n'est ignorée.

Les valeurs mesurées ici caractérisent uniquement des simulations numériques. DentalCAD reste un banc de recherche de laboratoire non clinique ; aucune validation clinique, certification ou aptitude à l'usage sur patient n'est revendiquée.
