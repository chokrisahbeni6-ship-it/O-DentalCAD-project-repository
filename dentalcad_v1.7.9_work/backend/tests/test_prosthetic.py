"""Regression tests for incomplete prosthetic tooth data."""
from app.prosthetic import plan_report


def _implant(tooth):
    return {"position": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, -1.0],
            "length": 10.0, "diameter": 3.6, "tooth": tooth}


def test_missing_tooth_center_does_not_raise_key_error():
    report = plan_report([_implant({"fdi": "36"})])
    assert report["prosthetic"] == [
        {"implant": 1, "tooth": "36", "status": "incomplete_missing_center"}
    ]
    assert any("centre de la dent prevue absent" in warning for warning in report["warnings"])


def test_invalid_tooth_center_does_not_crash_report():
    report = plan_report([_implant({"fdi": "36", "center": [1.0, float("nan"), 2.0]})])
    assert report["prosthetic"][0]["status"] == "invalid_center"
    assert any("centre de la dent prevue invalide" in warning for warning in report["warnings"])


def test_valid_tooth_center_still_calculates_prosthetic_metrics():
    report = plan_report([_implant({"fdi": "36", "center": [1.0, 0.0, -5.0]})])
    assert report["prosthetic"][0]["offset_mm"] == 1.0
    assert report["prosthetic"][0]["tooth"] == "36"
