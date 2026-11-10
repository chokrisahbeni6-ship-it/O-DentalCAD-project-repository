# DentalCAD R12 — rapport de validation partielle

Date : 2026-10-19. Périmètre : essais synthétiques de laboratoire non clinique.

## Résumé

**Résultats partiels positifs ; campagne stricte non validée.** Le code source du paquet a été extrait dans un répertoire de travail et les tests numériques qui ne nécessitent pas les dépendances de production ont été exécutés. Aucun Docker/Podman n'est disponible dans cet environnement, et l'accès réseau au dépôt Python échoue par résolution DNS ; bcrypt ne peut donc pas être installé ici.

## Exécutions réussies

- `pytest -q backend/tests/test_upload_helpers_source_isolated.py backend/tests/test_registration_math.py backend/tests/test_guide_ray_check.py` : **16 passed**, 1,35 s.
- `research/validation/benchmark_registration.py` : exit 0. Erreur translation 0,0038267 mm ; erreur rotation 0,0096083° ; TRE moyen 0,0041575 mm ; TRE P95 0,0061170 mm ; TRE max 0,0072978 mm ; déterminant rotation 0,9999999999999989.
- `research/validation/benchmark_registration_matrix.py` : exit 0 ; **9/9 cas** dans les limites numériques configurées. Erreur translation max 0,0067356 mm ; rotation max 0,0618652° ; TRE P95 max 0,0223786 mm.
- `node --check frontend/app.js` : exit 0.
- `bash -n research/validation/run_synthetic_campaign.sh` : exit 0.
- Archive source : structure ZIP vérifiée lors de l'extraction.

## Bloqueurs / non exécutés

- `bcrypt==4.0.1` absent. Tentative `pip install bcrypt==4.0.1` impossible : le DNS vers l'index de paquets ne résout pas.
- Docker/Podman absent : l'image `Dockerfile.validation` n'a pas été construite ; le service Redis et l'entrypoint strict ne sont pas exécutés.
- Les tests d'intégration API et les tests DICOM exigeant SimpleITK/pydicom n'ont pas été comptés comme réussis dans cette passe.
- Le résultat global de la campagne stricte est **NON VALIDÉ / BLOQUÉ**, jamais PASS.

## Prochaine action

Sur une machine Linux avec Docker et accès au registre de paquets, exécuter `docker compose -f docker-compose.validation.yml build --no-cache`, puis `docker compose -f docker-compose.validation.yml up --abort-on-container-exit --exit-code-from r12-campaign`. Conserver les journaux et vérifier `CAMPAIGN_STATUS.txt` avant d'interpréter la campagne.

Les simulations sont synthétiques et ne constituent ni une validation clinique, ni une certification, ni une autorisation d'utilisation sur patient. DentalCAD reste un banc de recherche de laboratoire non clinique.
