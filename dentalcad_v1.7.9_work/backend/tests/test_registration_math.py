import numpy as np
import pytest
from app.plan_tools import _norm_axis
from app.registration_math import _kabsch


def test_norm_axis_normalizes_downward_axis():
    axis = _norm_axis([0.2, 0.0, -1.0], 1)
    assert len(axis) == 3
    assert np.linalg.norm(axis) == pytest.approx(1.0, abs=1e-4)
    assert axis[2] < 0


@pytest.mark.parametrize("axis", [[0, 0, 0], [0, 0, 1], [1, 0, 0], [float("nan"), 0, -1], [1, 2]])
def test_norm_axis_rejects_invalid_or_upward_axes(axis):
    with pytest.raises(ValueError):
        _norm_axis(axis, 1)


def test_kabsch_returns_proper_rotation():
    rng = np.random.default_rng(123)
    A = rng.normal(size=(100, 3))
    theta = 0.2
    R = np.array([[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])
    t = np.array([1.0, -2.0, 0.5])
    B = A @ R.T + t
    Re, te = _kabsch(A, B)
    assert np.linalg.det(Re) == pytest.approx(1.0, abs=1e-8)
    assert np.allclose(Re, R, atol=1e-8)
    assert np.allclose(te, t, atol=1e-8)
