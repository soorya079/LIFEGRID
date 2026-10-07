"""
LIFEGRID Notification Processor Lambda handler.

Triggered by EventBridge rules on:
- RESOURCE_SHORTAGE events (from resource-processor)
- RESOURCE_ALLOCATED events (from api)

Records processing status in DynamoDB and emits structured logs
for CloudWatch observability.
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

REPORTS_TABLE = os.environ["REPORTS_TABLE"]
PROCESSED_EVENTS_TABLE = os.environ["PROCESSED_EVENTS_TABLE"]

_dynamo_reports = DynamoDBStore(REPORTS_TABLE, "report_id", [])
_report_svc.REPORTS_STORE = _dynamo_reports
_dynamo_idempotency = DynamoDBIdempotencyStore(PROCESSED_EVENTS_TABLE)

from backend.events.event_models import DomainEvent, EventType
from backend.services import report_service

HANDLER_SHORTAGE = "ShortageProcessor"
HANDLER_ALLOCATED = "AllocationProcessor"


def _handle_resource_shortage(domain_event: DomainEvent) -> dict:
    report_id = domain_event.report_id
    if not report_id:
        return {"skipped": True, "reason": "missing report_id"}

    already_processed = _dynamo_idempotency.is_processed(domain_event.event_id, HANDLER_SHORTAGE)
    if already_processed:
        return {"already_processed": True}

    shortages = domain_event.payload.get("shortages", [])
    report_service.update_report_processing(
        report_id,
        resource_shortages=shortages,
        event_processing_status="SHORTAGE_DETECTED",
        event_processing_error=None,
    )
    _dynamo_idempotency.mark_processed(domain_event.event_id, HANDLER_SHORTAGE)

    LOGGER.info(
        "Resource shortage recorded",
        extra={"report_id": report_id, "shortage_count": len(shortages)},
    )
    return {"report_id": report_id, "shortage_count": len(shortages)}


def _handle_resource_allocated(domain_event: DomainEvent) -> dict:
    report_id = domain_event.report_id
    if not report_id:
        return {"report_linked": False}

    already_processed = _dynamo_idempotency.is_processed(domain_event.event_id, HANDLER_ALLOCATED)
    if already_processed:
        return {"already_processed": True}

    allocation = domain_event.payload.get("allocation", {})
    try:
        report = report_service.get_report(report_id)
        report_service.update_report_processing(
            report.report_id,
            allocation_events=[*report.allocation_events, allocation],
        )
    except Exception as exc:
        LOGGER.warning("Could not update report with allocation", extra={"report_id": report_id, "error": str(exc)})

    _dynamo_idempotency.mark_processed(domain_event.event_id, HANDLER_ALLOCATED)

    LOGGER.info(
        "Allocation event processed",
        extra={"report_id": report_id, "allocation_id": allocation.get("allocation_id")},
    )
    return {"report_linked": True, "allocation_id": allocation.get("allocation_id")}


def lambda_handler(event: dict, context) -> dict:
    LOGGER.info("NotificationProcessor invoked", extra={"event_type": event.get("detail-type", "")})
    try:
        detail = event.get("detail", {})
        if isinstance(detail, str):
            detail = json.loads(detail)

        domain_event = DomainEvent.model_validate(detail)
        if domain_event.event_type == EventType.RESOURCE_SHORTAGE:
            result = _handle_resource_shortage(domain_event)
        elif domain_event.event_type == EventType.RESOURCE_ALLOCATED:
            result = _handle_resource_allocated(domain_event)
        else:
            LOGGER.warning("Unhandled event type", extra={"event_type": domain_event.event_type})
            result = {"skipped": True, "event_type": domain_event.event_type}

        return {"statusCode": 200, "body": result}
    except Exception as exc:
        LOGGER.exception("NotificationProcessor failed", extra={"error": str(exc)})
        return {"statusCode": 500, "body": {"error": str(exc)}}
