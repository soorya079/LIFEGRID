"""Validated models used by LIFEGRID's local flood analysis API."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiverLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RiskAnalysisRequest(StrictModel):
    rainfall_mm: float = Field(ge=0, le=500, description="Rainfall in millimetres")
    river_level: RiverLevel
    population_density: float = Field(
        ge=0, le=50_000, description="People per square kilometre"
    )
    road_accessibility: float = Field(
        ge=0, le=100, description="Accessible-road percentage, where 100 is best"
    )
    shelter_capacity: float = Field(
        ge=0, le=100, description="Shelter adequacy percentage, where 100 is best"
    )
    medical_capacity: float = Field(
        ge=0, le=100, description="Medical capacity percentage, where 100 is best"
    )
    historical_risk: float = Field(
        ge=0, le=100, description="Synthetic historical-risk index"
    )


class FactorExplanation(StrictModel):
    factor: str
    input_value: float | str
    normalized_risk: float
    weight: float
    contribution: float
    rating: RiskLevel
    reason: str


class RiskAnalysisResult(StrictModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    factors: dict[str, RiskLevel]
    factor_details: list[FactorExplanation]
    explanation: list[str]
    model_version: str
    model_notice: str


class DemandAssumptions(StrictModel):
    water_litres_per_person: float = Field(default=3.0, ge=0, le=100)
    food_kits_per_person: float = Field(default=1.0, ge=0, le=10)
    medical_units_per_person: float = Field(default=0.05, ge=0, le=1)
    shelter_spaces_per_person: float = Field(default=0.30, ge=0, le=1)


class DemandEstimate(StrictModel):
    affected_population: int = Field(ge=0)
    water_litres: float = Field(ge=0)
    food_kits: int = Field(ge=0)
    medical_units: int = Field(ge=0)
    shelter_spaces: int = Field(ge=0)
    assumptions: DemandAssumptions
    notice: str


ScenarioName = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class FloodSimulationRequest(StrictModel):
    scenario: ScenarioName | None = None
    total_population: int | None = Field(default=None, ge=1, le=10_000_000)
    rainfall_mm: float | None = Field(default=None, ge=0, le=500)
    river_level: RiverLevel | None = None
    population_density: float | None = Field(default=None, ge=0, le=50_000)
    road_accessibility: float | None = Field(default=None, ge=0, le=100)
    shelter_capacity: float | None = Field(default=None, ge=0, le=100)
    medical_capacity: float | None = Field(default=None, ge=0, le=100)
    historical_risk: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_scenario_or_inputs(self) -> "FloodSimulationRequest":
        input_fields = {
            "rainfall_mm",
            "river_level",
            "population_density",
            "road_accessibility",
            "shelter_capacity",
            "medical_capacity",
            "historical_risk",
        }
        provided_inputs = input_fields.intersection(self.model_fields_set)
        if self.scenario is not None and provided_inputs:
            raise ValueError("Provide a named scenario or explicit risk inputs, not both")
        if self.scenario is None:
            missing = [
                field
                for field in input_fields | {"total_population"}
                if getattr(self, field) is None
            ]
            if missing:
                raise ValueError(
                    "Provide a scenario or all explicit inputs; missing: "
                    + ", ".join(sorted(missing))
                )
        return self


class SimulationResult(StrictModel):
    scenario: str
    risk: RiskAnalysisResult
    affected_population: int
    demand: DemandEstimate
    recommended_actions: list[str]
    assumptions: list[str]
    data_label: str


class SuccessEnvelope(StrictModel):
    success: Literal[True] = True
    data: dict


class ErrorDetail(StrictModel):
    code: str
    message: str
    details: list[dict[str, str]] | None = None


class ErrorEnvelope(StrictModel):
    success: Literal[False] = False
    error: ErrorDetail