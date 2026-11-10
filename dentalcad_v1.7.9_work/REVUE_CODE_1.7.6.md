# DentalCAD v1.7.6 — révision technique candidate

## Corrections préparées
1. Règle du visualiseur : espacement physique calculé à partir des dimensions natives de la coupe et de l'étendue physique du volume; la mesure reste indicative.
2. Healthcheck Orthanc : le mot de passe est transmis explicitement à l'environnement du conteneur pour l'authentification Basic.
3. Import DICOM : lecture en blocs de 1 Mio vers disque, limites par fichier et par requête conservées; envoi vers Orthanc en flux depuis disque.
4. ICP : arrêt fondé sur le delta de rotation/translations plutôt que sur la variation du RMS.
5. Axe implantaire : refus des axes pointant vers +Z; convention documentée vers l'apex, Z négatif.
6. Kabsch : correction de déterminant binaire pour éviter `np.sign(det)==0` et une rotation singulière.
7. Benchmark : ICP de production, trim=0.8, cible avec points aberrants; résultats JSON régénérés à l'exécution du benchmark.
8. Compose : `REG_MAX_SPREAD_MM` passé au backend.
9. CSP Nginx : JavaScript externe dans `app.js`; suppression des gestionnaires JS inline.
10. Tests ciblés de `_norm_axis` et `_kabsch` ajoutés.

## Validation
La génération de cette archive ne prouve pas à elle seule le bon fonctionnement en conteneurs. Exécuter `pytest`, le benchmark, `docker compose config` et des essais d'intégration sur un jeu DICOM synthétique avant usage. Pas de validation clinique revendiquée.
