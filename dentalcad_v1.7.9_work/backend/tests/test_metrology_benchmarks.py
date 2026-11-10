from research.validation.benchmark_mesh import run as run_mesh_benchmark
from research.validation.benchmark_registration import run as run_registration_benchmark


def test_synthetic_mesh_metrology_benchmark():
    result = run_mesh_benchmark()
    assert result["mesh_points"] > 1000
    assert result["centroid_error_mm"] < 0.5
    assert result["radial_absolute_error_p95_mm"] < 1.5


def test_synthetic_registration_benchmark():
    result = run_registration_benchmark()
    assert result["translation_error_mm"] < 0.15
    assert result["rotation_error_deg"] < 0.2
    assert result["TRE_p95_mm"] < 0.15
