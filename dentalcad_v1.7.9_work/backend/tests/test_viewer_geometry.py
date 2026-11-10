import numpy as np

from app.viewer import _stretch_rows


def test_stretch_rows_keeps_shape_when_spacing_is_isotropic():
    image = np.arange(12).reshape(3, 4)
    result = _stretch_rows(image, 1.0)
    assert result.shape == image.shape
    assert np.array_equal(result, image)


def test_stretch_rows_resamples_for_anisotropic_spacing():
    image = np.arange(12).reshape(3, 4)
    result = _stretch_rows(image, 2.0)
    assert result.shape == (6, 4)
    # Nearest-neighbour resampling duplicates rows rather than inventing values.
    assert np.array_equal(result[0], image[0])
    assert np.array_equal(result[-1], image[-1])


def test_stretch_rows_handles_very_small_positive_ratio():
    image = np.arange(12).reshape(3, 4)
    result = _stretch_rows(image, 0.1)
    assert result.shape == (1, 4)
    assert np.isfinite(result).all()


def test_render_slice_rejects_invalid_spacing():
    import pytest
    from app.viewer import render_slice

    volume = np.zeros((8, 8, 8), dtype=np.int16)
    with pytest.raises(ValueError, match="espacement voxel"):
        render_slice(volume, (0.3, 0.0, 0.3), "axial", 0, 300, 1000)

def test_render_slice_rejects_non_3d_volume():
    import pytest
    from app.viewer import render_slice

    with pytest.raises(ValueError, match="tableau 3D"):
        render_slice(np.zeros((8, 8)), (0.3, 0.3, 0.3), "axial", 0, 300, 1000)
