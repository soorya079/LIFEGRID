"""
LIFEGRID API Lambda handler — mounts the FastAPI app via Mangum ASGI adapter.

This Lambda function wraps the existing backend FastAPI application
(unchanged business logic from Phase 6) and routes all API Gateway HTTP API
events through it. DynamoDB stores are injected via environment variables;
the local JSON store fallback is disabled in aws mode.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# ── Path setup: add task dir (contains backend/) to sys.path ─────────────────
_TASK = Path("/var/task")
if str(_TASK) not in sys.path:
    sys.path.insert(0, str(_TASK))

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger(__name__)

# ── Import DynamoDB store (bundled alongside this handler.py) ────────────────
from dynamo_store import DynamoDBStore, DynamoDBIdempotencyStore  # noqa: E402

import backend.services.report_service as _report_svc
import backend.services.resource_service as _resource_svc
import backend.events.event_bus as _event_bus
import backend.events.idempotency as _idempotency

REPORTS_TABLE = os.environ["REPORTS_TABLE"]
RESOURCES_TABLE = os.environ["RESOURCES_TABLE"]
EVENTS_TABLE = os.environ["EVENTS_TABLE"]
PROCESSED_EVENTS_TABLE = os.environ["PROCESSED_EVENTS_TABLE"]

# Patch report store
_dynamo_reports = DynamoDBStore(REPORTS_TABLE, "report_id", [])
_report_svc.REPORTS_STORE = _dynamo_reports

# Patch resource and allocation stores
# Allocations are stored in the same table with a different PK prefix
_dynamo_resources = DynamoDBStore(RESOURCES_TABLE, "resource_id", [])
_dynamo_allocations = DynamoDBStore(RESOURCES_TABLE + "-Allocations", "allocation_id", [])
_resource_svc.RESOURCES_STORE = _dynamo_resources
_resource_svc.ALLOCATIONS_STORE = _dynamo_allocations

# Patch event stores
_dynamo_events = DynamoDBStore(EVENTS_TABLE, "event_id", [])
_dynamo_failed = DynamoDBStore(EVENTS_TABLE + "-Failed", "event_id", [])
_event_bus.EVENTS_STORE = _dynamo_events
_event_bus.FAILED_EVENTS_STORE = _dynamo_failed

# Patch idempotency store
_dynamo_idempotency = DynamoDBIdempotencyStore(PROCESSED_EVENTS_TABLE)
_idempotency.PROCESSED_EVENTS_STORE = _dynamo_idempotency  # type: ignore[assignment]

# Now import the app — stores are already patched
from backend.main import app  # noqa: E402

try:
    from mangum import Mangum
    # Mangum 0.22 reads requestContext.http.path (NOT rawPath) for HTTP API v2.
    # That path includes the stage prefix, e.g. /prod/health.
    # api_gateway_base_path="/prod" strips it so FastAPI sees /health, /api/v1/... correctly.
    _handler = Mangum(app, lifespan="off", api_gateway_base_path="/prod")
except ImportError:
    LOGGER.error("mangum is not installed — cannot wrap FastAPI for Lambda")
    raise


def lambda_handler(event: dict, context) -> dict:
    """
    AWS Lambda entry point.
    Routes API Gateway HTTP API v2 payload format events to the FastAPI app.
    """
    LOGGER.info(
        "LIFEGRID API request",
        extra={
            "path": event.get("rawPath", "/"),
            "method": event.get("requestContext", {}).get("http", {}).get("method", ""),
            "request_id": event.get("requestContext", {}).get("requestId", ""),
        },
    )
    return _handler(event, context)



