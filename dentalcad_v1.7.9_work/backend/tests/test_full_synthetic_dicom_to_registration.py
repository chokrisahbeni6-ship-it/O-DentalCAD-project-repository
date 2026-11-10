"""Full production-path test: synthetic oblique DICOM -> segmentation/STL export -> ICP.
Requires pydicom and SimpleITK. It is intentionally skipped if dependencies are absent.
"""
import numpy as np
from _dicom_ds import format_ds
import pytest

pydicom = pytest.importorskip("pydicom", reason="pydicom required for synthetic DICOM generation")
sitk = pytest.importorskip("SimpleITK", reason="SimpleITK required for production pipeline")
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, CTImageStorage, generate_uid
from pydicom.valuerep import DSfloat


def _ds_values(values):
    """Format DICOM DS values within the 16-character limit."""
    return [DSfloat(float(v), auto_format=True) for v in values]


def _rotation():
    ax, ay, az = np.radians([8.0, -6.0, 13.0])
    Rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    Ry=np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]])
    Rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    return Rz @ Ry @ Rx


def _write_oblique_dicom_phantom(folder):
    rows = cols = 48; slices = 32
    spacing = np.array([0.45, 0.55, 0.8])
    origin = np.array([21.5, -32.0, 14.25]); D = _rotation()
    study, series = generate_uid(), generate_uid()
    yy, xx = np.indices((rows, cols))
    for k in range(slices):
        meta = FileMetaDataset(); meta.MediaStorageSOPClassUID = CTImageStorage
        meta.MediaStorageSOPInstanceUID = generate_uid(); meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds = FileDataset(str(folder / f"im{k:04d}.dcm"), {}, file_meta=meta, preamble=b"\0"*128)
        ds.SOPClassUID=CTImageStorage; ds.SOPInstanceUID=meta.MediaStorageSOPInstanceUID
        ds.StudyInstanceUID=study; ds.SeriesInstanceUID=series; ds.Modality="CT"
        ds.PatientName="SYNTHETIC^PHANTOM"; ds.PatientID="SYNTHETIC_ONLY"
        ds.Rows=rows; ds.Columns=cols; ds.SamplesPerPixel=1; ds.PhotometricInterpretation="MONOCHROME2"
        ds.BitsAllocated=16; ds.BitsStored=16; ds.HighBit=15; ds.PixelRepresentation=1
        ds.PixelSpacing=[format_ds(spacing[1]), format_ds(spacing[0])]
        ds.SliceThickness=DSfloat(float(spacing[2]), auto_format=True); ds.SpacingBetweenSlices=DSfloat(float(spacing[2]), auto_format=True)
        ds.ImageOrientationPatient=[format_ds(v) for v in np.r_[D[:,0],D[:,1]]]
        ds.ImagePositionPatient=[format_ds(v) for v in origin + D[:,2]*spacing[2]*k]
        ds.InstanceNumber=k+1; ds.RescaleIntercept=0; ds.RescaleSlope=1
        image=np.full((rows,cols),-1000,dtype=np.int16)
        # Asymmetric union: ellipsoid + off-axis protrusion to reduce rotational ambiguity.
        ell=((xx-22)/13)**2+((yy-23)/10)**2
        bump=((xx-31)/4)**2+((yy-16)/5)**2
        if 5 <= k <= 26:
            image[(ell<=1.0)|(bump<=1.0)] = 800
        ds.PixelData=image.tobytes(); ds.save_as(ds.filename, write_like_original=False)
    return spacing, origin, D, (cols, rows, slices)


def test_full_synthetic_oblique_dicom_to_production_stl_and_icp(tmp_path):
    from app.segmentation import read_series, segment_cbct_advanced
    from app.registration import icp_align
    spacing, origin, direction, size = _write_oblique_dicom_phantom(tmp_path)
    image=read_series(str(tmp_path))
    assert tuple(image.GetSize()) == size
    assert np.allclose(image.GetSpacing(), spacing, atol=1e-4)
    assert np.allclose(image.GetOrigin(), origin, atol=1e-3)
    assert np.allclose(np.asarray(image.GetDirection()).reshape(3,3), direction, atol=1e-4)

    output=tmp_path / "production_output"
    segmentation=segment_cbct_advanced(str(tmp_path), str(output), threshold=300)
    stl=output / "bone.stl"
    assert stl.exists() and stl.stat().st_size > 1000
    assert segmentation["bone_voxels"] > 1000

    result=icp_align(str(tmp_path), str(stl), threshold=300, max_rms=1.0)
    matrix=np.asarray(result["matrix"],dtype=float)
    assert matrix.shape == (4,4) and np.isfinite(matrix).all()
    assert np.isfinite(result["rms_all_mm"]) and np.isfinite(result["p95_mm"])
    assert result["rms_all_mm"] < 2.0
    # Same-frame export/registration should not require a large rigid correction.
    assert np.linalg.norm(matrix[:3,3]) < 2.0
