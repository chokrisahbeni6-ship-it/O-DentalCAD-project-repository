"""Bibliotheque d'implants : liste ce qui est AUTORISE dans un plan.

Aucune dimension de fabricant n'est fournie avec le logiciel. Le praticien (ou son
fournisseur) la remplit depuis les catalogues officiels : voir implants.json.
"""
import json
import os

_PATH = os.getenv("IMPLANT_LIBRARY", os.path.join(os.path.dirname(__file__), "implants.json"))
_cache = {}


def load_library(path=None):
    path = path or _PATH
    if path in _cache:
        return _cache[path]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        lib = {}
        for s in data["systems"]:
            for k in ("id", "name", "verified", "source", "diameters_mm", "lengths_mm"):
                if k not in s:
                    raise KeyError(f"{s.get('id', '?')} : champ '{k}' manquant")
            if not s["diameters_mm"] or not s["lengths_mm"]:
                raise KeyError(f"{s['id']} : listes de tailles vides")
            lib[str(s["id"])] = s
        if not lib:
            raise KeyError("aucun systeme")
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Bibliotheque d'implants illisible : {e}")
    _cache[path] = lib
    return lib


def check_implant(lib, system_id, diameter, length):
    """Retourne la fiche du systeme ou leve ValueError avec un message clair."""
    ids = ", ".join(sorted(lib))
    if not system_id:
        raise ValueError(f"systeme d'implant obligatoire (disponibles : {ids})")
    s = lib.get(system_id)
    if s is None:
        raise ValueError(f"systeme « {system_id} » absent de la bibliotheque (disponibles : {ids})")
    if not any(abs(diameter - x) < 0.01 for x in s["diameters_mm"]):
        raise ValueError(f"diametre {diameter} mm non prevu pour {system_id} "
                         f"(disponibles : {s['diameters_mm']})")
    if not any(abs(length - x) < 0.01 for x in s["lengths_mm"]):
        raise ValueError(f"longueur {length} mm non prevue pour {system_id} "
                         f"(disponibles : {s['lengths_mm']})")
    combos = s.get("combinations")
    if combos and not any(abs(diameter - c[0]) < 0.01 and abs(length - c[1]) < 0.01 for c in combos):
        raise ValueError(f"combinaison {diameter} x {length} mm inexistante pour {system_id}")
    return s


def public_view(lib):
    return [{"id": s["id"], "name": s["name"], "manufacturer": s.get("manufacturer", ""),
             "verified": bool(s["verified"]), "source": s["source"],
             "diameters_mm": s["diameters_mm"], "lengths_mm": s["lengths_mm"]}
            for s in lib.values()]
