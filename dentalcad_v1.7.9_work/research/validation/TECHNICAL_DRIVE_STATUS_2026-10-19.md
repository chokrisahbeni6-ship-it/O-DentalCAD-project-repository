# DentalCAD R12 — état du pilotage technique

Date : 2026-10-19. Cible : outil de recherche/ingénierie pour laboratoire dentaire, données synthétiques uniquement.

## Mise en place des workers

Ajout de `.github/workflows/dentalcad-bot-workers.yml` avec quatre jobs distincts :
1. Worker A : tests cœur et syntaxe JavaScript.
2. Worker B : tests géométrie/orientation/métrologie et benchmarks.
3. Worker C : vérification du pin `bcrypt==4.0.1` et audit `pip-audit`.
4. Worker D : campagne stricte Docker, dépendante de la réussite des trois premiers jobs, avec vérification du statut exact et conservation des artefacts.

Le workflow est prévu sur push, pull request, lancement manuel et exécution hebdomadaire. Il s'agit de workers CI déterministes, pas de six agents IA autonomes qui se modifient mutuellement.

## Vérifications locales exécutées pendant ce tour

- Worker A : `21 passed` en 1,13 s.
- Worker B : `11 passed` en 1,33 s.
- Matrice de recalage : script terminé avec code 0 ; résultat conservé dans `agent_runs/worker_B_registration_matrix_rerun.json`.
- `node --check frontend/app.js` : code 0.
- Docker n'est pas disponible dans cet environnement ; `bcrypt`, `pydicom`, `SimpleITK` et `redis` ne sont pas installés dans l'interpréteur local. Par conséquent, aucune nouvelle campagne Docker n'est revendiquée comme exécutée.

## Limites

Les tests locaux sont ciblés et synthétiques. Le statut strict précédent reste bloqué/échoué jusqu'à une exécution réussie de la campagne complète dans Docker. Les jobs GitHub Actions ne seront pas considérés comme passés avant qu'un run réel ne soit visible avec tous les jobs verts et l'artefact de preuve.
