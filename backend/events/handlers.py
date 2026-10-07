"""Independently testable handlers for the LIFEGRID event pipeline."""

from typing import TYPE_CHECKING

from backend.events.event_models import DomainEvent, EventType
from backend.models.report import EmergencyReport
from backend.models.risk import RiskAnalysisRequest
from backend.services import report_service, resource_service

if TYPE_CHECKING:
    from backend.events.event_bus import EventBus


def _event_context(report: EmergencyReport) -> dict:
    return {
        "report_id": report.report_id,
        "severity": report.severity,
        "location": {"latitude": report.latitude, "longitude": report.longitude},
    }


def handle_report_created(event: DomainEvent, bus: "EventBus") -> dict:
    report = report_service.get_report(event.report_id or "")
    location_risk, _risk_reason = report_service.location_risk_assessment(report.latitude, report.longitude)
    requirements = resource_service.calculate_requirements(report.people_affected)
    report = report_service.update_report_processing(
        report.report_id,
        risk_assessment=location_risk.model_dump(mode="json"),
        resource_requirements=requirements.model_dump(mode="json"),
        event_processing_status="RISK_ASSESSMENT_PENDING",
        event_processing_error=None,
    )
    child = DomainEvent(
        event_id=f"{event.event_id}:RISK_ASSESSED",
        event_type=EventType.RISK_ASSESSED,
        source="lifegrid.risk-processor",
        report_id=report.report_id,
        severity=report.severity,
        location={"latitude": report.latitude, "longitude": report.longitude},
        payload={
            "risk_assessment": location_risk.model_dump(mode="json"),
            "resource_requirements": requirements.model_dump(mode="json"),
        },
    )
    published = bus.publish(child)
    if not published.accepted:
        raise RuntimeError("Risk assessment event was not accepted")
    return {"risk_level": location_risk.risk_level.value, "risk_score": location_risk.risk_score}


def handle_risk_assessed(event: DomainEvent, bus: "EventBus") -> dict:
    report = report_service.get_report(event.report_id or "")
    shortages = resource_service.report_resource_shortages(report.report_id)
    shortage_records = [item.model_dump(mode="json") for item in shortages]
    status = "SHORTAGE_DETECTION_PENDING" if shortage_records else "COMPLETED"
    report_service.update_report_processing(
        report.report_id,
        risk_assessment=event.payload.get("risk_assessment", report.risk_assessment),
        resource_requirements=event.payload.get("resource_requirements", report.resource_requirements),
        resource_shortages=shortage_records,
        event_processing_status=status,
        event_processing_error=None,
    )
    if shortage_records:
        child = DomainEvent(
            event_id=f"{event.event_id}:RESOURCE_SHORTAGE",
            event_type=EventType.RESOURCE_SHORTAGE,
            source="lifegrid.resource-processor",
            report_id=report.report_id,
            severity=report.severity,
            location={"latitude": report.latitude, "longitude": report.longitude},
            payload={"shortages": shortage_records},
        )
        published = bus.publish(child)
        if not published.accepted:
            raise RuntimeError("Resource shortage event was not accepted")
    return {"shortage_types": [item["type"] for item in shortage_records]}


def handle_resource_shortage(event: DomainEvent, _bus: "EventBus") -> dict:
    report = report_service.get_report(event.report_id or "")
    shortages = event.payload.get("shortages", [])
    report_service.update_report_processing(
        report.report_id,
        resource_shortages=shortages,
        event_processing_status="SHORTAGE_DETECTED",
        event_processing_error=None,
    )
    return {"shortage_count": len(shortages)}


def handle_resource_allocated(event: DomainEvent, _bus: "EventBus") -> dict:
    if not event.report_id:
        return {"report_linked": False}
    report = report_service.get_report(event.report_id)
    allocation = event.payload.get("allocation", {})
    report_service.update_report_processing(
        report.report_id,
        allocation_events=[*report.allocation_events, allocation],
    )
    return {"report_linked": True, "allocation_id": allocation.get("allocation_id")}


def handle_report_verified(event: DomainEvent, _bus: "EventBus") -> dict:
    return {"report_id": event.report_id, "verified": True}


def handle_incident_resolved(event: DomainEvent, _bus: "EventBus") -> dict:
    if event.report_id:
        report_service.update_report_processing(
            event.report_id,
            event_processing_status="INCIDENT_RESOLVED",
            event_processing_error=None,
        )
    return {"report_id": event.report_id, "resolved": True}


def register_default_handlers(bus: "EventBus") -> None:
    bus.subscribe(EventType.REPORT_CREATED, "RiskProcessor", handle_report_created)
    bus.subscribe(EventType.REPORT_VERIFIED, "ReportVerification", handle_report_verified)
    bus.subscribe(EventType.RISK_ASSESSED, "ResourceProcessor", handle_risk_assessed)
    bus.subscribe(EventType.RESOURCE_SHORTAGE, "ShortageProcessor", handle_resource_shortage)
    bus.subscribe(EventType.RESOURCE_ALLOCATED, "AllocationProcessor", handle_resource_allocated)
    bus.subscribe(EventType.INCIDENT_RESOLVED, "ResolutionProcessor", handle_incident_resolved)
