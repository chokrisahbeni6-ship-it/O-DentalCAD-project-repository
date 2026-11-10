# DentalCAD — rapport du fantôme numérique R7

## Objet
Tester le noyau de recalage réellement utilisé par DentalCAD (`app.registration_math._icp` et `_kabsch`) sur des nuages 3D synthétiques avec transformation rigide connue. Le test mesure l'erreur par rapport à la vérité terrain, en mm et en degrés.

## Benchmark de référence
Exécution de `benchmark_registration.py` depuis le projet R6, sans remplacer les fonctions de production :
- 1 200 points source asymétriques ; 1 380 points cible, dont 180 aberrants (15 %) ; bruit gaussien sigma = 0,03 mm.
- Erreur de translation : 0,003827 mm.
- Erreur de rotation : 0,009608°.
- TRE moyen : 0,004157 mm ; TRE P95 : 0,006117 mm ; TRE maximum : 0,007298 mm.
- Déterminant de rotation : 0,9999999999999989 ; erreur d'orthogonalité Frobenius : 4,15e-15.
- Les assertions du benchmark ont passé.

## Matrice de résistance
`benchmark_registration_matrix.py` exécute le noyau ICP de production sur 9 combinaisons : bruit sigma 0 / 0,03 / 0,10 mm et taux d'aberrants 0 / 15 / 30 %.
- Résultat : **9/9 cas passent** les seuils d'ingénierie de ce banc d'essai : translation < 0,15 mm, rotation < 0,2°, TRE P95 < 0,15 mm.
- Cas le plus sévère (sigma 0,10 mm, 30 % d'aberrants) : translation 0,006736 mm, rotation 0,061865°, TRE P95 0,022379 mm, TRE max 0,027112 mm.
- Les données sont générées par une graine fixe ; les résultats sont reproductibles.

## Tests du projet
Suite pytest exécutée dans le backend : **31 passed, 3 skipped**.

## Ce qui n'a pas été exécuté
- Le module complet `app.registration.register_points` importe SimpleITK, qui est absent de l'environnement d'exécution. Le benchmark appelle directement les fonctions de calcul de production `_icp` et `_kabsch`, pas l'import DICOM + extraction CBCT + ICP complet.
- Le rééchantillonnage de volumes DICOM obliques avec SimpleITK n'a pas pu être exécuté ; `pydicom` est également absent.
- Aucun fichier DICOM n'a été écrit/lu dans ce test, aucune acquisition réelle, aucun fantôme physique et aucune validation clinique.

## Interprétation
Ces résultats valident le comportement numérique du noyau ICP sur les scénarios synthétiques décrits. Ils ne démontrent pas l'exactitude clinique, la qualité du recouvrement de surfaces réelles, l'orientation patient sur des DICOM réels, ni la sécurité d'un guide implantaire. Les seuils sont des critères du benchmark et non des tolérances cliniques homologuées.
