"""Versioned LIFEGRID domain-event schemas with UTC timestamps."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import Field, field_validator

from backend.models.risk import StrictModel


class EventType(StrEnum):
    REPORT_CREATED = "REPORT_CREATED"
    REPORT_VERIFIED = "REPORT_VERIFIED"
    RISK_ASSESSED = "RISK_ASSESSED"
    RESOURCE_SHORTAGE = "RESOURCE_SHORTAGE"
    RESOURCE_ALLOCATED = "RESOURCE_ALLOCATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"


class EventLocation(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DomainEvent(StrictModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=160)
    event_type: EventType
    source: str = Field(min_length=1, max_length=120)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    report_id: str | None = Field(default=None, max_length=100)
    severity: int | None = Field(default=None, ge=1, le=5)
    location: EventLocation | None = None
    payload: dict = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)


class HandlerResult(StrictModel):
    event_id: str
    handler: str
    already_processed: bool
    success: bool
    attempts: int
    error: str | None = None


class PublishResult(StrictModel):
    event: DomainEvent
    accepted: bool
    mode: str
    handlers: list[HandlerResult] = Field(default_factory=list)


class FailedEventRecord(StrictModel):
    event_id: str
    event_type: EventType
    handler: str
    report_id: str | None = None
    error: str
    attempt: int = Field(ge=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)