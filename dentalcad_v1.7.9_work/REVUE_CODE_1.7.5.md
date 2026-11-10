# DentalCAD v1.7.5 — candidat revue de code

Corrections ciblées :
- Snapshot canonique JSONB et hash stockés dans plan_versions; génération du guide à partir du snapshot stocké.
- Persistance des axes et dent prévue dans implants.
- Table schema_version (version 2).
- Limite individuelle MAX_DICOM_FILE_BYTES (défaut 256 Mio), en plus du plafond global.
- Benchmark relié aux fonctions _kabsch/_icp de production.
- Tolérance de volume portée de 0,5 % à 2 %, avec écart relatif explicite dans l’erreur; seuil à confirmer sur jeux de maillages contrôlés.
- Orthanc épinglé à 24.8.2, healthcheck et dépendance du backend.

À valider sur l’environnement cible : disponibilité des tags Docker, healthcheck Orthanc/authentification, migration sur copie de base, tests d’API et benchmark. Cette archive n’est pas une validation clinique.

Compatibilité : les anciennes versions de plan sans canonical_plan sont lisibles via les colonnes d’implants; la génération de guide refuse explicitement les versions historiques sans snapshot canonique.


### Correctif complémentaire — modèle ImplantPlan
- Le champ facultatif `tooth` est désormais déclaré afin de préserver la dent planifiée lors de la validation Pydantic.
- `extra="forbid"` fait échouer explicitement les champs inattendus au lieu de les ignorer silencieusement.
- Ajout de tests de régression ciblés pour la conservation de `tooth` et le rejet des champs inconnus.
- Ces tests doivent encore être exécutés dans l’environnement backend complet.
