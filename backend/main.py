"""FastAPI entry point for the local LIFEGRID flood-response MVP."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.models.risk import (
    ErrorEnvelope,
    FloodSimulationRequest,
    RiskAnalysisRequest,
    SuccessEnvelope,
)
from backend.models.report import (
    ReportCreateRequest,
    ReportProcessingStatus,
    ReportStatus,
    ReportStatusUpdate,
)
from backend.models.resource import (
    AllocationRequest,
    RequirementRequest,
    ResourceMatchRequest,
)
from backend.services import report_service, resource_service
from backend.services.json_store import DataStoreError
from backend.services.report_service import ReportConflictError, ReportNotFoundError
from backend.services.risk_engine import analyze_risk
from backend.services.simulation_engine import simulate_flood
from backend.services.resource_service import (
    AllocationConflictError,
    ResourceNotFoundError,
)
from backend.events.event_bus import (
    get_event_bus,
    local_event_history,
    local_failed_event_history,
)
from backend.events.event_models import DomainEvent, EventLocation, EventType

DATA_FILE = Path(__file__).parent / "data" / "sample_zones.json"
LOGGER = logging.getLogger(__name__)

app = FastAPI(
    title="LIFEGRID Local Flood Response API",
    description=(
        "Local synthetic-demo API for deterministic, explainable flood-risk "
        "and demand estimates. Not an official warning or validated forecast."
    ),
    version="0.1.0",
)
_raw_origins = os.getenv(
    "LIFEGRID_FRONTEND_ORIGIN",
    "http://127.0.0.1:5173,http://localhost:5173",
)
# Support comma-separated origins (e.g. "https://soorya079.github.io,http://127.0.0.1:5173")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Accept"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "location": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    payload = ErrorEnvelope(
        error={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": details,
        }
    )
    return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    message = str(exc.detail) if isinstance(exc.detail, str) else "Request failed"
    payload = ErrorEnvelope(error={"code": code, "message": message})
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(mode="json", exclude_none=True),
        headers=exc.headers,
    )


@app.exception_handler(ReportNotFoundError)
@app.exception_handler(ResourceNotFoundError)
async def not_found_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    payload = ErrorEnvelope(error={"code": "NOT_FOUND", "message": str(exc)})
    return JSONResponse(status_code=404, content=payload.model_dump(mode="json", exclude_none=True))


@app.exception_handler(ReportConflictError)
@app.exception_handler(AllocationConflictError)
async def conflict_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    payload = ErrorEnvelope(error={"code": "CONFLICT", "message": str(exc)})
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json", exclude_none=True))


@app.exception_handler(DataStoreError)
async def data_store_error_handler(_request: Request, _exc: DataStoreError) -> JSONResponse:
    payload = ErrorEnvelope(error={"code": "DATA_STORE_ERROR", "message": "Local data could not be read or safely updated."})
    return JSONResponse(status_code=500, content=payload.model_dump(mode="json", exclude_none=True))


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    LOGGER.error("Unexpected local API error", exc_info=exc)
    payload = ErrorEnvelope(error={"code": "INTERNAL_ERROR", "message": "The request could not be completed. Try again or inspect local server logs."})
    return JSONResponse(status_code=500, content=payload.model_dump(mode="json", exclude_none=True))


def _success(data: Any) -> dict[str, Any]:
    return SuccessEnvelope(data=data).model_dump(mode="json")


@app.get("/", response_model=SuccessEnvelope)
async def root() -> dict[str, Any]:
    return _success(
        {
            "service": "LIFEGRID Local Flood Response API",
            "mode": "local synthetic demo",
            "docs": "/docs",
        }
    )


@app.get("/health", response_model=SuccessEnvelope)
async def health() -> dict[str, Any]:
    return _success({"status": "ok", "mode": "local"})


@app.get("/api/v1/zones", response_model=SuccessEnvelope)
async def list_zones() -> dict[str, Any]:
    with DATA_FILE.open(encoding="utf-8") as data_file:
        data = json.load(data_file)
    return _success(data)


@app.post("/api/v1/risk/analyze", response_model=SuccessEnvelope)
async def risk_analyze(payload: RiskAnalysisRequest) -> dict[str, Any]:
    return _success(analyze_risk(payload).model_dump(mode="json"))


@app.post("/api/v1/simulation/flood", response_model=SuccessEnvelope)
async def flood_simulation(payload: FloodSimulationRequest) -> dict[str, Any]:
    result = simulate_flood(payload)
    return _success(result.model_dump(mode="json"))


@app.post("/api/v1/reports", status_code=201, response_model=SuccessEnvelope)
async def create_report(payload: ReportCreateRequest) -> dict[str, Any]:
    report = report_service.create_report(payload)
    event = DomainEvent(
        event_type=EventType.REPORT_CREATED,
        source="lifegrid.api",
        report_id=report.report_id,
        severity=report.severity,
        location=EventLocation(latitude=report.latitude, longitude=report.longitude),
        payload={"category": report.category.value, "source": report.source.value},
    )
    try:
        published = get_event_bus().publish(event)
        if not published.accepted:
            report = report_service.update_report_processing(
                report.report_id,
                event_processing_status=ReportProcessingStatus.FAILED,
                event_processing_error="One or more local event handlers failed; see failed-event history.",
            )
    except Exception as error:
        LOGGER.exception("Could not publish report-created event", extra={"event_id": event.event_id, "report_id": report.report_id})
        report = report_service.update_report_processing(
            report.report_id,
            event_processing_status=ReportProcessingStatus.FAILED,
            event_processing_error=f"Event publication failed: {type(error).__name__}",
        )
    return _success(report_service.get_report(report.report_id).model_dump(mode="json"))


@app.get("/api/v1/reports", response_model=SuccessEnvelope)
async def list_reports() -> dict[str, Any]:
    return _success(report_service.list_reports().model_dump(mode="json"))


@app.get("/api/v1/reports/{report_id}", response_model=SuccessEnvelope)
async def get_report(report_id: str) -> dict[str, Any]:
    return _success(report_service.get_report(report_id).model_dump(mode="json"))


@app.patch("/api/v1/reports/{report_id}/status", response_model=SuccessEnvelope)
async def patch_report_status(
    report_id: str, payload: ReportStatusUpdate
) -> dict[str, Any]:
    report = report_service.update_report_status(report_id, payload)
    event_type = {
        ReportStatus.VERIFIED: EventType.REPORT_VERIFIED,
        ReportStatus.RESOLVED: EventType.INCIDENT_RESOLVED,
    }.get(report.status)
    if event_type is not None:
        event = DomainEvent(
            event_type=event_type,
            source="lifegrid.api",
            report_id=report.report_id,
            severity=report.severity,
            location=EventLocation(latitude=report.latitude, longitude=report.longitude),
            payload={"status": report.status.value},
        )
        try:
            result = get_event_bus().publish(event)
            if not result.accepted:
                report = report_service.update_report_processing(
                    report.report_id,
                    event_processing_error="Status event handler failed; see failed-event history.",
                )
        except Exception as error:
            LOGGER.exception("Could not publish report status event", extra={"event_id": event.event_id, "report_id": report.report_id})
            report = report_service.update_report_processing(
                report.report_id,
                event_processing_error=f"Event publication failed: {type(error).__name__}",
            )
    return _success(report_service.get_report(report.report_id).model_dump(mode="json"))


@app.delete("/api/v1/reports/{report_id}", response_model=SuccessEnvelope)
async def remove_report(report_id: str) -> dict[str, Any]:
    report_service.delete_report(report_id)
    return _success({"deleted": True, "report_id": report_id})


@app.get("/api/v1/resources", response_model=SuccessEnvelope)
async def list_resources() -> dict[str, Any]:
    resources, data_label = resource_service.list_resources()
    return _success({"resources": [item.model_dump(mode="json") for item in resources], "data_label": data_label})


@app.get("/api/v1/resources/summary", response_model=SuccessEnvelope)
async def get_resource_summary() -> dict[str, Any]:
    return _success(resource_service.resource_summary().model_dump(mode="json"))


@app.get("/api/v1/resources/shortages", response_model=SuccessEnvelope)
async def get_resource_shortages() -> dict[str, Any]:
    return _success(resource_service.resource_shortages().model_dump(mode="json"))


@app.get("/api/v1/resources/allocations", response_model=SuccessEnvelope)
async def get_allocation_history() -> dict[str, Any]:
    allocations = resource_service.allocation_history()
    return _success({"allocations": [item.model_dump(mode="json") for item in allocations], "count": len(allocations)})


@app.get("/api/v1/resources/{resource_id}", response_model=SuccessEnvelope)
async def get_resource(resource_id: str) -> dict[str, Any]:
    return _success(resource_service.get_resource(resource_id).model_dump(mode="json"))


@app.post("/api/v1/resources/requirements", response_model=SuccessEnvelope)
async def get_requirements(payload: RequirementRequest) -> dict[str, Any]:
    return _success(resource_service.calculate_requirements(payload.affected_population).model_dump(mode="json"))


@app.post("/api/v1/resources/match", response_model=SuccessEnvelope)
async def match_resources(payload: ResourceMatchRequest) -> dict[str, Any]:
    return _success(resource_service.match_resources(payload).model_dump(mode="json"))


@app.post("/api/v1/resources/allocate", status_code=201, response_model=SuccessEnvelope)
async def allocate_resource(payload: AllocationRequest) -> dict[str, Any]:
    allocation = resource_service.allocate_resource(payload)
    event = DomainEvent(
        event_id=f"allocation:{allocation.allocation_id}",
        event_type=EventType.RESOURCE_ALLOCATED,
        source="lifegrid.api",
        report_id=allocation.report_id,
        payload={"allocation": allocation.model_dump(mode="json")},
    )
    try:
        result = get_event_bus().publish(event)
        event_state = {"status": "ACCEPTED" if result.accepted else "FAILED", "event_id": event.event_id}
    except Exception as error:
        LOGGER.exception("Could not publish resource-allocated event", extra={"event_id": event.event_id, "report_id": allocation.report_id})
        event_state = {"status": "FAILED", "event_id": event.event_id, "error": type(error).__name__}
    return _success({**allocation.model_dump(mode="json"), "event_processing": event_state})


@app.get("/api/v1/events", response_model=SuccessEnvelope)
async def get_events() -> dict[str, Any]:
    events = local_event_history()
    return _success({"events": events, "count": len(events), "mode": os.getenv("APP_ENV", "local")})


@app.get("/api/v1/events/failed", response_model=SuccessEnvelope)
async def get_failed_events() -> dict[str, Any]:
    failures = local_failed_event_history()
    return _success({"failed_events": failures, "count": len(failures), "mode": os.getenv("APP_ENV", "local")})