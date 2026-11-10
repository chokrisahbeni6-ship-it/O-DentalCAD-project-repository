"""Controles de planification (etape 6) : implants entre eux et implant <-> dent prevue.

Logique pure (numpy), dans le repere unique du plan. Les seuils sont des ALERTES de depart,
reglables par variables d'environnement : remplacez-les par ceux de votre protocole.
Ce module ne remplace pas une planification prothetique complete (pas de dent virtuelle).
"""
import math
import os

import numpy as np

from app.guide_geometry import unit

MIN_GAP_MM = float(os.getenv("PROSTH_MIN_IMPLANT_GAP_MM", "3.0"))   # valeur souvent citee entre implants
MAX_ANGLE_DEG = float(os.getenv("PROSTH_MAX_ANGLE_DEG", "15"))
MAX_OFFSET_MM = float(os.getenv("PROSTH_MAX_OFFSET_MM", "1.5"))


def segment_distance(p1, q1, p2, q2):
    """Distance minimale entre deux segments 3D [p1,q1] et [p2,q2]."""
    p1, q1, p2, q2 = (np.asarray(x, float) for x in (p1, q1, p2, q2))
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = d1 @ d1, d2 @ d2, d2 @ r
    eps = 1e-12
    if a <= eps and e <= eps:
        return float(np.linalg.norm(r))
    if a <= eps:
        s, t = 0.0, float(np.clip(f / e, 0, 1))
    else:
        c = d1 @ r
        if e <= eps:
            t, s = 0.0, float(np.clip(-c / a, 0, 1))
        else:
            b = d1 @ d2
            den = a * e - b * b
            s = float(np.clip((b * f - c * e) / den, 0, 1)) if den > eps else 0.0
            t = (b * s + f) / e
            if t < 0:
                t, s = 0.0, float(np.clip(-c / a, 0, 1))
            elif t > 1:
                t, s = 1.0, float(np.clip((b - c) / a, 0, 1))
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))


def implant_segment(imp):
    """Segment axe de l'implant : de la plateforme (position) vers l'apex, sur la longueur."""
    pos = np.asarray(imp["position"], float)
    a = unit(imp.get("axis") or (0.0, 0.0, -1.0))
    return pos, pos + a * float(imp["length"]), a


def plan_report(plan, min_gap=None, max_angle=None, max_offset=None):
    min_gap = MIN_GAP_MM if min_gap is None else min_gap
    max_angle = MAX_ANGLE_DEG if max_angle is None else max_angle
    max_offset = MAX_OFFSET_MM if max_offset is None else max_offset
    blocking, warnings, pairs, prosth = [], [], [], []
    segs = [implant_segment(p) for p in plan]

    for i in range(len(plan)):
        for j in range(i + 1, len(plan)):
            gap = (segment_distance(segs[i][0], segs[i][1], segs[j][0], segs[j][1])
                   - plan[i]["diameter"] / 2 - plan[j]["diameter"] / 2)
            pairs.append({"a": i + 1, "b": j + 1, "surface_gap_mm": round(gap, 2)})
            if gap < 0:
                blocking.append(f"Implants {i + 1} et {j + 1} : les corps se chevauchent "
                                f"({-gap:.2f} mm d'interpenetration)")
            elif gap < min_gap:
                warnings.append(f"Implants {i + 1} et {j + 1} : {gap:.2f} mm entre les surfaces "
                                f"(alerte sous {min_gap:g} mm)")

    for i, p in enumerate(plan, 1):
        t = p.get("tooth")
        if not t:
            continue
        pos, _apex, a = segs[i - 1]
        # A tooth entry is optional and may be incomplete while a plan is being edited.
        # Do not let missing/malformed coordinates crash the entire report.
        center = t.get("center") if isinstance(t, dict) else None
        if center is None:
            warnings.append(
                f"Implant {i} : centre de la dent prevue absent ; controle prothetique non calcule"
            )
            prosth.append({"implant": i, "tooth": t.get("fdi") if isinstance(t, dict) else None,
                           "status": "incomplete_missing_center"})
            continue
        try:
            c = np.asarray(center, dtype=float)
            if c.shape != (3,) or not np.all(np.isfinite(c)):
                raise ValueError("center must contain three finite coordinates")
        except (TypeError, ValueError):
            warnings.append(
                f"Implant {i} : centre de la dent prevue invalide ; controle prothetique non calcule"
            )
            prosth.append({"implant": i, "tooth": t.get("fdi") if isinstance(t, dict) else None,
                           "status": "invalid_center"})
            continue
        offset = float(np.linalg.norm(np.cross(c - pos, a)))
        row = {"implant": i, "tooth": t.get("fdi"), "offset_mm": round(offset, 2),
               "plateform_to_tooth_center_mm": round(float(-(c - pos) @ a), 2)}
        if offset > max_offset:
            warnings.append(f"Implant {i} : l'axe passe a {offset:.2f} mm du centre de la dent "
                            f"{t.get('fdi') or ''} prevue (alerte au-dela de {max_offset:g} mm)")
        if t.get("axis"):
            ang = math.degrees(math.acos(min(1.0, abs(float(a @ unit(t["axis"]))))))
            row["angle_deg"] = round(ang, 1)
            if ang > max_angle:
                warnings.append(f"Implant {i} : {ang:.1f} deg d'ecart avec l'axe de la dent "
                                f"{t.get('fdi') or ''} prevue (alerte au-dela de {max_angle:g} deg)")
        prosth.append(row)

    return {"blocking": blocking, "warnings": warnings, "pairs": pairs, "prosthetic": prosth,
            "thresholds": {"min_implant_gap_mm": min_gap, "max_angle_deg": max_angle,
                           "max_offset_mm": max_offset},
            "convention": "position = centre de la plateforme ; l'implant s'etend de la vers l'apex "
                          "(direction axis) sur sa longueur",
            "note": "Alertes indicatives dans le repere du plan ; ne remplacent pas votre protocole."}
