"""Test métrologique synthétique APPROXIMATIF du pipeline de maillage DentalCAD.

Le test reproduit la chaîne géométrique (lissage Gaussien, Marching Cubes,
transformation voxel->LPS, lissage de surface, décimation), mais utilise SciPy
pour le lissage volumique et n'appelle pas directement la fonction de production
car SimpleITK n'est pas installé dans l'environnement de validation courant.
Il compare le résultat à une sphère analytique connue. Ce n'est ni une validation
exacte du code de production ni une validation sur fantôme CBCT étalonné.
Exécution : python research/validation/benchmark_mesh.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
import vtk
from vtk.util import numpy_support

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261018


def build_mesh(mask_zyx, spacing_xyz, origin_xyz, direction, decimate=0.5):
    # Production-equivalent: gaussian smoothing in physical units, then VTK MC.
    spacing_xyz = np.asarray(spacing_xyz, dtype=float)
    sigma_vox_zyx = (1.0 / spacing_xyz[2], 1.0 / spacing_xyz[1], 1.0 / spacing_xyz[0])
    smooth = gaussian_filter(mask_zyx.astype(np.float32), sigma=sigma_vox_zyx)
    vtk_img = vtk.vtkImageData()
    vtk_img.SetDimensions(*smooth.shape[::-1])
    vtk_img.SetSpacing(1.0, 1.0, 1.0)
    vtk_img.SetOrigin(0.0, 0.0, 0.0)
    vtk_img.GetPointData().SetScalars(numpy_support.numpy_to_vtk(np.ascontiguousarray(smooth).ravel(order="C"), deep=True))
    mc = vtk.vtkMarchingCubes()
    mc.SetInputData(vtk_img)
    mc.SetValue(0, 0.5)
    mc.ComputeNormalsOff()
    mc.Update()

    M = np.eye(4)
    M[:3, :3] = np.asarray(direction).reshape(3, 3) @ np.diag(spacing_xyz)
    M[:3, 3] = np.asarray(origin_xyz)
    vm = vtk.vtkMatrix4x4()
    for i in range(4):
        for j in range(4):
            vm.SetElement(i, j, float(M[i, j]))
    transform = vtk.vtkTransform()
    transform.SetMatrix(vm)
    tf = vtk.vtkTransformPolyDataFilter()
    tf.SetInputConnection(mc.GetOutputPort())
    tf.SetTransform(transform)
    tf.Update()
    port = tf.GetOutputPort()
    if np.linalg.det(M[:3, :3]) < 0:
        reverse = vtk.vtkReverseSense()
        reverse.SetInputConnection(port)
        reverse.ReverseCellsOn()
        reverse.ReverseNormalsOn()
        reverse.Update()
        port = reverse.GetOutputPort()
    smoother = vtk.vtkWindowedSincPolyDataFilter()
    smoother.SetInputConnection(port)
    smoother.SetNumberOfIterations(15)
    smoother.Update()
    dec = vtk.vtkQuadricDecimation()
    dec.SetInputConnection(smoother.GetOutputPort())
    dec.SetTargetReduction(decimate)
    dec.Update()
    out = vtk.vtkPolyData()
    out.DeepCopy(dec.GetOutput())
    return out


def run():
    rng = np.random.default_rng(SEED)
    spacing = np.array([0.4, 0.5, 0.6])
    shape_xyz = np.array([100, 90, 80])
    center_index_xyz = (shape_xyz - 1) / 2
    radius_mm = 10.0
    zz, yy, xx = np.indices(shape_xyz[::-1])
    dx = (xx - center_index_xyz[0]) * spacing[0]
    dy = (yy - center_index_xyz[1]) * spacing[1]
    dz = (zz - center_index_xyz[2]) * spacing[2]
    mask = (dx * dx + dy * dy + dz * dz) <= radius_mm ** 2

    # Non-identity direction tests that physical transform is applied, not just spacing.
    ax, ay, az = np.radians([7.0, -11.0, 19.0])
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    direction = Rz @ Ry @ Rx
    origin = np.array([31.0, -17.0, 8.5])
    center_physical = origin + direction @ (center_index_xyz * spacing)

    mesh = build_mesh(mask, spacing, origin, direction, decimate=0.5)
    pts = numpy_support.vtk_to_numpy(mesh.GetPoints().GetData()).astype(float)
    radial_error = np.linalg.norm(pts - center_physical, axis=1) - radius_mm
    bounds = np.array(mesh.GetBounds()).reshape(3, 2)
    # Compare oriented mesh centroid with the expected center and principal-axis extents.
    centroid_error = float(np.linalg.norm(pts.mean(axis=0) - center_physical))
    metrics = {
        "seed": SEED,
        "reference": "analytic sphere radius 10 mm sampled on anisotropic 0.4x0.5x0.6 mm grid",
        "mesh_points": int(mesh.GetNumberOfPoints()),
        "mesh_triangles": int(mesh.GetNumberOfCells()),
        "spacing_xyz_mm": spacing.tolist(),
        "direction_matrix_determinant": float(np.linalg.det(direction)),
        "centroid_error_mm": centroid_error,
        "radial_absolute_error_mean_mm": float(np.mean(np.abs(radial_error))),
        "radial_absolute_error_p95_mm": float(np.percentile(np.abs(radial_error), 95)),
        "radial_absolute_error_max_mm": float(np.max(np.abs(radial_error))),
        "radial_signed_error_mean_mm": float(np.mean(radial_error)),
        "physical_bounds_mm": bounds.tolist(),
        "note": "Approximate synthetic pipeline test (SciPy smoothing; production exporter not directly executed because SimpleITK is unavailable). Not clinical validation. Voxelization and 1-mm smoothing contribute to error.",
    }
    if mesh.GetNumberOfPoints() < 1000 or not np.isfinite(pts).all():
        raise AssertionError(f"Invalid mesh output: {metrics}")
    if centroid_error > 0.5:
        raise AssertionError(f"Mesh physical placement error too large: {metrics}")
    if metrics["radial_absolute_error_p95_mm"] > 1.5:
        raise AssertionError(f"Mesh surface deviation too large for this synthetic case: {metrics}")
    return metrics


if __name__ == "__main__":
    result = run()
    out = ROOT / "research" / "validation" / "benchmark_mesh_results.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
