# DentalCAD R12 — campagne de tests synthétiques et chemin de production

**Destination : laboratoire exclusivement non clinique.** Graine déterministe : 20261018.

## Résultats réellement exécutés dans cet environnement

### A. Helpers de chargement DICOM de production — 4 tests réussis
Les fonctions `_stream_upload_to_path` et `save_dicom_uploads` ont été extraites par AST depuis `backend/app/main.py` et exécutées sans modifier leur corps. Cas vérifiés : série valide, DICOM invalide avec nettoyage, plafond cumulé, plafond par fichier.

**Portée exacte :** ces tests exercent les helpers réels, mais ne démarrent pas l'application FastAPI ni son routage HTTP, l'authentification, Redis ou le cycle de vie complet. Le test d'intégration API d'origine ne collecte toujours pas car `bcrypt` manque ; `python-jose` et `redis` manquent également.

### B. Fantôme géométrique oblique de repli — PASS
Script : `benchmark_oblique_pipeline_fallback.py`.
- Volume source : 80 × 76 × 64 ; espacement 0,45 × 0,55 × 0,70 mm ; direction oblique déterministe ; origine LPS non nulle.
- Rééchantillonnage indépendant SciPy sur grille alignée à 0,5 mm.
- Extraction de surface via VTK Marching Cubes : 5 928 points, 11 852 triangles.
- Couverture des voxels de premier plan par voisinage le plus proche : 98,891 %.
- Distance surface→frontière du fantôme source : moyenne 0,35877 mm ; P95 0,52146 mm ; maximum 0,65347 mm.
- Raffinement ICP du noyau de production : erreur de translation 1,25e-13 mm ; rotation 0° ; TRE P95 8,61e-14 mm.

**Interprétation critique :** la pose initiale est volontairement proche de la vérité terrain. L'erreur quasi nulle vérifie le raffinement local dans ce scénario, pas la convergence globale depuis une pose arbitraire.

### C. Recalage ICP — PASS
Benchmark de référence : erreur translation 0,0038267 mm ; rotation 0,0096083° ; TRE P95 0,0061170 mm.
Matrice de résistance : 9/9 scénarios respectent les seuils internes déclarés dans le benchmark.

### D. Maillage de référence approximatif — PASS
Benchmark SciPy de la sphère synthétique : erreur radiale absolue moyenne 0,09914 mm ; P95 0,13191 mm ; maximum 0,17450 mm. Ce n'est pas l'exporteur STL de production.

### E. Suite de régression ciblée — PASS
34 tests réussis, 3 ignorés, sur la suite antérieure. Les nouveaux tests isolés des helpers d'upload passent : 4/4. Le test DICOM oblique réel et le test de bout en bout sont correctement marqués pour ignorer l'exécution si pydicom/SimpleITK ne sont pas installés.

## Tentative d'exécution du chemin de production
- `benchmark_mesh_production.py` a été tenté et échoue immédiatement à l'import : `ModuleNotFoundError: No module named 'SimpleITK'`.
- Installation des dépendances exactes tentée via pip ; impossible car le runtime ne résout pas le DNS. Aucun paquet n'a été installé.
- `pydicom`, `SimpleITK`, `bcrypt`, `python-jose`, `redis` et `rtree` sont absents.
- Aucun vrai fichier DICOM n'a pu être lu par la fonction de production `read_series` dans cet environnement.
- Le test conditionnel `test_oblique_dicom_roundtrip.py` prépare une série DICOM synthétique oblique et vérifie taille, origine, espacement et direction LPS avec `read_series` quand les dépendances sont présentes.
- Le test conditionnel `test_full_synthetic_dicom_to_registration.py` prépare un même fantôme DICOM, exécute `read_series` → `segment_cbct_advanced` → exporteur STL de production → `icp_align`, puis vérifie la géométrie et les métriques du recalage. Il n'a pas pu être exécuté ici.

## Conclusion sans extrapolation
Les tests numériques exécutables localement passent. Les quatre helpers d'upload réels passent leurs tests unitaires isolés. **Les tests d'intégration HTTP, le rééchantillonnage SimpleITK sur DICOM oblique, l'exporteur de production et le pipeline DICOM→surface→recalage restent non exécutés** à cause des dépendances absentes et du réseau indisponible. Aucune réussite n'est revendiquée pour ces étapes.
