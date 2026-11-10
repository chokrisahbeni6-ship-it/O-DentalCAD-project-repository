"""Stress matrix using DentalCAD production _kabsch/_icp; synthetic only."""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
import numpy as np
from scipy.spatial import cKDTree
from app.registration_math import _icp

SEED = 20261018

def rot_error_deg(R, Rt):
    return float(np.degrees(np.arccos(np.clip((np.trace(R @ Rt.T)-1)/2, -1, 1))))

def main():
    rng=np.random.default_rng(SEED)
    src=rng.uniform([-22,-13,-8],[18,16,11],size=(1200,3))
    ax,ay,az=np.radians([7.0,-4.0,11.0])
    Rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    Ry=np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]])
    Rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    Rt=Rz@Ry@Rx; tt=np.array([3.2,-1.7,4.1]); exact=src@Rt.T+tt
    rows=[]
    for sigma in [0.0,0.03,0.10]:
      for outlier_fraction in [0.0,0.15,0.30]:
        local=np.random.default_rng(SEED+int(sigma*1000)+int(outlier_fraction*100))
        noisy=exact+local.normal(0,sigma,exact.shape)
        nout=int(len(src)*outlier_fraction)
        outliers=local.uniform([-80,-80,-80],[80,80,80],size=(nout,3)) if nout else np.empty((0,3))
        tgt=np.vstack([noisy,outliers]); tree=cKDTree(tgt)
        # centroid initialization, as in the production benchmark
        R0=np.eye(3); t0=tgt[:len(src)].mean(0)-src.mean(0)
        trim=max(0.7,1.0-outlier_fraction-0.05)
        Re,te,_=_icp(src,tree,tgt,R0,t0,iters=150,trim=trim,tol=1e-8)
        pred=src@Re.T+te; tre=np.linalg.norm(pred-exact,axis=1)
        row={'noise_sigma_mm':sigma,'outlier_fraction':outlier_fraction,'n_outliers':nout,'trim':trim,
             'translation_error_mm':float(np.linalg.norm(te-tt)), 'rotation_error_deg':rot_error_deg(Re,Rt),
             'TRE_mean_mm':float(tre.mean()),'TRE_p95_mm':float(np.percentile(tre,95)),
             'TRE_max_mm':float(tre.max()),'det_rotation':float(np.linalg.det(Re)),
             'passed_numerical_limits':bool(np.linalg.norm(te-tt)<0.15 and rot_error_deg(Re,Rt)<0.2 and np.percentile(tre,95)<0.15)}
        rows.append(row)
    result={'test':'DentalCAD production _icp/_kabsch stress matrix','seed':SEED,'points_source':len(src),
            'criteria':{'translation_error_mm_lt':0.15,'rotation_error_deg_lt':0.2,'TRE_p95_mm_lt':0.15},
            'cases':rows,'passed_cases':sum(r['passed_numerical_limits'] for r in rows),'total_cases':len(rows),
            'limitations':['Synthetic point clouds only; no DICOM image registration.','Does not call full register_points because SimpleITK is unavailable in this runtime.','Thresholds are engineering test criteria for this benchmark, not clinical acceptance criteria.']}
    out=Path(__file__).with_name('benchmark_registration_matrix_results.json')
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
