"""Visualiseur de coupes CBCT (lecture seule, aucun calcul clinique)."""
import json
import os
import struct
import zlib

import numpy as np

PLANES = ("axial", "coronal", "sagittal")


def _png_bytes(rgb: np.ndarray) -> bytes:
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 3))
            + chunk(b"IEND", b""))


def prepare_volume(dicom_dir: str, job_dir: str) -> dict:
    """Lit la plus grande série DICOM et la garde en .npy pour consulter les coupes."""
    import SimpleITK as sitk
    from app.segmentation import read_series
    img = read_series(dicom_dir)
    # Re-échantillonne les acquisitions obliques dans un repère patient LPS
    # orthogonal : sans cela, les plans nommés axial/coronal/sagittal peuvent
    # en réalité suivre les axes du scanner plutôt que ceux du patient.
    img = _resample_to_patient_lps(img, sitk)
    a = sitk.GetArrayFromImage(img).astype(np.int16)          # (z, y, x), axes LPS
    np.save(os.path.join(job_dir, "volume.npy"), a)
    sx, sy, sz = img.GetSpacing()
    meta = {
        "counts": {"axial": int(a.shape[0]), "coronal": int(a.shape[1]),
                   "sagittal": int(a.shape[2])},
        "spacing_xyz_mm": [round(sx, 4), round(sy, 4), round(sz, 4)],
        "intensity_min": int(a.min()), "intensity_max": int(a.max()),
        "coordinate_system": "LPS",
        "orientation_note": "Volume ré-échantillonné dans les axes patient LPS; affichage axial radiologique à confirmer sur un repère connu.",
        "origin_lps_mm": [round(float(v), 4) for v in img.GetOrigin()],
        "direction": [round(float(v), 6) for v in img.GetDirection()],
    }
    with open(os.path.join(job_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    return meta


def _resample_to_patient_lps(img, sitk_module):
    """Ré-échantillonne un volume dans un repère orthogonal patient LPS.

    LPS : X positif vers la gauche du patient, Y vers le postérieur, Z vers le
    supérieur. Les dimensions et l'origine sont calculées depuis les huit coins
    physiques du volume pour éviter de tronquer une acquisition oblique.
    """
    size = np.asarray(img.GetSize(), dtype=int)
    corners = []
    for x in (0, int(size[0] - 1)):
        for y in (0, int(size[1] - 1)):
            for z in (0, int(size[2] - 1)):
                corners.append(img.TransformIndexToPhysicalPoint((x, y, z)))
    corners = np.asarray(corners, dtype=np.float64)
    lower = corners.min(axis=0)
    upper = corners.max(axis=0)

    # Affectation globale un-à-un : chaque axe image ne peut servir qu'une fois.
    # L'algorithme hongrois évite les choix gloutons qui peuvent être sous-optimaux.
    from scipy.optimize import linear_sum_assignment
    direction = np.asarray(img.GetDirection(), dtype=np.float64).reshape(3, 3)
    old_spacing = np.asarray(img.GetSpacing(), dtype=np.float64)
    if direction.shape != (3, 3) or not np.isfinite(direction).all():
        raise ValueError("Matrice de direction DICOM invalide")
    world_axes, image_axes = linear_sum_assignment(-np.abs(direction))
    spacing_lps = np.empty(3, dtype=np.float64)
    for world_axis, image_axis in zip(world_axes, image_axes):
        spacing_lps[int(world_axis)] = old_spacing[int(image_axis)]

    out_size = np.ceil((upper - lower) / spacing_lps).astype(int) + 1
    if np.any(out_size < 1) or int(np.prod(out_size, dtype=np.int64)) > 250_000_000:
        raise ValueError("Ré-échantillonnage LPS trop volumineux; vérifier l'espacement CBCT")
    identity = sitk_module.Transform(3, sitk_module.sitkIdentity)
    return sitk_module.Resample(
        img, [int(v) for v in out_size], identity, sitk_module.sitkLinear,
        [float(v) for v in lower], [float(v) for v in spacing_lps],
        [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        -1024, img.GetPixelID(),
    )


def load_meta(job_dir: str) -> dict:
    with open(os.path.join(job_dir, "meta.json")) as f:
        return json.load(f)


def render_slice(vol, spacing_xyz, plane: str, index: int, low: int, high: int) -> bytes:
    """Coupe en niveaux de gris. Jaune : low < valeur <= high. Rouge : valeur > high."""
    if plane not in PLANES:
        raise ValueError("plan inconnu")
    vol = np.asarray(vol)
    if vol.ndim != 3 or any(n < 1 for n in vol.shape):
        raise ValueError("Le volume doit être un tableau 3D non vide (z, y, x)")
    spacing_xyz = np.asarray(spacing_xyz, dtype=np.float64)
    if spacing_xyz.shape != (3,) or not np.isfinite(spacing_xyz).all() or np.any(spacing_xyz <= 0):
        raise ValueError("L'espacement voxel doit contenir trois valeurs positives finies en mm")
    nz, ny, nx = vol.shape
    sx, sy, sz = spacing_xyz
    if plane == "axial":
        sl = np.asarray(vol[int(np.clip(index, 0, nz - 1))])
        # Une coupe axiale a pour lignes l'axe Y et pour colonnes l'axe X.
        # Sans cette correction, les structures sont déformées si sy != sx.
        sl = _stretch_rows(sl, sy / sx)
    elif plane == "coronal":
        sl = np.asarray(vol[:, int(np.clip(index, 0, ny - 1)), :])[::-1]
        sl = _stretch_rows(sl, sz / sx)
    else:
        sl = np.asarray(vol[:, :, int(np.clip(index, 0, nx - 1))])[::-1]
        sl = _stretch_rows(sl, sz / sy)
    g = np.clip((sl.astype(np.float32) + 200.0) / 1700.0, 0, 1)
    img = np.stack([g, g, g], axis=-1) * 255.0
    if high <= low:
        m_yel = np.zeros(sl.shape, bool)
        m_red = sl > low
    else:
        m_yel = (sl > low) & (sl <= high)
        m_red = sl > high
    img[m_yel] = 0.5 * img[m_yel] + 0.5 * np.array([255, 220, 0])
    img[m_red] = 0.5 * img[m_red] + 0.5 * np.array([255, 0, 0])
    return _png_bytes(img.astype(np.uint8))


def _stretch_rows(sl: np.ndarray, ratio: float) -> np.ndarray:
    """Corrige les proportions si l'épaisseur de coupe diffère de la taille du pixel."""
    if abs(ratio - 1.0) < 0.02:
        return sl
    n = max(1, int(round(sl.shape[0] * ratio)))
    idx = np.minimum((np.arange(n) / ratio).astype(int), sl.shape[0] - 1)
    return sl[idx]
