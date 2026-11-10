"""Banc d'essai synthétique indépendant pour le recalage rigide 3D.
Il valide les métriques sur des données connues, pas l'intégration complète DentalCAD.
Exécution : python benchmark_registration.py
"""
import json
import os
import sys
from pathlib import Path
# Allow direct execution from research/validation as documented.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
import numpy as np
from scipy.spatial import cKDTree
from app.registration_math import _kabsch, _icp

SEED = 20261017

def production_kabsch(A, B):
    return _kabsch(A, B)


def production_icp(src, tgt, R, t, iters=150, trim=0.8, tol=1e-8):
    tree = cKDTree(tgt)
    return _icp(src, tree, tgt, R, t, iters=iters, trim=trim, tol=tol)

def angle_error(R_est, R_true):
    R_delta = R_est @ R_true.T
    return float(np.degrees(np.arccos(np.clip((np.trace(R_delta)-1)/2,-1,1))))

def run():
    rng=np.random.default_rng(SEED)
    # Asymmetric point cloud prevents trivial symmetry from dominating the test.
    src=rng.uniform([-22,-13,-8],[18,16,11],size=(1200,3))
    ax=np.radians(7.0); ay=np.radians(-4.0); az=np.radians(11.0)
    Rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    Ry=np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]])
    Rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    R_true=Rz@Ry@Rx
    t_true=np.array([3.2,-1.7,4.1])
    tgt=src@R_true.T+t_true
    # Small noise represents measurement perturbation; truth remains available.
    tgt_noisy=tgt+rng.normal(0,0.03,tgt.shape)
    # Ajoute 15 % de points aberrants à la cible; trim=0.8 doit les écarter.
    outliers=rng.uniform([-80,-80,-80],[80,80,80],size=(180,3))
    tgt_test=np.vstack([tgt_noisy,outliers])
    R0=np.eye(3); t0=tgt_noisy.mean(0)-src.mean(0)
    R_est,t_est,_=production_icp(src,tgt_test,R0,t0,trim=0.8)
    pred=src@R_est.T+t_est
    tre=np.linalg.norm(pred-(src@R_true.T+t_true),axis=1)
    metrics={
      "seed":SEED,
      "scenario":"asymmetric cloud; known rigid transform; Gaussian target noise sigma=0.03 mm; 180 uniform target outliers; production ICP trim=0.8",
      "n_points_source":len(src),
      "n_points_target_including_outliers":len(tgt_test),
      "target_outliers":len(outliers),
      "trim":0.8,
      "translation_error_mm":float(np.linalg.norm(t_est-t_true)),
      "rotation_error_deg":angle_error(R_est,R_true),
      "TRE_mean_mm":float(np.mean(tre)),
      "TRE_p95_mm":float(np.percentile(tre,95)),
      "TRE_max_mm":float(np.max(tre)),
      "rotation_determinant":float(np.linalg.det(R_est)),
      "orthogonality_frobenius_error":float(np.linalg.norm(R_est.T@R_est-np.eye(3))),
      "note":"Utilise _kabsch/_icp de production; scénario synthétique uniquement, ne démontre pas la précision clinique."
    }
    assert metrics["translation_error_mm"] < 0.15, metrics
    assert metrics["rotation_error_deg"] < 0.2, metrics
    assert metrics["TRE_p95_mm"] < 0.15, metrics
    assert abs(metrics["rotation_determinant"]-1.0) < 1e-6, metrics
    assert metrics["orthogonality_frobenius_error"] < 1e-6, metrics
    return metrics

if __name__=="__main__":
    result=run()
    print(json.dumps(result,indent=2))
    with open("benchmark_registration_results.json","w",encoding="utf-8") as f:
        json.dump(result,f,indent=2)
