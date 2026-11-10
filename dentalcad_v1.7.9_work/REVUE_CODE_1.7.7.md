# DentalCAD v1.7.7 — correctifs de validation ciblés

## Changements réalisés
- `viewer.py` : correction du rapport d'aspect des coupes axiales lorsque les espacements X/Y sont anisotropes, en cohérence avec les coupes coronales et sagittales.
- `viewer.py` : validation explicite du volume 3D et des trois espacements voxel (valeurs positives et finies) avant rendu, pour éviter les divisions invalides et résultats incohérents.
- `main.py` : version d'API alignée sur l'archive candidate (`1.7.7`) au lieu de retourner à tort `1.6`.
- Ajout de `pytest.ini` : les tests peuvent être lancés depuis la racine avec `pytest -q`, sans configuration manuelle de `PYTHONPATH`.
- Ajout de tests de régression sur les proportions physiques et les entrées invalides du visualiseur.

## Vérifications locales
- `pytest -q` : 14 tests réussis.
- Benchmark ICP synthétique exécuté : erreur de translation ~0,00383 mm, rotation ~0,00961° dans le scénario testé. Ces chiffres synthétiques ne constituent pas une validation clinique.

## Limites restantes
- Docker/Orthanc n'ont pas été testés en intégration dans cet environnement.
- Aucun détecteur automatique de nerf alvéolaire inférieur ou de sinus n'est ajouté.
- Le seuil CBCT reste non calibré; la visualisation et les mesures sont des outils de recherche à contrôler par le praticien.
