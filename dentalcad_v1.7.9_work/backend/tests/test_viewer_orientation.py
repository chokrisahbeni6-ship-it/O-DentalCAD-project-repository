import numpy as np

from app.viewer import _resample_to_patient_lps


class FakeImage:
    def __init__(self, size, spacing, origin, direction):
        self.size = tuple(size)
        self.spacing = tuple(spacing)
        self.origin = np.asarray(origin, dtype=float)
        self.direction = np.asarray(direction, dtype=float).reshape(3, 3)

    def GetSize(self):
        return self.size

    def GetSpacing(self):
        return self.spacing

    def TransformIndexToPhysicalPoint(self, idx):
        return tuple(self.origin + self.direction @ (np.asarray(idx) * self.spacing))

    def GetPixelID(self):
        return 16

    def GetDirection(self):
        return tuple(self.direction.ravel())


class FakeSitk:
    sitkIdentity = 0
    sitkLinear = 1

    @staticmethod
    def Transform(*args):
        return args

    @staticmethod
    def Resample(*args):
        return args


def test_oblique_volume_resampling_targets_patient_lps_axes_and_preserves_bounds():
    # 90-degree in-plane rotation plus oblique Z tilt.
    a = np.radians(90)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    image = FakeImage((10, 20, 30), (0.4, 0.5, 0.6), (12, -8, 3), Rz)
    result = _resample_to_patient_lps(image, FakeSitk)
    # Resample args: input, size, transform, interpolator, origin, spacing, direction...
    output_size, output_origin, output_spacing, output_direction = result[1], result[4], result[5], result[6]
    assert output_size == [20, 10, 30]
    assert np.allclose(output_origin, [2.5, -8.0, 3.0])
    assert np.allclose(output_spacing, [0.5, 0.4, 0.6])
    assert np.allclose(output_direction, np.eye(3).ravel())
