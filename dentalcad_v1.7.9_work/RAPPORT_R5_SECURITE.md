# DentalCAD v1.7.9 R5 — rapport de sécurité

## Changements réalisés
- Remplacement du limiteur HTTP en mémoire par un compteur Redis atomique en fenêtre glissante, partagé entre processus/instances utilisant la même base Redis.
- Politique fail-closed : l'API renvoie HTTP 503 si Redis est indisponible.
- Ajout d'une authentification HMAC-SHA256 des événements de la chaîne d'audit, avec vérification de l'intégrité avant tout nouvel ajout.
- Ajout d'un vérificateur de chaîne et de tests de détection de falsification et de mauvaise clé.
- Ajout du service Redis persistant dans Compose, de la dépendance Python Redis et de variables d'environnement documentées.
- Mise à jour de Caddyfile pour router les appels API vers le backend et le trafic applicatif vers le frontend.

## Vérifications exécutées dans l'environnement courant
- `PYTHONPATH=. pytest -q` : **27 passed, 3 skipped**.
- `python -m compileall -q backend/app backend/tests` : réussi.
- `node --check frontend/app.js` : réussi.
- `docker compose config` : non exécuté, car Docker n'est pas installé dans cet environnement.
- Déploiement Caddy/HTTPS réel : non exécuté (pas de serveur/DNS/ports de production disponibles).

## Limites et actions obligatoires avant exposition publique
- La sécurité du HMAC dépend du secret `AUDIT_HMAC_KEY`. Le secret doit être généré aléatoirement, stocké hors du volume de données et inaccessible à l'administrateur qui pourrait modifier le journal. Pour résistance à l'administrateur de l'hôte, exporter les événements vers un service distant append-only/WORM ou un système d'audit externe.
- Redis persistant AOF améliore la continuité mais ne constitue pas un service haute disponibilité ni une protection contre un administrateur de l'hôte. Prévoir réseau privé, ACL/secret Redis et sauvegardes adaptées avant production.
- Le proxy doit transmettre l'adresse client de façon fiable; ne pas accepter directement des en-têtes `X-Forwarded-For` non filtrés.
- Le fantôme physique, le recalage sur acquisitions réelles et les validations cliniques restent hors de cette livraison logicielle.
