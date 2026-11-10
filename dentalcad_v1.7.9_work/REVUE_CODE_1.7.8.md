# DentalCAD v1.7.8 — validation métrologique et orientation

## Modifications

- Le visualiseur ré-échantillonne désormais le volume dans un repère patient orthogonal LPS avant de préparer les vues. Cela évite de présenter directement les axes d'une acquisition oblique comme des plans patient standards.
- Le volume conserve les espacements physiques et expose dans les métadonnées le repère LPS, l'origine et la matrice de direction.
- Les champs de métadonnées `hu_min` / `hu_max` ont été remplacés par `intensity_min` / `intensity_max` : les niveaux CBCT ne doivent pas être présentés comme des unités Hounsfield calibrées.
- Version API mise à jour en 1.7.8.
- Ajout d'un test géométrique de ré-échantillonnage sur une orientation connue.
- Ajout d'un banc d'essai de maillage sur une sphère analytique et intégration des bancs d'essai ICP/maillage à la suite pytest.

## Résultats exécutés

- `pytest -q` : **17 tests réussis**.
- `python -m compileall -q backend/app` : réussi.
- `node --check frontend/app.js` : réussi dans l'environnement courant.
- Maillage synthétique (grille anisotrope 0,4 × 0,5 × 0,6 mm, sphère de rayon 10 mm) : 3 861 sommets, 7 718 triangles; erreur radiale absolue moyenne 0,099 mm, P95 0,132 mm, maximum 0,175 mm; erreur du centroïde 0,008 mm.
- ICP synthétique : erreur de translation 0,00383 mm, erreur de rotation 0,00961°, TRE P95 0,00612 mm sur le scénario testé.

## Limites importantes

- Le banc de maillage est **approximatif** : il utilise SciPy pour le lissage volumique et ne peut pas appeler directement `_export_mask_to_stl`, car SimpleITK n'est pas installé dans l'environnement courant. Ses métriques ne sont donc pas une preuve exacte du comportement de l'exporteur de production.
- Les résultats ICP et maillage sont synthétiques, avec des géométries idéalisées. Ils ne prouvent pas l'exactitude sur des données cliniques.
- Le ré-échantillonnage LPS est couvert par un test de géométrie simulé, mais pas encore par un véritable DICOM oblique de référence.
- Les tests ne valident pas la segmentation anatomique, la détection du nerf mandibulaire, la segmentation des sinus, la densité osseuse calibrée ni les distances de sécurité implantaires.
- Docker/Orthanc et le parcours Windows complet ne sont pas validés dans cet environnement.

## Prochaine validation nécessaire

1. Exécuter avec les dépendances complètes (dont SimpleITK) pour tester directement l'exporteur STL de production.
2. Comparer à un fantôme géométrique étalonné ou à une référence STL/CBCT connue.
3. Tester les vues sur des DICOM standards et obliques avec marqueurs anatomiques connus et vérifier droite/gauche avec un praticien.
4. Évaluer le recalage sur des paires scan de surface/CBCT réelles avec points de contrôle indépendants et erreurs TRE.
