# Exécuter la campagne R12 en Docker (laboratoire non clinique)

## Prérequis
- Docker Engine et le plugin Docker Compose v2 sous Linux.
- Accès au registre Docker et à l'index Python au premier build, ou caches d'images/roues équivalents.
- Espace disque suffisant pour VTK et SimpleITK.

## Exécution
Depuis la racine du dépôt :

```bash
mkdir -p research/validation/run_logs
# Vérifier d'abord que le fichier compose est valide.
docker compose -f docker-compose.validation.yml config
# Construire puis lancer le banc isolé.
docker compose -f docker-compose.validation.yml up --build --abort-on-container-exit --exit-code-from r12-campaign
# Nettoyer seulement le conteneur/réseau de validation (aucune donnée persistante n'est utilisée).
docker compose -f docker-compose.validation.yml down --remove-orphans
```

Les journaux sont enregistrés dans `research/validation/run_logs/`. Un échec de dépendance de production fait échouer la campagne en mode strict (`REQUIRE_PRODUCTION_TESTS=1`) au lieu d'être masqué par un succès partiel.

## Périmètre et précautions
- Le service Redis est temporaire et réservé à la campagne.
- Le réseau Docker de validation est `internal`; il n'expose aucun port.
- La base est une SQLite temporaire dans le conteneur, et aucune donnée patient n'est requise.
- Ne montez pas de répertoire DICOM réel, de secrets réels ou de volume de production dans cette stack.
- `pydicom==2.4.4` est explicitement épinglé, car les tests DICOM synthétiques l'utilisent et il n'était pas présent dans les exigences runtime initiales.
- Les outils pytest sont épinglés dans `requirements-validation.txt`; ils ne sont pas des dépendances runtime de l'application.
- Les résultats constituent des tests synthétiques de laboratoire, sans validation clinique ni certification.
