"""Calculs geometriques du guide (numpy seulement, testables sans maillage)."""
import math

import numpy as np

SECTIONS = 48        # nombre de cotes des cylindres de coupe (trimesh.creation.cylinder)


def unit(axis):
    a = np.asarray(axis, dtype=float)
    return a / np.linalg.norm(a)


def tilt_deg(axis):
    return math.degrees(math.acos(min(1.0, abs(float(unit(axis)[2])))))


def center_xy(pos, axis, z):
    """Point (x, y) ou l'axe de l'implant traverse le plan horizontal d'altitude z."""
    a = unit(axis)
    if abs(a[2]) < 1e-6:
        raise ValueError("axe horizontal")
    p = np.asarray(pos, dtype=float)
    return p[:2] + a[:2] / a[2] * (z - p[2])


def rot_z_to(u):
    """Matrice de rotation 3x3 envoyant l'axe +Z sur le vecteur unitaire u."""
    u = unit(u)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(z, u)
    c = float(z @ u)
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * (1.0 / (1.0 + c))


def hole_halfwidth(r, axis):
    """Demi-largeur horizontale (conservative) d'un trou incline : r / cos(inclinaison)."""
    return r / math.cos(math.radians(tilt_deg(axis)))


def min_wall(imps, z_bottom, z_top):
    """Paroi minimale entre trous voisins sur toute l'epaisseur de la plaque.
    imps : liste de (pos, axis, rayon). Retourne +inf s'il n'y a qu'un implant."""
    best = math.inf
    for i in range(len(imps)):
        for j in range(i + 1, len(imps)):
            (pa, aa, ra), (pb, ab, rb) = imps[i], imps[j]
            d0 = center_xy(pa, aa, z_bottom) - center_xy(pb, ab, z_bottom)
            d1 = center_xy(pa, aa, z_top) - center_xy(pb, ab, z_top)
            dv = d1 - d0
            s = 0.0 if float(dv @ dv) < 1e-18 else float(np.clip(-(d0 @ dv) / (dv @ dv), 0, 1))
            dmin = float(np.linalg.norm(d0 + s * dv))
            best = min(best, dmin - hole_halfwidth(ra, aa) - hole_halfwidth(rb, ab))
    return best


def edge_clearance(imps, z_bottom, z_top, lo, hi):
    """Distance minimale entre un trou et le bord de la plaque (emprise lo..hi en xy)."""
    best = math.inf
    for pos, axis, r in imps:
        hw = hole_halfwidth(r, axis)
        for z in (z_bottom, z_top):
            c = center_xy(pos, axis, z)
            best = min(best, float(np.min(c - hw - lo)), float(np.min(hi - (c + hw))))
    return best


def polygon_area(r, n=SECTIONS):
    return 0.5 * n * r * r * math.sin(2 * math.pi / n)


def expected_volume(plate_volume, imps, thickness):
    """Volume theorique du guide : plaque moins chaque trou (prisme incline traversant la plaque)."""
    v = plate_volume
    for _pos, axis, r in imps:
        cos_t = math.cos(math.radians(tilt_deg(axis)))
        v -= polygon_area(r) * thickness / cos_t
    return v
