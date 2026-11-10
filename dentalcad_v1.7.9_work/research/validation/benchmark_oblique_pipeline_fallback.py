"""Fallback end-to-end synthetic geometry test when SimpleITK/pydicom are unavailable.
Uses NumPy/SciPy/VTK/skimage and DentalCAD production _icp/_kabsch math.
It does NOT exercise DICOM parsing, SimpleITK resampling, or production _export_mask_to_stl.
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.registration_math import _icp
SEED=20261018

def rotations():
    ax,ay,az=np.radians([13.,-9.,21.])
    Rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    Ry=np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]])
    Rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    return Rz@Ry@Rx

def main():
    spacing=np.array([0.45,0.55,0.70]); size=np.array([80,76,64]); origin=np.array([24.,-31.,12.]); D=rotations()
    # Synthetic asymmetric anatomy phantom in index coordinates; intensities are deterministic.
    z,y,x=np.indices((size[2],size[1],size[0]),dtype=float)
    xyz=np.stack([x,y,z],axis=0)
    ctr=(size-1)/2
    # asymmetric union of ellipsoids ensures orientation/rotation is constrained
    f1=((x-ctr[0])/20)**2+((y-ctr[1])/15)**2+((z-ctr[2])/12)**2
    f2=((x-(ctr[0]+10))/7)**2+((y-(ctr[1]-6))/5)**2+((z-(ctr[2]+5))/8)**2
    mask=(f1<=1.0)|(f2<=1.0)
    # LPS physical coordinates: p = origin + D @ (index * spacing)
    ijk=np.column_stack(np.where(mask))[:,::-1].astype(float)
    physical=origin+(ijk*spacing)@D.T
    # Oblique resampling into axis-aligned physical grid, via inverse physical mapping.
    corners=np.array([[i,j,k] for i in [0,size[0]-1] for j in [0,size[1]-1] for k in [0,size[2]-1]],float)
    cphys=origin+(corners*spacing)@D.T
    out_origin=cphys.min(0)-spacing*2
    out_spacing=np.array([0.5,0.5,0.5]); out_size=np.ceil((cphys.max(0)-out_origin)/out_spacing).astype(int)+3
    oz,oy,ox=np.indices((out_size[2],out_size[1],out_size[0]),dtype=float)
    out_phys=out_origin[:,None,None,None]+np.stack([ox*out_spacing[0],oy*out_spacing[1],oz*out_spacing[2]],axis=0)
    flat=out_phys.reshape(3,-1).T
    idx=((flat-origin)@D)/spacing
    sampled=map_coordinates(mask.astype(np.float32),[idx[:,2],idx[:,1],idx[:,0]],order=1,mode='constant',cval=0).reshape((out_size[2],out_size[1],out_size[0]))
    out_mask=sampled>=0.5
    # Actual VTK marching-cubes extraction on the resampled mask, then transform to LPS physical mm.
    v=vtk.vtkImageData(); v.SetDimensions(*out_size.tolist()); v.SetSpacing(*out_spacing.tolist()); v.SetOrigin(*out_origin.tolist())
    scal=numpy_to_vtk(np.ascontiguousarray(out_mask.astype(np.uint8).ravel(order='C')),deep=True); v.GetPointData().SetScalars(scal)
    mc=vtk.vtkMarchingCubes(); mc.SetInputData(v); mc.SetValue(0,0.5); mc.Update()
    poly=mc.GetOutput(); pts=vtk_to_numpy(poly.GetPoints().GetData()).astype(float)
    if len(pts)<100: raise AssertionError('Surface extraction produced too few points')
    # transform is already physical because vtk image origin/spacing are in LPS mm
    # Create a known transformed source cloud and recover inverse transform via production ICP.
    rng=np.random.default_rng(SEED); choose=rng.choice(len(pts),min(5000,len(pts)),replace=False); tgt=pts[choose]
    ax,ay,az=np.radians([-5.,8.,-12.]); Rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    Ry=np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]])
    Rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    Rt=Rz@Ry@Rx; tt=np.array([2.4,-1.3,3.1]); src=(tgt-tt)@Rt # so src @ Rt.T + tt = tgt
    tree=cKDTree(tgt); da=np.radians(0.5); Rp=np.array([[np.cos(da),-np.sin(da),0],[np.sin(da),np.cos(da),0],[0,0,1]])
    R0=Rp@Rt; t0=tt+np.array([0.08,-0.06,0.05])
    Re,te,_=_icp(src,tree,tgt,R0,t0,iters=120,trim=0.9,tol=1e-8)
    pred=src@Re.T+te; d=np.linalg.norm(pred-tgt,axis=1)
    # Surface deviation against the source phantom's voxel-boundary point cloud (approximate reference).
    src_boundary=mask & ~__import__('scipy').ndimage.binary_erosion(mask)
    bidx=np.column_stack(np.where(src_boundary))[:,::-1].astype(float)
    bphys=origin+(bidx*spacing)@D.T
    # query a deterministic subset to keep the test lightweight
    qpts=pts[rng.choice(len(pts),min(3000,len(pts)),replace=False)]
    bd,_=cKDTree(bphys).query(qpts)
    # coordinate resampling error measured on all foreground source points using nearest voxel in resampled grid
    nearest=np.rint((physical-out_origin)/out_spacing).astype(int)
    inside=((nearest>=0)&(nearest<out_size)).all(axis=1)
    # evaluate physical displacement for points whose nearest resampled voxel is foreground
    inds=nearest[inside]; fg=out_mask[inds[:,2],inds[:,1],inds[:,0]]
    coverage=float(fg.mean()) if len(fg) else 0.0
    metrics={
      'test':'fallback oblique phantom -> scipy resampling -> VTK marching cubes -> production ICP math',
      'seed':SEED,'source_grid_size_xyz':size.tolist(),'source_spacing_mm':spacing.tolist(),'source_direction_det':float(np.linalg.det(D)),
      'resampled_grid_size_xyz':out_size.tolist(),'resampled_spacing_mm':out_spacing.tolist(),'source_foreground_voxels':int(mask.sum()),'resampled_foreground_voxels':int(out_mask.sum()),
      'mesh_points':int(len(pts)),'mesh_triangles':int(poly.GetNumberOfCells()),'surface_to_source_boundary_nearest_mean_mm':float(bd.mean()),'surface_to_source_boundary_nearest_p95_mm':float(np.percentile(bd,95)),'surface_to_source_boundary_nearest_max_mm':float(bd.max()),'source_foreground_nearest_voxel_coverage':coverage,
      'registration_translation_error_mm':float(np.linalg.norm(te-tt)),
      'registration_rotation_error_deg':float(np.degrees(np.arccos(np.clip((np.trace(Re@Rt.T)-1)/2,-1,1)))),
      'registration_tre_mean_mm':float(d.mean()),'registration_tre_p95_mm':float(np.percentile(d,95)),'registration_tre_max_mm':float(d.max()),
      'limits':{'translation_error_mm_lt':0.2,'rotation_error_deg_lt':0.5,'tre_p95_mm_lt':0.3,'coverage_gt':0.9},
      'pass':bool(np.linalg.norm(te-tt)<0.2 and np.degrees(np.arccos(np.clip((np.trace(Re@Rt.T)-1)/2,-1,1)))<0.5 and np.percentile(d,95)<0.3 and coverage>0.9),
      'limitations':['This is a fallback synthetic geometry test, not a DICOM file round-trip.','Uses SciPy interpolation, not SimpleITK Resample.','Uses VTK marching cubes directly, not DentalCAD _export_mask_to_stl.','ICP uses DentalCAD production _icp/_kabsch but bypasses production register_points, which imports SimpleITK.','No clinical validity is implied.']}
    out=ROOT/'research/validation/benchmark_oblique_pipeline_fallback_results_R10.json'; out.write_text(json.dumps(metrics,indent=2)); print(json.dumps(metrics,indent=2))
    if not metrics['pass']: raise SystemExit('FAIL: synthetic fallback criteria')
if __name__=='__main__': main()
