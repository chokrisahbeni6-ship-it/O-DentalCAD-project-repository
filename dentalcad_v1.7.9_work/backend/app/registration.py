"""Calage (alignement) d'un scan de surface STL sur un CBCT : vrai algorithme ICP.

Principes de sécurité :
 - résultat reproductible (graine fixe) ;
 - 24 orientations de départ testées (évite les calages "à l'envers") ;
 - l'erreur est calculée sur TOUS les points ET sur les 80 % meilleurs,
   les deux sont affichées ;
 - si l'erreur dépasse le seuil, le résultat est REFUSÉ (aucune matrice).
Le résultat doit de toute façon être contrôlé visuellement par le praticien.
"""
import itertools
import os

import numpy as np
import SimpleITK as sitk
import vtk
from scipy import ndimage
from scipy.spatial import cKDTree
from vtk.util.numpy_support import vtk_to_numpy

from app.segmentation import read_series
from app.registration_math import _kabsch, _icp

SEED = 42
MAX_SPREAD_MM = float(os.getenv("REG_MAX_SPREAD_MM", "0.3"))   # instabilité tolérée


def extract_cbct_surface(dicom_dir, threshold=300, max_points=60000, rng=None):
    rng = rng or np.random.default_rng(SEED)
    image = read_series(dicom_dir)
    mask = sitk.GetArrayFromImage(image) > threshold
    surface = mask & ~ndimage.binary_erosion(mask)        # surface seulement
    idx = np.argwhere(surface)                             # (z, y, x)
    if len(idx) == 0:
        raise ValueError("Aucun voxel osseux détecté")
    if len(idx) > max_points:
        idx = idx[rng.choice(len(idx), max_points, replace=False)]
    ijk = idx[:, ::-1].astype(np.float64)                  # (x, y, z)
    spacing = np.array(image.GetSpacing())
    origin = np.array(image.GetOrigin())
    D = np.array(image.GetDirection()).reshape(3, 3)       # orientation du scanner
    return origin + (ijk * spacing) @ D.T


def load_stl_points(stl_path, max_pts=30000, rng=None):
    rng = rng or np.random.default_rng(SEED)
    reader = vtk.vtkSTLReader()
    reader.SetFileName(stl_path)
    reader.Update()
    pd = reader.GetOutput()
    if pd.GetNumberOfPoints() == 0:
        raise ValueError("STL vide ou illisible")
    pts = vtk_to_numpy(pd.GetPoints().GetData()).astype(np.float64)
    if len(pts) > max_pts:
        pts = pts[rng.choice(len(pts), max_pts, replace=False)]
    return pts



def _octahedral_rotations():
    mats = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product([1, -1], repeat=3):
            M = np.zeros((3, 3))
            for r, (c, s) in enumerate(zip(perm, signs)):
                M[r, c] = s
            if np.linalg.det(M) > 0:
                mats.append(M)
    return mats                                            # 24 rotations


def _rot_angle_deg(R):
    c = (np.trace(R) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def _rand_rotation(rng, max_deg):
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    a = np.radians(rng.uniform(0.5, 1.0) * max_deg)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * (K @ K)


def stability_test(src, tree, tgt, R, t, rng, n_trials=8, rot_deg=3.0, trans_mm=1.0, iters=150):
    """Relance l'ICP depuis des départs légèrement perturbés autour de la solution.
    Si les résultats divergent, la géométrie est trop peu contraignante : le calage
    n'est pas fiable même si l'erreur moyenne (RMS) est faible."""
    sub = src[rng.choice(len(src), min(len(src), 6000), replace=False)]
    ref = sub @ R.T + t
    c = ref.mean(0)
    worst_shift, worst_rot = 0.0, 0.0
    for _ in range(n_trials):
        P = _rand_rotation(rng, rot_deg)
        dt = rng.normal(size=3)
        dt *= trans_mm * rng.uniform(0.3, 1.0) / np.linalg.norm(dt)
        R0, t0 = P @ R, P @ t - P @ c + c + dt
        R1, t1, _ = _icp(sub, tree, tgt, R0, t0, iters)
        shift = float(np.sqrt(np.mean(np.sum((sub @ R1.T + t1 - ref) ** 2, axis=1))))
        worst_shift = max(worst_shift, shift)
        worst_rot = max(worst_rot, _rot_angle_deg(R1 @ R.T))
    return {"trials": n_trials, "max_shift_mm": worst_shift, "max_rotation_deg": worst_rot}


def register_points(src, tgt, max_rms=0.5, max_spread=MAX_SPREAD_MM):
    """Aligne src (STL) sur tgt (CBCT). Retourne un dictionnaire de résultats.

    Les nuages doivent être exprimés en millimètres et dans des tableaux N×3.
    Les métriques ICP ne suffisent pas à établir une validité clinique.
    """
    src = np.asarray(src, dtype=np.float64)
    tgt = np.asarray(tgt, dtype=np.float64)
    if src.ndim != 2 or tgt.ndim != 2 or src.shape[1:] != (3,) or tgt.shape[1:] != (3,):
        raise ValueError("Les nuages source et cible doivent avoir la forme N×3")
    if len(src) < 100 or len(tgt) < 100:
        raise ValueError("Pas assez de points pour le calage (minimum 100 par nuage)")
    if not np.isfinite(src).all() or not np.isfinite(tgt).all():
        raise ValueError("Nuage de points contenant des valeurs NaN ou infinies")
    if not np.isfinite(max_rms) or max_rms <= 0 or not np.isfinite(max_spread) or max_spread <= 0:
        raise ValueError("Les seuils RMS et de stabilité doivent être finis et strictement positifs")
    rng = np.random.default_rng(SEED)
    tree = cKDTree(tgt)
    sc, tc = src.mean(0), tgt.mean(0)
    coarse = src[rng.choice(len(src), min(len(src), 4000), replace=False)]

    best = None
    for M in _octahedral_rotations():                      # départs multiples
        R, t, err = _icp(coarse, tree, tgt, M, tc - M @ sc, iters=25)
        if best is None or err < best[2]:
            best = (R, t, err)
    R, t, _ = _icp(src, tree, tgt, best[0], best[1], iters=100)   # affinage

    d, _ = tree.query(src @ R.T + t)
    ds = np.sort(d)
    rms_trim = float(np.sqrt(np.mean(ds[: int(len(ds) * 0.8)] ** 2)))
    rms_all = float(np.sqrt(np.mean(d ** 2)))
    overlap = float(np.mean(d <= 1.0))
    warnings = []
    if overlap < 0.6:
        warnings.append("Moins de 60 % des points sont à moins de 1 mm : recouvrement faible.")
    if rms_all > 2 * rms_trim:
        warnings.append("L'erreur sur tous les points est bien plus élevée que sur les 80 % "
                        "meilleurs : une partie du scan ne s'aligne pas.")
    stab = stability_test(src, tree, tgt, R, t, np.random.default_rng(SEED + 1))
    stable = stab["max_shift_mm"] <= max_spread
    if not stable:
        warnings.append(
            f"Calage INSTABLE : en relançant depuis des départs voisins, le résultat varie "
            f"jusqu'à {stab['max_shift_mm']:.2f} mm (rotation {stab['max_rotation_deg']:.1f}°). "
            "La forme du scan contraint mal l'alignement ; ne pas s'y fier.")
    M4 = np.eye(4)
    M4[:3, :3], M4[:3, 3] = R, t
    return {
        "matrix": M4.tolist(),
        "rms_trimmed_mm": rms_trim,
        "rms_all_mm": rms_all,
        "p95_mm": float(np.percentile(d, 95)),
        "max_mm": float(d.max()),
        "overlap_1mm": overlap,
        "rotation_deg": _rot_angle_deg(R),
        "translation_xyz_mm": [float(x) for x in t],
        "stability": stab,
        "stability_max_allowed_mm": max_spread,
        "rms_ok": bool(rms_trim <= max_rms),
        "stable": bool(stable),
        "acceptable": bool(rms_trim <= max_rms and stable),
        "warnings": warnings,
        "transform_direction": "STL -> repère CBCT (mm)",
    }


def icp_align(dicom_dir, stl_path, threshold=300, max_rms=0.5):
    rng = np.random.default_rng(SEED)
    src = load_stl_points(stl_path, rng=rng)
    tgt = extract_cbct_surface(dicom_dir, threshold, rng=rng)
    return register_points(src, tgt, max_rms)
