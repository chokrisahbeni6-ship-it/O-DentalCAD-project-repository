"""Tests de régression du modèle utilisé pour la génération du guide."""
import pytest
from pydantic import ValidationError

from app.models_schemas import ImplantPlan


def test_implant_plan_preserves_optional_tooth():
    tooth = {"fdi": "36", "center": [12.0, 4.0, -8.0], "axis": [0.0, 0.0, -1.0]}
    plan = ImplantPlan(
        system_id="test-system", diameter=3.6, length=12.0,
        position=[12.0, 4.0, -8.0], axis=[0.0, 0.0, -1.0], tooth=tooth,
    )
    assert plan.model_dump()["tooth"] == tooth


def test_implant_plan_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ImplantPlan(diameter=3.6, length=12.0, position=[0.0, 0.0, 0.0],
                    unexpected_field="must not be silently ignored")
