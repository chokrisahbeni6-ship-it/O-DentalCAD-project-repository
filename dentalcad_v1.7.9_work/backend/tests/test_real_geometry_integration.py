"""Integration checks using actual geometry libraries (not mocks).

These tests are intentionally skipped when production extras are unavailable.
They validate geometric mechanics, not clinical suitability of a guide.
"""
import numpy as np
import pytest
import trimesh

from app.guide_generator import _verify_hole_rays


def _square_ring_plate_mesh():
    """Watertight square plate with a square through-hole, spanning z=[-2, 2]."""
    # Each ring has four vertices; corresponding top/bottom rings are joined.
    outer = [(-5, -5), (5, -5), (5, 5), (-5, 5)]
    inner = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    verts = []
    for z in (-2.0, 2.0):
        verts.extend([(x, y, z) for x, y in outer])
        verts.extend([(x, y, z) for x, y in inner])
    faces = []
    # top and bottom annular surfaces
    for i in range(4):
        j = (i + 1) % 4
        # vertex ids: outer bottom 0..3, inner bottom 4..7,
        # outer top 8..11, inner top 12..15
        faces += [[8+i, 8+j, 12+j], [8+i, 12+j, 12+i]]
        faces += [[i, 4+j, j], [i, 4+i, 4+j]]
        # outer wall and inner wall
        faces += [[i, j, 8+j], [i, 8+j, 8+i]]
        faces += [[4+i, 12+j, 4+j], [4+i, 12+i, 12+j]]
    mesh = trimesh.Trimesh(vertices=np.asarray(verts), faces=np.asarray(faces), process=True)
    return mesh


def test_real_trimesh_ray_engine_clear_hole_and_blocked_axis():
    pytest.importorskip("rtree", reason="install backend/requirements.txt for the production ray index")
    mesh = _square_ring_plate_mesh()
    assert mesh.is_watertight
    implants = [(np.zeros(3), np.array([0., 0., 1.]), 1.0)]
    assert _verify_hole_rays(mesh, implants, np.array([[0., 0.]]), 0.0, 4.0)
    # An off-centre ray crosses the plate material and must be rejected.
    with pytest.raises(ValueError, match="ray-cast échoué"):
        _verify_hole_rays(mesh, implants, np.array([[3., 0.]]), 0.0, 4.0)


def test_simpleitk_oblique_image_resampling_has_patient_axis_direction_and_bounds():
    sitk = pytest.importorskip("SimpleITK", reason="install backend/requirements.txt for production DICOM tests")
    from app.viewer import _resample_to_patient_lps

    # Synthetic image with an oblique direction matrix. This is a controlled
    # integration fixture, not a patient DICOM study.
    image = sitk.Image([20, 16, 12], sitk.sitkFloat32)
    image.SetSpacing((0.4, 0.5, 0.7))
    image.SetOrigin((12.0, -8.0, 3.0))
    angle = np.deg2rad(17.0)
    c, s = np.cos(angle), np.sin(angle)
    # Rotate around patient X, then around Z to create a genuinely oblique volume.
    rx = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    az = np.deg2rad(11.0)
    cz, sz = np.cos(az), np.sin(az)
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    direction = rz @ rx
    image.SetDirection(tuple(direction.ravel()))
    # Asymmetric landmark makes axis flips easier to detect.
    image.SetPixel((3, 5, 7), 1234.0)

    out = _resample_to_patient_lps(image, sitk)
    out_direction = np.asarray(out.GetDirection()).reshape(3, 3)
    assert np.allclose(out_direction, np.eye(3), atol=1e-8)
    assert all(n > 0 for n in out.GetSize())
    assert np.all(np.isfinite(out.GetSpacing()))
    assert all(v > 0 for v in out.GetSpacing())
    # All eight original physical voxel-centre corners must lie inside the
    # output physical axis-aligned bounds (within one output voxel tolerance).
    lo = np.asarray(out.GetOrigin())
    hi = lo + (np.asarray(out.GetSize()) - 1) * np.asarray(out.GetSpacing())
    for x in (0, image.GetSize()[0]-1):
        for y in (0, image.GetSize()[1]-1):
            for z in (0, image.GetSize()[2]-1):
                p = np.asarray(image.TransformIndexToPhysicalPoint((x, y, z)))
                assert np.all(p >= lo - np.asarray(out.GetSpacing()) - 1e-6)
                assert np.all(p <= hi + np.asarray(out.GetSpacing()) + 1e-6)


def test_vtk_real_mesh_ray_cast_distinguishes_open_hole_from_blocked_plate():
    """Exercise a real ray/triangle engine available in this environment (VTK)."""
    vtk = pytest.importorskip("vtk")
    mesh = _square_ring_plate_mesh()
    points = vtk.vtkPoints()
    for p in mesh.vertices:
        points.InsertNextPoint(float(p[0]), float(p[1]), float(p[2]))
    cells = vtk.vtkCellArray()
    for face in mesh.faces:
        tri = vtk.vtkTriangle()
        for j, vertex_id in enumerate(face):
            tri.GetPointIds().SetId(j, int(vertex_id))
        cells.InsertNextCell(tri)
    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(cells)
    tree = vtk.vtkOBBTree()
    tree.SetDataSet(poly)
    tree.BuildLocator()

    def intersections(x):
        hit_points = vtk.vtkPoints()
        hit_cells = vtk.vtkIdList()
        tree.IntersectWithLine((x, 0, -12), (x, 0, 12), hit_points, hit_cells)
        return hit_points.GetNumberOfPoints()

    assert intersections(0.0) == 0, "ray through the aperture must not hit the guide mesh"
    assert intersections(3.0) == 2, "ray through plate material must hit both plate faces"
