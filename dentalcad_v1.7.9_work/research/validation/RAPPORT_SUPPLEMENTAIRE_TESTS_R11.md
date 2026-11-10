# DentalCAD — campagne supplémentaire de tests synthétiques R11

## Dépendances et limites d'environnement
L'archive R10 a été réouverte et inspectée. NumPy, SciPy, VTK et scikit-image sont disponibles. SimpleITK, pydicom, bcrypt, python-jose et rtree sont absents. L'installation réseau des paquets a échoué (DNS indisponible), donc les dépendances ne peuvent pas être ajoutées depuis cet environnement.

## Test de géométrie oblique de repli
Le nouveau script `benchmark_oblique_pipeline_fallback.py` exécute :
1. création d'un fantôme 3D asymétrique sur grille anisotrope (0,45 × 0,55 × 0,70 mm) avec direction oblique connue et origine LPS non nulle ;
2. rééchantillonnage indépendant via interpolation SciPy sur une grille physique alignée à 0,5 mm ;
3. extraction réelle de surface par VTK Marching Cubes ;
4. calcul de distance de surface vers la frontière du fantôme d'origine ;
5. recalage sur transformation rigide connue en appelant `_icp`/`_kabsch` de DentalCAD.

Résultat : PASS selon les critères définis dans le JSON. Le maillage compte 5 928 points et 11 852 triangles ; couverture des voxels de premier plan par voisinage le plus proche : environ 98,9 %. L'erreur de recalage est numériquement quasi nulle parce que le point de départ est volontairement proche de la vérité terrain. Cela vérifie le calcul de raffinement local, pas la capacité de convergence depuis une pose inconnue.

**Limite majeure :** ce test de repli n'utilise ni un fichier DICOM, ni SimpleITK, ni `read_series`, ni le vrai exporteur `_export_mask_to_stl`, ni `register_points`. Il ne remplace pas le test demandé de bout en bout avec les fonctions de production.

## Tests d'intégration API
Le test `test_api_upload_integration.py` a été relancé, mais sa collecte échoue à cause des dépendances absentes : d'abord `bcrypt`, puis `python-jose` lors d'une tentative isolée. Il n'est pas déclaré réussi. Les tests d'upload cumulatif nécessitent l'installation des dépendances déclarées et une exécution réelle de la suite.

## Suite de tests
La suite ciblée antérieure reste : 34 réussis, 3 ignorés. Le module API d'upload reste bloqué. Aucun service Docker/Redis/Caddy réel n'a été démarré ou validé dans cette session.

## Conclusion
Les tests supplémentaires renforcent les preuves sur une géométrie synthétique oblique, le rééchantillonnage indépendant, l'extraction VTK et le raffinement ICP local. Le pipeline CBCT/DICOM complet reste non validé de bout en bout. Usage exclusivement laboratoire/non clinique.
