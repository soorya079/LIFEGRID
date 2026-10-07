"""Citizen report request and response schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from backend.models.risk import StrictModel


class ReportCategory(StrEnum):
    FLOOD = "FLOOD"
    ROAD_BLOCK = "ROAD_BLOCK"
    MEDICAL = "MEDICAL"
    SHELTER = "SHELTER"
    FOOD = "FOOD"
    WATER = "WATER"
    FIRE = "FIRE"
    OTHER = "OTHER"


class ReportStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    VERIFIED = "VERIFIED"
    DISPATCHED = "DISPATCHED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class ReportSource(StrEnum):
    CITIZEN = "CITIZEN"
    SIMULATION = "SIMULATION"


class PriorityLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReportCreateRequest(StrictModel):
    category: ReportCategory
    title: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=8, max_length=2_000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    severity: int = Field(ge=1, le=5, description="1 minor to 5 extreme")
    people_affected: int = Field(default=0, ge=0, le=1_000_000)
    source: ReportSource = ReportSource.CITIZEN


class ReportStatusUpdate(StrictModel):
    status: ReportStatus
    actor: str = Field(default="LOCAL_OPERATOR", min_length=2, max_length=80)
    reason: str = Field(min_length=3, max_length=500)


class ReportStatusEvent(StrictModel):
    timestamp: datetime
    actor: str
    status: ReportStatus
    reason: str


class ReportProcessingStatus(StrEnum):
    PENDING = "PENDING"
    RISK_ASSESSMENT_PENDING = "RISK_ASSESSMENT_PENDING"
    SHORTAGE_DETECTION_PENDING = "SHORTAGE_DETECTION_PENDING"
    COMPLETED = "COMPLETED"
    SHORTAGE_DETECTED = "SHORTAGE_DETECTED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    FAILED = "FAILED"


class EmergencyReport(StrictModel):
    report_id: str
    category: ReportCategory
    title: str
    description: str
    latitude: float
    longitude: float
    severity: int
    people_affected: int
    timestamp: datetime
    status: ReportStatus
    source: ReportSource
    priority_score: int = Field(ge=0, le=100)
    priority_level: PriorityLevel
    priority_explanation: list[str]
    location_risk_score: int = Field(ge=0, le=100)
    possible_duplicate: bool = False
    duplicate_report_ids: list[str] = Field(default_factory=list)
    status_history: list[ReportStatusEvent] = Field(default_factory=list)
    data_label: str = "SYNTHETIC DEMO / LOCAL REPORT DATA"
    risk_assessment: dict | None = None
    resource_requirements: dict | None = None
    resource_shortages: list[dict] = Field(default_factory=list)
    allocation_events: list[dict] = Field(default_factory=list)
    event_processing_status: ReportProcessingStatus = ReportProcessingStatus.PENDING
    event_processing_error: str | None = None


class ReportListResponse(StrictModel):
    reports: list[EmergencyReport]
    count: int
    data_label: str
