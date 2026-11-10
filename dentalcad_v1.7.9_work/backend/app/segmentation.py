"""Segmentation osseuse CBCT (méthode simple par seuil).

LIMITES CONNUES (à ne pas oublier) :
 - Le seuil est fixe et NON calibré : sur un CBCT, les niveaux de gris ne sont
   pas de vrais Unités Hounsfield et varient selon l'appareil.
 - Maxillaire / mandibule ne sont PAS séparés (l'ancienne coupe "à mi-hauteur"
   était fausse dès que le patient était un peu décalé).
 - Le nerf alvéolaire inférieur et le sinus ne sont PAS détectés.
 - Artéfacts métalliques non traités.
"""
import os

import numpy as np
import SimpleITK as sitk
import vtk
from vtk.util import numpy_support


def read_series(dicom_dir):
    reader = sitk.ImageSeriesReader()
    ids = reader.GetGDCMSeriesIDs(dicom_dir) or []
    if not ids:
        raise ValueError("Série DICOM vide")
    # Plusieurs séries dans le dossier (scouts, captures...) : on prend la plus
    # grande (le vrai volume 3D) au lieu de la première au hasard.
    best = max(ids, key=lambda sid: len(reader.GetGDCMSeriesFileNames(dicom_dir, sid)))
    names = reader.GetGDCMSeriesFileNames(dicom_dir, best)
    reader.SetFileNames(names)
    image = reader.Execute()
    if image.GetDimension() != 3 or min(image.GetSize()) < 8:
        raise ValueError("Volume 3D invalide")
    return image


def otsu_threshold(values, lo=0, hi=3000, bins=300):
    """Seuil d'Otsu sur les valeurs comprises entre lo et hi (l'air est exclu).
    Valeur INDICATIVE : sur un CBCT, l'échelle n'est pas calibrée."""
    v = np.asarray(values).ravel()
    v = v[(v > lo) & (v <= hi)]
    if v.size < 1000:
        return None
    hist, edges = np.histogram(v, bins=bins, range=(lo, hi))
    hist = hist.astype(np.float64)
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centers)
    mt = m0[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (w0 * w1) * ((m0 / w0) - ((mt - m0) / w1)) ** 2
    between = np.nan_to_num(between)
    return int(round(centers[int(np.argmax(between))]))


def split_mask_z(mask, split_z):
    """Sépare un masque (z, y, x) en deux parties à la coupe split_z (manuel)."""
    nz = mask.shape[0]
    if not 1 <= split_z <= nz - 1:
        raise ValueError(f"Coupe de séparation hors limites (1 à {nz - 1})")
    low = mask.copy(); low[split_z:] = 0          # indices < split_z
    high = mask.copy(); high[:split_z] = 0        # indices >= split_z
    return low, high


def segment_cbct_advanced(dicom_dir, output_dir, threshold=300, split_z=None):
    image = read_series(dicom_dir)
    arr = sitk.GetArrayFromImage(image)
    suggested = otsu_threshold(arr)
    bone = (arr > threshold).astype(np.uint8)
    if bone.sum() == 0:
        raise ValueError("Aucun voxel osseux au-dessus du seuil")

    bone_img = sitk.GetImageFromArray(bone)
    bone_img.CopyInformation(image)
    closed = sitk.BinaryMorphologicalClosing(bone_img, [3, 3, 3])

    cc = sitk.ConnectedComponent(closed)
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(cc)
    sizes = sorted(((l, stats.GetNumberOfPixels(l)) for l in stats.GetLabels()),
                   key=lambda x: -x[1])
    keep = [sizes[0][0]]
    if len(sizes) > 1 and sizes[1][1] > 0.1 * sizes[0][1]:
        keep.append(sizes[1][0])
    mask = np.isin(sitk.GetArrayFromImage(cc), keep).astype(np.uint8)

    os.makedirs(output_dir, exist_ok=True)
    _export_mask_to_stl(mask, image, os.path.join(output_dir, "bone.stl"))
    results = [{"name": "bone", "file": "bone.stl"}]
    warnings = ["Seuil fixe non calibré : à vérifier visuellement sur les coupes."]

    if split_z is None:
        warnings.append("Maxillaire/mandibule non séparés.")
    else:
        low, high = split_mask_z(mask, int(split_z))
        D = np.array(image.GetDirection()).reshape(3, 3)
        up_is_high_index = D[2, 2] > 0              # axe Z du scanner (patient : + = vers la tête)
        if abs(D[2, 2]) < 0.7:
            warnings.append("Acquisition oblique : le nom haute/basse n'est pas fiable.")
        parts = (("partie_haute", high), ("partie_basse", low)) if up_is_high_index \
            else (("partie_haute", low), ("partie_basse", high))
        for name, part in parts:
            if part.sum() == 0:
                warnings.append(f"{name} : aucun voxel osseux, non exporté.")
                continue
            _export_mask_to_stl(part, image, os.path.join(output_dir, name + ".stl"))
            results.append({"name": name, "file": name + ".stl"})
        warnings.append(f"Séparation MANUELLE à la coupe {int(split_z)} : les noms haute/basse "
                        "viennent de l'axe Z du scanner, à vérifier visuellement.")
    warnings.append("Nerf alvéolaire inférieur et sinus NON détectés (mesure manuelle seulement).")

    spacing = image.GetSpacing()
    return {
        "status": "ok",
        "results": results,
        "volume_shape": list(mask.shape),
        "method": "threshold_simple",
        "threshold": int(threshold),
        "bone_voxels": int(mask.sum()),
        "bone_volume_mm3": float(mask.sum() * spacing[0] * spacing[1] * spacing[2]),
        "suggested_threshold": suggested,
        "suggested_threshold_note": "Otsu, indicatif : à confirmer sur les coupes.",
        "warnings": warnings,
    }


def _export_mask_to_stl(mask, ref_image, out_path, decimate=0.5):
    """Export a binary 3D mask as an STL in the source image's physical frame.

    Coordinates are written in millimetres using the image origin, spacing and
    direction matrix. This is a geometric export only; it does not certify the
    anatomical accuracy of the segmentation.
    """
    mask = np.asarray(mask)
    if mask.ndim != 3 or any(n < 2 for n in mask.shape):
        raise ValueError("Le masque doit être un volume 3D non vide")
    if ref_image.GetDimension() != 3:
        raise ValueError("L'image de référence doit être 3D")
    expected_zyx = tuple(reversed(ref_image.GetSize()))
    if mask.shape != expected_zyx:
        raise ValueError(f"Dimensions du masque {mask.shape} incompatibles avec l'image {expected_zyx}")
    if not np.isfinite(mask).all():
        raise ValueError("Le masque contient des valeurs non finies")
    if not 0.0 <= float(decimate) < 1.0:
        raise ValueError("decimate doit être compris entre 0 inclus et 1 exclu")
    if not np.any(mask):
        raise ValueError("Le masque est vide : aucun maillage à exporter")

    mask_img = sitk.GetImageFromArray((mask > 0).astype(np.uint8))
    mask_img.CopyInformation(ref_image)
    # RecursiveGaussian requires a floating-point scalar image in SimpleITK.
    mask_float = sitk.Cast(mask_img, sitk.sitkFloat32)
    smoothed = sitk.SmoothingRecursiveGaussian(mask_float, 1.0)   # sigma = 1 mm
    arr = np.ascontiguousarray(sitk.GetArrayFromImage(smoothed).astype(np.float32))

    # 1) Surface extraite en coordonnées "voxel" (spacing 1, origine 0)
    vtk_img = vtk.vtkImageData()
    vtk_img.SetDimensions(*arr.shape[::-1])
    vtk_img.SetSpacing(1.0, 1.0, 1.0)
    vtk_img.SetOrigin(0.0, 0.0, 0.0)
    vtk_img.GetPointData().SetScalars(numpy_support.numpy_to_vtk(arr.ravel(order="C"), deep=True))

    mc = vtk.vtkMarchingCubes()
    mc.SetInputData(vtk_img)
    mc.SetValue(0, 0.5)
    mc.ComputeNormalsOff()
    mc.Update()

    # 2) Passage en coordonnées PHYSIQUES (mm) avec origine, espacement ET
    #    orientation (direction) du scanner : c'était omis dans la v1.2.
    spacing = np.array(ref_image.GetSpacing())
    origin = np.array(ref_image.GetOrigin())
    D = np.array(ref_image.GetDirection()).reshape(3, 3)
    M = np.eye(4)
    M[:3, :3] = D @ np.diag(spacing)
    M[:3, 3] = origin
    vm = vtk.vtkMatrix4x4()
    for i in range(4):
        for j in range(4):
            vm.SetElement(i, j, float(M[i, j]))
    tr = vtk.vtkTransform()
    tr.SetMatrix(vm)
    tf = vtk.vtkTransformPolyDataFilter()
    tf.SetInputConnection(mc.GetOutputPort())
    tf.SetTransform(tr)
    tf.Update()
    port = tf.GetOutputPort()

    if np.linalg.det(M[:3, :3]) < 0:          # repère "miroir" : recoller les faces
        rev = vtk.vtkReverseSense()
        rev.SetInputConnection(port)
        rev.ReverseCellsOn()
        rev.ReverseNormalsOn()
        rev.Update()
        port = rev.GetOutputPort()

    smoother = vtk.vtkWindowedSincPolyDataFilter()
    smoother.SetInputConnection(port)
    smoother.SetNumberOfIterations(15)
    smoother.Update()

    dec = vtk.vtkQuadricDecimation()
    dec.SetInputConnection(smoother.GetOutputPort())
    dec.SetTargetReduction(decimate)           # 50 % (70 % auparavant)
    dec.Update()

    writer = vtk.vtkSTLWriter()
    writer.SetFileName(out_path)
    writer.SetFileTypeToBinary()
    writer.SetInputConnection(dec.GetOutputPort())
    if dec.GetOutput().GetNumberOfPoints() < 3 or dec.GetOutput().GetNumberOfCells() < 1:
        raise ValueError("L'extraction de surface n'a produit aucun maillage exploitable")
    if writer.Write() != 1:
        raise OSError(f"Échec d'écriture du fichier STL : {out_path}")
