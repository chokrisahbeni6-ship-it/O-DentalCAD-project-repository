"""Generateur de guide - VERSION DE TEST (plaque percee).

Ce que fait cette version : une plaque plane au-dessus de la gencive, percee de trous
qui SUIVENT l'axe de chaque implant (inclinaison jusqu'a 35 deg), avec controles
geometriques avant fabrication et controle du volume apres fabrication.

Ce qu'elle ne fait PAS : elle ne s'appuie pas sur les dents ni sur la gencive, n'a pas de
manchons de forage et n'est pas validee cliniquement. NON UTILISABLE EN BOUCHE.
"""
import numpy as np
import trimesh

from app import guide_geometry as gg

VOLUME_TOLERANCE = 0.02      # 2 % : tolérance géométrique numérique; à confirmer sur maillages représentatifs
# La déviation exacte est retournée dans le rapport et dans le message d’erreur.



def _verify_hole_rays(guide, imps, centers, z_mid, thickness):
    """Independent mesh ray check: each implant axis must pass through an open hole.

    A ray is cast along the planned axis across the whole plate. Any mesh hit means
    that the nominal hole centerline is obstructed. Requires trimesh's ray backend.
    """
    # Fail closed on malformed inputs: zip() alone would silently skip implants
    # if the center list were shorter than the plan.
    centers = np.asarray(centers, dtype=float)
    if len(imps) == 0 or centers.shape != (len(imps), 2):
        raise ValueError("Contrôle ray-cast impossible : un centre XY est requis pour chaque implant")
    if not np.isfinite(centers).all() or not np.isfinite(float(z_mid)):
        raise ValueError("Contrôle ray-cast impossible : coordonnées non finies")
    if not np.isfinite(float(thickness)) or float(thickness) <= 0:
        raise ValueError("Contrôle ray-cast impossible : épaisseur de plaque invalide")

    ray_length = float(thickness) * 2.0 + 20.0
    for idx, ((pos, axis, _radius), center_xy) in enumerate(zip(imps, centers), start=1):
        axis = np.asarray(axis, dtype=float)
        if axis.shape != (3,) or not np.isfinite(axis).all() or np.linalg.norm(axis) < 1e-12:
            raise ValueError(f"Contrôle ray-cast impossible : axe invalide (implant {idx})")
        axis = gg.unit(axis)
        if abs(float(axis[2])) < 1e-6:
            raise ValueError(f"Contrôle ray-cast impossible : axe quasi horizontal (implant {idx})")
        point = np.array([center_xy[0], center_xy[1], z_mid], dtype=float)
        origin = point - axis * ray_length
        try:
            locations, _ray_ids, _triangle_ids = guide.ray.intersects_location(
                ray_origins=np.asarray([origin]),
                ray_directions=np.asarray([axis]),
                multiple_hits=True,
            )
        except Exception as exc:
            raise RuntimeError(
                "Contrôle ray-cast indépendant indisponible : installez les dépendances "
                "de ray casting du backend. Guide refusé par sécurité."
            ) from exc
        if len(locations):
            raise ValueError(
                f"Contrôle ray-cast échoué pour l'implant {idx} : l'axe traverse le maillage "
                "du guide au lieu de passer librement par le trou. Guide refusé."
            )
    return True


def generate_guide(gum_path, implants, params, out_path):
    gum = trimesh.load(gum_path, force="mesh")
    if len(gum.vertices) == 0:
        raise ValueError("Le scan de gencive est vide")
    if not implants:
        raise ValueError("Aucun implant dans le plan")

    pos = [np.array(i.position, dtype=float) for i in implants]
    axes = [gg.unit(i.axis) for i in implants]
    radii = [(i.diameter + params.clearance_mm) / 2 for i in implants]
    imps = list(zip(pos, axes, radii))

    v = gum.vertices
    near = np.zeros(len(v), dtype=bool)
    for p in pos:
        near |= np.linalg.norm(v[:, :2] - p[:2], axis=1) <= 10.0
    top = float(v[near, 2].max()) if near.any() else float(max(p[2] for p in pos))
    t = params.plate_thickness_mm
    z_bot = top + params.air_gap_mm
    z_top, z_mid = z_bot + t, z_bot + t / 2

    # --- controles AVANT de fabriquer quoi que ce soit ---
    wall = gg.min_wall(imps, z_bot, z_top)
    if wall < params.min_wall_mm:
        raise ValueError(f"Implants trop proches : paroi de {wall:.2f} mm entre deux trous "
                         f"(minimum {params.min_wall_mm} mm)")
    centers = np.array([gg.center_xy(p, a, z_mid) for p, a, _ in imps])
    lo, hi = centers.min(0) - params.margin_mm, centers.max(0) + params.margin_mm
    edge = gg.edge_clearance(imps, z_bot, z_top, lo, hi)
    if edge < params.min_wall_mm:
        raise ValueError(f"Trou trop pres du bord de la plaque ({edge:.2f} mm) : augmentez la marge")

    plate = trimesh.creation.box(extents=[hi[0] - lo[0], hi[1] - lo[1], t])
    plate.apply_translation([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, z_mid])
    plate_volume = float(plate.volume)

    guide = plate
    for (p, a, r), c_xy in zip(imps, centers):          # un trou a la fois
        cutter = trimesh.creation.cylinder(radius=float(r), height=t * 3, sections=gg.SECTIONS)
        T = np.eye(4)
        T[:3, :3] = gg.rot_z_to(a)
        T[:3, 3] = [c_xy[0], c_xy[1], z_mid]
        cutter.apply_transform(T)
        guide = trimesh.boolean.difference([guide, cutter], engine="manifold")

    if len(guide.faces) == 0 or guide.volume <= 0:
        raise ValueError("Generation echouee (volume nul)")
    watertight = bool(guide.is_watertight)
    if not watertight:
        raise ValueError("Le guide genere n'est pas un volume ferme")

    # Independent geometric check in addition to expected-volume comparison.
    ray_cast_ok = _verify_hole_rays(guide, imps, centers, z_mid, t)

    expected = gg.expected_volume(plate_volume, imps, t)
    deviation = abs(float(guide.volume) - expected) / expected
    if deviation > VOLUME_TOLERANCE:
        raise ValueError(f"Controle de volume echoue : {guide.volume:.1f} mm3 obtenus pour "
                         f"{expected:.1f} mm3 attendus (ecart {deviation * 100:.2f} %). "
                         "Les trous ne sont pas ceux du plan : guide refuse.")

    guide.export(out_path)
    return {
        "volume_mm3": float(guide.volume),
        "validation": {
            "ok": True,
            "implants": len(implants),
            "min_wall_between_holes_mm": None if wall == float("inf") else round(float(wall), 2),
            "min_edge_wall_mm": round(float(edge), 2),
            "max_tilt_deg": round(max(gg.tilt_deg(a) for a in axes), 1),
            "expected_volume_mm3": round(expected, 2),
            "volume_deviation_pct": round(deviation * 100, 4),
            "watertight": watertight,
            "independent_hole_ray_cast": ray_cast_ok,
            "type": "GUIDE DE TEST - NON UTILISABLE EN BOUCHE",
        },
    }
