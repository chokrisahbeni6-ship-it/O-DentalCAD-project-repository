# DentalCAD R12 — exécution vérifiée et statut Docker

Date : 2026-10-19. Usage : banc de recherche de laboratoire exclusivement non clinique.

## Résultat observé dans l'environnement disponible

La campagne a été lancée localement depuis l'archive R12 :

- `bash research/validation/run_synthetic_campaign.sh` : code de sortie 0 pour la campagne partielle.
- Tests upload isolés et tests DICOM conditionnels : **4 passed, 2 skipped** (`run_logs/pytest_synthetic.txt`).
- Les quatre benchmarks synthétiques de repli ont été exécutés et leurs sorties écrites dans `run_logs/` : recalage, matrice de résistance, géométrie oblique SciPy/VTK et maillage de repli.
- Le statut `run_logs/production_dependencies.txt` indique explicitement que les tests de production sont ignorés faute de dépendances.
- Mode strict `REQUIRE_PRODUCTION_TESTS=1` : code de sortie **1**, avec le message attendu dans `run_logs/strict_mode_failure.txt`. Ceci empêche de confondre campagne partielle et campagne de production complète.

## Pourquoi Docker n'a pas pu être lancé ici

L'environnement courant est Linux x86_64 avec Python 3.13.5, mais aucun exécutable Docker ou Podman n'est disponible. Les modules `SimpleITK`, `pydicom`, `redis`, `bcrypt` et `jose` sont absents. Une tentative antérieure d'installation des dépendances avait échoué au niveau DNS. Sans moteur de conteneurs, accès aux images et dépendances compatibles, je ne peux pas construire ni démarrer honnêtement le conteneur dans cet environnement.

## Tests de production qui restent à exécuter

- Construction effective de `Dockerfile.validation`.
- Démarrage Redis réel et vérification `REDIS_PING_OK` depuis le conteneur de campagne.
- Intégration HTTP/API avec authentification et limites d'upload.
- Lecture/rééchantillonnage SimpleITK d'une série DICOM synthétique oblique.
- Export de surface par le moteur de production.
- Pipeline complet DICOM → segmentation → STL → recalage.

## Exécution sur une machine Linux avec Docker

Depuis la racine du projet :

```bash
docker compose -f docker-compose.validation.yml config
docker compose -f docker-compose.validation.yml up --build --abort-on-container-exit --exit-code-from r12-campaign
docker compose -f docker-compose.validation.yml down --remove-orphans
```

Inspecter `research/validation/run_logs/`. La réussite complète exige un code de sortie zéro **et** les journaux `pytest_production.txt` et `mesh_production.json` créés, sans statut `SKIPPED`. Le code zéro du mode non strict seul ne prouve pas que les tests de production ont été exécutés.

Aucun DICOM patient ni secret réel ne doit être monté dans ce banc de test. Ces résultats ne constituent ni validation clinique ni certification de DentalCAD.
