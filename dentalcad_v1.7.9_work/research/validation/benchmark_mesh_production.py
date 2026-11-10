"""Metrology benchmark against DentalCAD's actual production STL exporter.

Requires backend dependencies (SimpleITK, VTK, NumPy). Uses a known analytic
sphere sampled on an anisotropic grid and a rotated physical direction matrix.
This validates geometric handling in a synthetic case only; it is not clinical
validation and not a substitute for a calibrated physical phantom.
Run from the project root: python research/validation/benchmark_mesh_production.py
"""
import json
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
import SimpleITK as sitk
import vtk
from vtk.util import numpy_support

from app.segmentation import _export_mask_to_stl

SEED = 20261018


def run():
    spacing = np.array([0.4, 0.5, 0.6], dtype=float)
    size_xyz = np.array([100, 90, 80], dtype=int)
    center_index = (size_xyz - 1) / 2.0
    radius_mm = 10.0
    zz, yy, xx = np.indices(tuple(size_xyz[::-1]))
    dist2 = (((xx - center_index[0]) * spacing[0]) ** 2
             + ((yy - center_index[1]) * spacing[1]) ** 2
             + ((zz - center_index[2]) * spacing[2]) ** 2)
    mask = (dist2 <= radius_mm ** 2).astype(np.uint8)

    ax, ay, az = np.radians([7.0, -11.0, 19.0])
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    direction = Rz @ Ry @ Rx
    origin = np.array([31.0, -17.0, 8.5])
    center_physical = origin + direction @ (center_index * spacing)

    ref = sitk.GetImageFromArray(mask)
    ref.SetSpacing(tuple(spacing))
    ref.SetOrigin(tuple(origin))
    ref.SetDirection(tuple(direction.ravel()))

    with tempfile.TemporaryDirectory(prefix="dentalcad_mesh_validation_") as td:
        out_path = str(Path(td) / "production_mesh.stl")
        _export_mask_to_stl(mask, ref, out_path, decimate=0.5)
        reader = vtk.vtkSTLReader()
        reader.SetFileName(out_path)
        reader.Update()
        mesh = reader.GetOutput()
        if mesh.GetNumberOfPoints() < 1000 or mesh.GetNumberOfCells() < 1000:
            raise AssertionError("Production exporter returned an unexpectedly small/empty mesh")
        pts = numpy_support.vtk_to_numpy(mesh.GetPoints().GetData()).astype(float)

    radial_error = np.linalg.norm(pts - center_physical, axis=1) - radius_mm
    metrics = {
        "benchmark": "actual DentalCAD _export_mask_to_stl production function",
        "seed": SEED,
        "reference": "analytic sphere radius 10 mm on anisotropic grid; rotated direction matrix",
        "spacing_xyz_mm": spacing.tolist(),
        "direction_determinant": float(np.linalg.det(direction)),
        "mesh_points": int(len(pts)),
        "mesh_triangles": int(mesh.GetNumberOfCells()),
        "centroid_error_mm": float(np.linalg.norm(pts.mean(axis=0) - center_physical)),
        "radial_absolute_error_mean_mm": float(np.mean(np.abs(radial_error))),
        "radial_absolute_error_p95_mm": float(np.percentile(np.abs(radial_error), 95)),
        "radial_absolute_error_max_mm": float(np.max(np.abs(radial_error))),
        "radial_signed_error_mean_mm": float(np.mean(radial_error)),
        "note": "Synthetic geometric validation of the production exporter only; not clinical validation or validation against a calibrated physical phantom.",
    }
    if metrics["centroid_error_mm"] > 0.5:
        raise AssertionError(f"Production mesh physical placement error too large: {metrics}")
    if metrics["radial_absolute_error_p95_mm"] > 1.5:
        raise AssertionError(f"Production mesh surface deviation too large: {metrics}")
    return metrics


if __name__ == "__main__":
    result = run()
    output = ROOT / "research" / "validation" / "benchmark_mesh_production_results.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
