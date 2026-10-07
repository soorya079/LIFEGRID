"""
LIFEGRID Resource Processor Lambda handler.

Triggered by EventBridge rule on RISK_ASSESSED events.
Calculates resource shortages for the report, updates DynamoDB,
and emits RESOURCE_SHORTAGE if shortages exist.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

_TASK = Path("/var/task")
if str(_TASK) not in sys.path:
    sys.path.insert(0, str(_TASK))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger(__name__)

from dynamo_store import DynamoDBStore, DynamoDBIdempotencyStore  # noqa: E402

import backend.services.report_service as _report_svc
import backend.services.resource_service as _resource_svc
import backend.events.event_bus as _event_bus

REPORTS_TABLE = os.environ["REPORTS_TABLE"]
PROCESSED_EVENTS_TABLE = os.environ["PROCESSED_EVENTS_TABLE"]
RESOURCES_TABLE = os.environ["RESOURCES_TABLE"]
EVENTS_TABLE = os.environ["EVENTS_TABLE"]

_dynamo_reports = DynamoDBStore(REPORTS_TABLE, "report_id", [])
_report_svc.REPORTS_STORE = _dynamo_reports

_dynamo_resources = DynamoDBStore(RESOURCES_TABLE, "resource_id", [])
_dynamo_allocations = DynamoDBStore(RESOURCES_TABLE + "-Allocations", "allocation_id", [])
_resource_svc.RESOURCES_STORE = _dynamo_resources
_resource_svc.ALLOCATIONS_STORE = _dynamo_allocations

_dynamo_idempotency = DynamoDBIdempotencyStore(PROCESSED_EVENTS_TABLE)
_dynamo_events = DynamoDBStore(EVENTS_TABLE, "event_id", [])
_dynamo_failed = DynamoDBStore(EVENTS_TABLE + "-Failed", "event_id", [])
_event_bus.EVENTS_STORE = _dynamo_events
_event_bus.FAILED_EVENTS_STORE = _dynamo_failed

from backend.events.event_models import DomainEvent, EventType
from backend.events.event_bus import EventBridgeEventBus
from backend.services import report_service, resource_service

HANDLER_NAME = "ResourceProcessor"
_eb_bus: EventBridgeEventBus | None = None


def _get_event_bus() -> EventBridgeEventBus:
    global _eb_bus
    if _eb_bus is None:
        _eb_bus = EventBridgeEventBus()
    return _eb_bus


def _process_risk_assessed(domain_event: DomainEvent) -> dict:
    report_id = domain_event.report_id
    if not report_id:
        return {"skipped": True, "reason": "missing report_id"}

    already_processed = _dynamo_idempotency.is_processed(domain_event.event_id, HANDLER_NAME)
    if already_processed:
        LOGGER.info("Duplicate delivery — already processed", extra={"event_id": domain_event.event_id})
        return {"already_processed": True}

    report = report_service.get_report(report_id)
    shortages = resource_service.report_resource_shortages(report.report_id)
    shortage_records = [item.model_dump(mode="json") for item in shortages]
    status = "SHORTAGE_DETECTION_PENDING" if shortage_records else "COMPLETED"

    report_service.update_report_processing(
        report.report_id,
        risk_assessment=domain_event.payload.get("risk_assessment", report.risk_assessment),
        resource_requirements=domain_event.payload.get("resource_requirements", report.resource_requirements),
        resource_shortages=shortage_records,
        event_processing_status=status,
        event_processing_error=None,
    )

    if shortage_records:
        child = DomainEvent(
            event_id=f"{domain_event.event_id}:RESOURCE_SHORTAGE",
            event_type=EventType.RESOURCE_SHORTAGE,
            source="lifegrid.resource-processor",
            report_id=report.report_id,
            severity=report.severity,
            location={"latitude": report.latitude, "longitude": report.longitude},
            payload={"shortages": shortage_records},
        )
        _get_event_bus().publish(child)

    _dynamo_idempotency.mark_processed(domain_event.event_id, HANDLER_NAME)

    LOGGER.info(
        "Resource shortage assessment complete",
        extra={"report_id": report_id, "shortage_count": len(shortage_records)},
    )
    return {"report_id": report_id, "shortage_types": [item["type"] for item in shortage_records]}


def lambda_handler(event: dict, context) -> dict:
    LOGGER.info("ResourceProcessor invoked", extra={"event_type": event.get("detail-type", "")})
    try:
        detail = event.get("detail", {})
        if isinstance(detail, str):
            detail = json.loads(detail)
        domain_event = DomainEvent.model_validate(detail)
        result = _process_risk_assessed(domain_event)
        return {"statusCode": 200, "body": result}
    except Exception as exc:
        LOGGER.exception("ResourceProcessor failed", extra={"error": str(exc)})
        return {"statusCode": 500, "body": {"error": str(exc)}}
