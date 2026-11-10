# DentalCAD R12 — équipe de bot workers

Ce dépôt configure une équipe de workers automatisés dans GitHub Actions. Ce ne sont pas des agents autonomes qui modifient le code en permanence : ils exécutent des contrôles déterministes à chaque push/PR, à la demande, et chaque semaine.

- **Worker A — code/tests cœur** : tests de logique prothétique, schéma de plan implantaire, recalage, guide-ray et helpers d'import ; vérification syntaxique JavaScript.
- **Worker B — audit indépendant** : géométrie, orientation, métrologie, matrice de recalage et benchmark de maillage.
- **Worker C — dépendances/sécurité** : confirme le pin bcrypt et exécute pip-audit.
- **Worker D — campagne stricte Docker** : ne démarre qu'après réussite des trois workers précédents ; construit l'image, lance Redis et la campagne synthétique isolée, puis exige le statut exact `R12_STRICT_CAMPAIGN_PASS`.

Les jobs A, B et C sont séparés pour que les résultats d'un seul worker ne puissent pas faire passer la campagne entière. Le worker D conserve les journaux même en cas d'échec. Un test ignoré/skippé ne compte pas comme réussi si le script strict le signale comme bloquant.

## Activation

Le workflow `.github/workflows/dentalcad-bot-workers.yml` s'exécute sur push, pull request, déclenchement manuel et chaque lundi. Pour l'utiliser, le projet doit être hébergé dans un dépôt GitHub avec GitHub Actions activé. Aucun résultat distant n'est revendiqué tant qu'un run n'a pas été exécuté.

## Sécurité et périmètre

Les données sont synthétiques, la base est temporaire et le réseau Docker de validation est interne. Ne pas utiliser de données identifiantes de patients. Les résultats logiciels ne constituent pas une validation clinique ou une autorisation de fabrication.
