"""Resource inventory, demand, matching, and allocation schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from backend.models.report import PriorityLevel
from backend.models.risk import StrictModel


class ResourceType(StrEnum):
    WATER = "WATER"
    FOOD = "FOOD"
    MEDICINE = "MEDICINE"
    SHELTER = "SHELTER"
    AMBULANCE = "AMBULANCE"


class ResourceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    EXHAUSTED = "EXHAUSTED"
    UNAVAILABLE = "UNAVAILABLE"


class ResourceRecord(StrictModel):
    resource_id: str
    type: ResourceType
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    available_quantity: float = Field(ge=0)
    unit: str
    capacity: float = Field(gt=0)
    status: ResourceStatus

    @model_validator(mode="after")
    def quantity_within_capacity(self) -> "ResourceRecord":
        if self.available_quantity > self.capacity:
            raise ValueError("available_quantity cannot exceed capacity")
        return self


class ResourceRequirements(StrictModel):
    water_required: int
    food_required: int
    medicine_required: int
    shelter_required: int
    ambulances_required: int
    assumptions: dict[str, float]
    formula: str


class RequirementRequest(StrictModel):
    affected_population: int = Field(ge=1, le=1_000_000)


class IncidentContext(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    affected_population: int = Field(ge=1, le=1_000_000)
    risk_level: PriorityLevel
    resource_type: ResourceType


class ResourceMatchRequest(IncidentContext):
    report_id: str | None = None


class ResourceRecommendation(StrictModel):
    resource_id: str
    name: str
    type: ResourceType
    unit: str
    latitude: float
    longitude: float
    distance_km: float
    available_quantity: float
    required_quantity: float
    recommended_quantity: float
    reason: str


class ResourceMatchResult(StrictModel):
    report_id: str | None = None
    resource_type: ResourceType
    risk_level: PriorityLevel
    required_quantity: float
    recommended_quantity: float
    shortage_quantity: float
    recommendations: list[ResourceRecommendation]
    assumptions: dict[str, float]
    method: str
    notice: str


class AllocationRequest(StrictModel):
    resource_id: str = Field(min_length=1, max_length=80)
    quantity: float = Field(gt=0, le=1_000_000_000)
    report_id: str | None = Field(default=None, max_length=80)
    actor: str = Field(default="LOCAL_OPERATOR", min_length=2, max_length=80)
    reason: str = Field(min_length=3, max_length=500)


class AllocationRecord(StrictModel):
    allocation_id: str
    resource_id: str
    resource_name: str
    resource_type: ResourceType
    quantity: float
    unit: str
    report_id: str | None = None
    actor: str
    reason: str
    timestamp: datetime
    remaining_inventory: float
    shortage_quantity: float
    assumptions: dict[str, float]
    shortage_formula: str
    data_label: str = "SYNTHETIC DEMO / LOCAL ALLOCATION"


class ResourceTypeSummary(StrictModel):
    type: ResourceType
    unit: str
    required: float
    available: float
    coverage_percent: float
    shortage: float
    resource_count: int


class ResourceSummary(StrictModel):
    requirements: ResourceRequirements
    resources: list[ResourceTypeSummary]
    open_report_count: int
    data_label: str


class ShortageSummary(StrictModel):
    shortages: list[ResourceTypeSummary]
    assumptions: dict[str, float]
    formula: str
    data_label: str