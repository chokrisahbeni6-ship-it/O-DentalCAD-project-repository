# DentalCAD v1.7.9 — R3 integration validation report

## Scope
- Added real-mesh integration fixture: a watertight square plate with a through-aperture.
- Added a VTK OBB-tree ray/triangle test which distinguishes a clear aperture axis from a ray through plate material.
- Added optional production integration tests for the `trimesh` ray backend (`rtree`) and SimpleITK oblique-volume resampling.
- Kept the original ZIP and R2 archive unchanged.

## Results in the current execution environment
- Existing and new runnable suite: **23 passed, 3 skipped**.
- VTK real-mesh ray test: passed; the central aperture ray had zero mesh intersections and the obstructed ray had two surface intersections.
- The `trimesh` production ray integration test was skipped because `rtree` is not installed.
- The SimpleITK oblique resampling integration test was skipped because `SimpleITK` is not installed.
- Attempts to install missing Python dependencies failed because package-index/network access is unavailable in this environment.

## Important limitations
- No anonymized patient DICOM series or clinical guide STL was supplied for this run. The LPS test uses a synthetic oblique image and is ready to run when SimpleITK is installed; it is not evidence of validation on real patient DICOM.
- The VTK ray test validates the mesh/aperture geometry using a real ray-triangle engine, but does not replace a run through the application's configured `trimesh`/`rtree` production path.
- No clinical, manufacturing, or regulatory validation is claimed. The guide generator itself labels its output as a test guide, not for intraoral use.

## Run on the intended backend environment
From `backend/`:

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. pytest -q
```

The full integration checks should run without skips once the pinned production dependencies are installed. For patient-data validation, use an anonymized DICOM series with known orientation landmarks and a representative guide mesh, and retain quantitative expected-vs-observed measurements.
