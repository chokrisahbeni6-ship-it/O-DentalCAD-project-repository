# DentalCAD R12 — validation laboratoire (exécution actuelle)

Date : 2026-10-19. Objet : outil de recherche et d'ingénierie pour laboratoire dentaire. Tests sur données synthétiques uniquement.

## Résumé exécutif

**Validation stricte : FAIL / BLOQUÉE.** Les tests et benchmarks locaux qui ne dépendent pas de la pile de production ont été exécutés. Le mode strict a été lancé avec `REQUIRE_PRODUCTION_TESTS=1` et a terminé avec le code 1 et `R12_STRICT_CAMPAIGN_FAIL`, car des dépendances de production sont absentes. Docker n'est pas installé dans l'environnement actuel, donc aucune image n'a été construite.

## Résultats effectivement exécutés

- Tests ciblés : `16 passed` (1,11 s) pour `test_upload_helpers_source_isolated.py`, `test_registration_math.py`, `test_guide_ray_check.py`.
- Benchmarks de recalage, matrice de recalage, pipeline oblique fallback et maillage fallback : tous les quatre ont terminé avec le code 0.
- Matrice de recalage : 9 cas et critères numériques enregistrés dans `run_logs/registration_matrix_current.json`.
- Pipeline oblique fallback : `pass: true` pour les limites configurées. Limitation importante : SciPy/VTK fallback, pas un aller-retour DICOM SimpleITK de production.
- Maillage fallback : exécuté, mais l'erreur radiale P95 mesurée est d'environ 0,132 mm et l'erreur maximale d'environ 0,175 mm ; interpréter selon le protocole et les limites d'acceptation du laboratoire.
- `node --check frontend/app.js` : code 0.
- `bash -n` sur les scripts de validation : code 0.
- Campagne synthétique avec `REQUIRE_PRODUCTION_TESTS=1` : **code 1**, statut `R12_STRICT_CAMPAIGN_FAIL`. Le sous-ensemble synthétique a signalé `4 passed, 2 skipped`; ces deux tests ignorés ne sont pas comptés comme réussis.

## Blocages confirmés

- Docker CLI absent : image Docker non construite et non exécutée.
- Dépendances absentes dans le Python de travail : `bcrypt`, `pydicom`, `SimpleITK` (ainsi que les autres dépendances de production requises par le script).
- Tentative d'installation des paquets impossible dans cet environnement en raison de l'accès réseau/package-index indisponible dans la session précédente.
- Tests API/production et chemin DICOM complet non validés.

## Interprétation

Les résultats positifs concernent uniquement des tests ciblés et des benchmarks synthétiques de secours. Ils ne démontrent pas que le chemin complet d'import DICOM, de géométrie de production, d'authentification et d'intégration fonctionne. Ne pas déclarer la campagne complète PASS.

## Étape suivante

Sur un hôte de validation doté de Docker Compose et d'un accès au registre de paquets :

```bash
bash research/validation/build_and_run_strict.sh
```

Conserver le code de sortie et les journaux, puis vérifier `research/validation/run_logs/CAMPAIGN_STATUS.txt` contient exactement `R12_STRICT_CAMPAIGN_PASS`. Les tests sont synthétiques et ne constituent pas une validation clinique ou une autorisation d'utilisation sur patient.
