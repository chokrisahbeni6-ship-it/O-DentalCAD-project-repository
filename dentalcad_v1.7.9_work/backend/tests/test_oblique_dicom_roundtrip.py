"""Real synthetic DICOM oblique-series round-trip. Requires pydicom + SimpleITK."""
import uuid
from pathlib import Path

import numpy as np
import pytest

pydicom = pytest.importorskip("pydicom", reason="pydicom required for real DICOM round-trip")
sitk = pytest.importorskip("SimpleITK", reason="SimpleITK required for production DICOM reader")
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, CTImageStorage, generate_uid

from _dicom_ds import format_ds

def rotation_xyz(deg=(11.0, -7.0, 17.0)):
    ax, ay, az = np.radians(deg)
    Rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    Ry=np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]])
    Rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    return Rz @ Ry @ Rx


def test_real_oblique_dicom_roundtrip_through_dentalcad_reader(tmp_path):
    # Import production reader only after optional dependencies are confirmed.
    from app.segmentation import read_series
    rows, cols, slices = 32, 36, 24
    spacing_xyz = np.array([0.42, 0.57, 0.83])
    origin = np.array([31.2, -18.4, 42.7])
    D = rotation_xyz()
    study_uid, series_uid = generate_uid(), generate_uid()
    xdir, ydir, zdir = D[:,0], D[:,1], D[:,2]
    yy, xx = np.indices((rows, cols))
    for k in range(slices):
        meta = FileMetaDataset()
        meta.MediaStorageSOPClassUID = CTImageStorage
        meta.MediaStorageSOPInstanceUID = generate_uid()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds = FileDataset(str(tmp_path / f"slice_{k:04d}.dcm"), {}, file_meta=meta, preamble=b"\0"*128)
        ds.SOPClassUID = CTImageStorage; ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
        ds.StudyInstanceUID = study_uid; ds.SeriesInstanceUID = series_uid
        ds.Modality = "CT"; ds.PatientName = "SYNTHETIC^PHANTOM"; ds.PatientID = "SYNTHETIC_ONLY"
        ds.Rows = rows; ds.Columns = cols; ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"; ds.BitsAllocated = 16; ds.BitsStored = 16
        ds.HighBit = 15; ds.PixelRepresentation = 1
        ds.PixelSpacing = [format_ds(spacing_xyz[1]), format_ds(spacing_xyz[0])]
        ds.SliceThickness = format_ds(spacing_xyz[2]); ds.SpacingBetweenSlices = format_ds(spacing_xyz[2])
        ds.ImageOrientationPatient = [format_ds(v) for v in np.r_[xdir, ydir]]
        ipp = origin + zdir * spacing_xyz[2] * k
        ds.ImagePositionPatient = [format_ds(v) for v in ipp]
        ds.InstanceNumber = k + 1
        # Deterministic asymmetric intensity object; no patient data.
        image = np.full((rows, cols), -1000, dtype=np.int16)
        ell = ((xx-15)/8)**2 + ((yy-14)/6)**2
        bump = ((xx-23)/3)**2 + ((yy-20)/4)**2
        if k >= 4 and k <= 19:
            image[(ell <= 1.0) | (bump <= 1.0)] = 800
        ds.RescaleIntercept = 0; ds.RescaleSlope = 1
        ds.PixelData = image.tobytes()
        ds.save_as(ds.filename, write_like_original=False)

    image = read_series(str(tmp_path))
    assert image.GetDimension() == 3
    assert tuple(image.GetSize()) == (cols, rows, slices)
    assert np.allclose(image.GetSpacing(), spacing_xyz, atol=1e-4)
    assert np.allclose(image.GetOrigin(), origin, atol=1e-3)
    got_D = np.asarray(image.GetDirection()).reshape(3,3)
    assert np.allclose(got_D, D, atol=1e-4)
    assert np.linalg.det(got_D) > 0.999
