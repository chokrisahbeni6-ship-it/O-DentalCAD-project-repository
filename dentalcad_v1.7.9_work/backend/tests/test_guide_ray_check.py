import numpy as np
import pytest

from app.guide_generator import _verify_hole_rays


class FakeRay:
    def __init__(self, hits=0):
        self.hits = hits
        self.origins = None
        self.directions = None

    def intersects_location(self, ray_origins, ray_directions, multiple_hits):
        self.origins = ray_origins
        self.directions = ray_directions
        assert multiple_hits is True
        return np.zeros((self.hits, 3)), np.zeros(self.hits, dtype=int), np.zeros(self.hits, dtype=int)


class FakeMesh:
    def __init__(self, hits=0):
        self.ray = FakeRay(hits)


def test_hole_ray_check_accepts_clear_axis():
    mesh = FakeMesh()
    imps = [(np.array([0., 0., 0.]), np.array([0., 0., 1.]), 1.5)]
    assert _verify_hole_rays(mesh, imps, np.array([[0., 0.]]), 5., 4.) is True
    assert np.allclose(mesh.ray.directions[0], [0., 0., 1.])


def test_hole_ray_check_rejects_axis_blocked_by_mesh():
    mesh = FakeMesh(hits=1)
    imps = [(np.array([0., 0., 0.]), np.array([0., 0., 1.]), 1.5)]
    with pytest.raises(ValueError, match="ray-cast échoué"):
        _verify_hole_rays(mesh, imps, np.array([[0., 0.]]), 5., 4.)


def test_hole_ray_check_fails_closed_if_ray_backend_unavailable():
    class BrokenRay:
        def intersects_location(self, **kwargs):
            raise ImportError("missing spatial index")
    class BrokenMesh:
        ray = BrokenRay()
    imps = [(np.array([0., 0., 0.]), np.array([0., 0., 1.]), 1.5)]
    with pytest.raises(RuntimeError, match="Guide refusé par sécurité"):
        _verify_hole_rays(BrokenMesh(), imps, np.array([[0., 0.]]), 5., 4.)


def test_hole_ray_check_rejects_missing_center_instead_of_silently_skipping_implant():
    mesh = FakeMesh()
    imps = [
        (np.array([0., 0., 0.]), np.array([0., 0., 1.]), 1.5),
        (np.array([5., 0., 0.]), np.array([0., 0., 1.]), 1.5),
    ]
    with pytest.raises(ValueError, match="centre XY est requis pour chaque implant"):
        _verify_hole_rays(mesh, imps, np.array([[0., 0.]]), 5., 4.)


def test_hole_ray_check_rejects_invalid_thickness():
    mesh = FakeMesh()
    imps = [(np.array([0., 0., 0.]), np.array([0., 0., 1.]), 1.5)]
    with pytest.raises(ValueError, match="épaisseur de plaque invalide"):
        _verify_hole_rays(mesh, imps, np.array([[0., 0.]]), 5., 0.)
