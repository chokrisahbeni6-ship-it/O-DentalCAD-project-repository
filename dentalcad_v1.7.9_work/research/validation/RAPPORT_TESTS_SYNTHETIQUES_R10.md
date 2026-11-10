# DentalCAD R10 — campagne de tests synthétiques

Date d'exécution : 2026-10-18. Portée : laboratoire / usage exclusivement non clinique.

## Résumé des tests exécutés

### 1. Noyau de recalage de production (`_kabsch` / `_icp`)
Commande : `python research/validation/benchmark_registration.py`
- Résultat : PASS.
- 1 200 points source asymétriques, transformation rigide connue, bruit gaussien sigma 0,03 mm, 180 points aberrants ajoutés à la cible.
- Erreur de translation : 0,0038267 mm.
- Erreur de rotation : 0,0096083°.
- TRE moyen : 0,0041575 mm ; P95 : 0,0061170 mm ; maximum : 0,0072978 mm.
- Déterminant de rotation : 0,9999999999999989 ; erreur d'orthogonalité : 4,15e-15.

### 2. Matrice de résistance ICP
Commande : `python research/validation/benchmark_registration_matrix.py`
- Résultat : 9/9 cas passent les seuils internes définis par ce benchmark.
- Paramètres : bruit sigma 0 / 0,03 / 0,10 mm ; taux de points aberrants 0 / 15 / 30 %.
- Cas le plus perturbé : erreur de translation 0,006736 mm ; erreur de rotation 0,061865° ; TRE P95 0,022379 mm ; TRE max 0,027112 mm.
- Seuils de ce test seulement : translation < 0,15 mm ; rotation < 0,2° ; TRE P95 < 0,15 mm.

### 3. Géométrie de surface synthétique
Commande : `python research/validation/benchmark_mesh.py`
- Résultat : PASS du benchmark approximatif SciPy, pas de l'exporteur de production.
- Sphère analytique de rayon 10 mm ; grille anisotrope 0,4 × 0,5 × 0,6 mm ; 3 861 points, 7 718 triangles.
- Erreur de centroïde : 0,00798 mm.
- Erreur radiale absolue moyenne : 0,09914 mm ; P95 : 0,13191 mm ; maximum : 0,17450 mm.
- Le script signale lui-même que le lissage et la voxelisation contribuent à l'erreur.

### 4. Suite ciblée des tests
Commande pytest ciblant les tests mathématiques, géométriques, ray-cast VTK, audit, métrologie, interface non clinique et contrat proxy :
- Résultat : **34 passed, 3 skipped**.
- Les tests ignorés comprennent des tests conditionnés par les dépendances optionnelles absentes.

### 5. Tests de production non exécutables dans cet environnement
- La suite complète ne collecte pas : `tests/test_api_upload_integration.py` échoue à l'import, car `bcrypt` est absent.
- `SimpleITK`, `pydicom` et `rtree` sont absents. Le test d'import/rééchantillonnage d'image oblique SimpleITK, l'exporteur STL de production utilisant SimpleITK/VTK et le ray-cast trimesh avec index spatial ne peuvent donc pas être déclarés passants ici.
- `benchmark_mesh_production.py` n'a pas été exécuté avec succès et ne doit pas être confondu avec `benchmark_mesh.py`.
- Aucun pipeline CBCT → DICOM → rééchantillonnage → extraction de surface → recalage complet n'est déclaré validé de bout en bout.

## Conclusion
Les tests synthétiques disponibles du noyau ICP, de la géométrie de surface approximative et du ray-cast VTK réussissent leurs critères déclarés. La couverture reste partielle : la campagne n'établit ni la validation du pipeline complet ni une performance clinique. Prochaine étape : installer les dépendances exactes du fichier `backend/requirements.txt` dans un environnement isolé, relancer tous les tests, puis exécuter le benchmark de production SimpleITK/VTK et le test de rééchantillonnage oblique.
