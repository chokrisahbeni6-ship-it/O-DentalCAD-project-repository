"""Fonctions mathématiques ICP/Kabsch utilisées en production et dans le benchmark."""
import numpy as np
from scipy.spatial import cKDTree

def _kabsch(A, B):
    ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    det = float(np.linalg.det(Vt.T @ U.T))
    # det très proche de zéro peut faire np.sign(det)==0 et produire une matrice singulière.
    correction = -1.0 if det < 0.0 else 1.0
    R = Vt.T @ np.diag([1.0, 1.0, correction]) @ U.T
    return R, cb - R @ ca


def _icp(src, tree, tgt, R, t, iters, trim=0.8, tol=1e-6):
    if not 0.1 <= trim <= 1.0:
        raise ValueError("trim doit être compris entre 0.1 et 1.0")
    if len(src) < 10 or len(tgt) < 10:
        raise ValueError("ICP : au moins 10 points sont nécessaires dans chaque nuage")
    k = min(len(src), max(10, int(len(src) * trim)))
    err = np.inf
    for _ in range(iters):
        moved = src @ R.T + t
        d, nn = tree.query(moved)
        sel = np.argsort(d)[:k]
        dR, dt = _kabsch(moved[sel], tgt[nn[sel]])
        R_new, t_new = dR @ R, dR @ t + dt
        # Convergence sur les paramètres de transformation, pas sur la variation du RMS.
        rotation_delta = float(np.linalg.norm(R_new - R, ord="fro"))
        translation_delta = float(np.linalg.norm(t_new - t))
        R, t = R_new, t_new
        moved_after = src @ R.T + t
        d_after, _ = tree.query(moved_after)
        d_selected = np.partition(d_after, k - 1)[:k]
        err = float(np.sqrt(np.mean(d_selected ** 2)))
        if max(rotation_delta, translation_delta) < tol:
            break
    return R, t, err
