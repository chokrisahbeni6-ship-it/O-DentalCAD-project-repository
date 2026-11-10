from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImplantPlan(BaseModel):
    # Les champs inconnus doivent échouer explicitement plutôt que disparaître silencieusement.
    model_config = ConfigDict(extra="forbid")
    system_id: Optional[str] = None
    diameter: float = Field(gt=0, le=10)           # mm
    length: float = Field(gt=0, le=25)             # mm
    position: List[float] = Field(min_length=3, max_length=3)   # mm, repère CBCT
    axis: List[float] = Field(default_factory=lambda: [0.0, 0.0, -1.0], min_length=3, max_length=3)  # vers l'apex
    tooth: Optional[Dict[str, Any]] = None  # dent planifiée normalisée (FDI, centre, axe éventuel)


class GuideParams(BaseModel):
    clearance_mm: float = Field(0.3, ge=0.1, le=1.0)          # jeu autour de l'implant
    plate_thickness_mm: float = Field(4.0, ge=2.0, le=10.0)
    air_gap_mm: float = Field(0.5, ge=0.0, le=3.0)            # distance plaque / gencive
    margin_mm: float = Field(8.0, ge=4.0, le=20.0)
    min_wall_mm: float = Field(1.5, ge=1.0, le=5.0)           # paroi minimale entre trous
