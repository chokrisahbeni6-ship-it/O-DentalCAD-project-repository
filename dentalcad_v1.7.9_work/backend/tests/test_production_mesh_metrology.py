"""Tests for the real production STL export path (requires SimpleITK and VTK)."""
import pytest

sitk = pytest.importorskip("SimpleITK", reason="SimpleITK is a backend dependency; install backend/requirements.txt")
pytest.importorskip("vtk", reason="VTK is a backend dependency")

from app.segmentation import _export_mask_to_stl
from research.validation.benchmark_mesh_production import run as run_production_mesh_benchmark
import numpy as np


def test_production_mesh_export_rejects_empty_mask(tmp_path):
    image = sitk.Image([16, 16, 16], sitk.sitkUInt8)
    mask = np.zeros((16, 16, 16), dtype=np.uint8)
    with pytest.raises(ValueError, match="vide"):
        _export_mask_to_stl(mask, image, str(tmp_path / "empty.stl"))


def test_production_mesh_export_rejects_mismatched_dimensions(tmp_path):
    image = sitk.Image([16, 16, 16], sitk.sitkUInt8)
    mask = np.ones((15, 16, 16), dtype=np.uint8)
    with pytest.raises(ValueError, match="incompatibles"):
        _export_mask_to_stl(mask, image, str(tmp_path / "bad.stl"))


def test_production_mesh_metrology_benchmark():
    result = run_production_mesh_benchmark()
    assert result["mesh_points"] > 1000
    assert result["centroid_error_mm"] < 0.5
    assert result["radial_absolute_error_p95_mm"] < 1.5
