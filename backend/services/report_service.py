"""Local citizen-report intake, priority, and duplicate heuristics."""

import json
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

from backend.config import (
    CATEGORY_URGENCY_SCORES,
    DUPLICATE_DISTANCE_METERS,
    DUPLICATE_MIN_DESCRIPTION_SIMILARITY,
    DUPLICATE_TIME_WINDOW_HOURS,
    EARTH_RADIUS_KM,
    PRIORITY_POPULATION_NORMALIZATION_MAX,
    PRIORITY_WEIGHTS,
)
from backend.models.report import (
    EmergencyReport,
    PriorityLevel,
    ReportCreateRequest,
    ReportListResponse,
    ReportSource,
    ReportStatus,
    ReportStatusEvent,
    ReportStatusUpdate,
)
from backend.models.risk import RiskAnalysisRequest
from backend.services.json_store import DataStoreError, JsonFileStore
from backend.services.risk_engine import analyze_risk

DATA_DIR = Path(os.getenv("LIFEGRID_DATA_DIR", Path(__file__).parents[1] / "data"))
REPORTS_STORE = JsonFileStore(DATA_DIR / "reports.json", [])
ZONES_FILE = DATA_DIR / "sample_zones.json"
REPORT_DATA_LABEL = "SYNTHETIC DEMO DATA - reports are unverified local decision-support inputs."
PRIORITY_NOTICE = "LIFEGRID MVP decision-support heuristic; not scientifically validated."

ALLOWED_STATUS_TRANSITIONS: dict[ReportStatus, set[ReportStatus]] = {
    ReportStatus.RECEIVED: {ReportStatus.VALIDATING, ReportStatus.REJECTED},
    ReportStatus.VALIDATING: {ReportStatus.VERIFIED, ReportStatus.REJECTED},
    ReportStatus.VERIFIED: {ReportStatus.DISPATCHED, ReportStatus.REJECTED},
    ReportStatus.DISPATCHED: {ReportStatus.RESOLVED},
    ReportStatus.RESOLVED: set(),
    ReportStatus.REJECTED: set(),
}


class ReportNotFoundError(LookupError):
    pass


class ReportConflictError(ValueError):
    pass


def haversine_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    haversine = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, haversine)))


def _location_risk(latitude: float, longitude: float) -> tuple[int, str]:
    assessment, reason = location_risk_assessment(latitude, longitude)
    return assessment.risk_score, reason


def location_risk_assessment(latitude: float, longitude: float):
    try:
        with ZONES_FILE.open(encoding="utf-8") as zones_file:
            zones = json.load(zones_file).get("zones", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        zones = []
    if not zones:
        request = RiskAnalysisRequest(
            rainfall_mm=0,
            river_level="LOW",
            population_density=0,
            road_accessibility=100,
            shelter_capacity=100,
            medical_capacity=100,
            historical_risk=0,
        )
        return analyze_risk(request), "No synthetic zone reference was available; location risk contribution is zero."
    nearest = min(zones, key=lambda zone: haversine_km(latitude, longitude, zone["latitude"], zone["longitude"]))
    result = analyze_risk(RiskAnalysisRequest(
        rainfall_mm=nearest["rainfall_mm"],
        river_level=nearest["river_level"],
        population_density=nearest["population_density"],
        road_accessibility=nearest["road_accessibility"],
        shelter_capacity=nearest["shelter_capacity"],
        medical_capacity=nearest["medical_capacity"],
        historical_risk=nearest["historical_risk"],
    ))
    return result, f"Nearest synthetic zone {nearest['name']} has risk score {result.risk_score}."


def calculate_priority(
    request: ReportCreateRequest,
    location_risk_score: int,
    location_reason: str | None = None,
) -> tuple[int, PriorityLevel, list[str]]:
    severity_score = request.severity * 20
    people_score = min(100.0, math.log1p(request.people_affected) / math.log1p(PRIORITY_POPULATION_NORMALIZATION_MAX) * 100)
    category_score = CATEGORY_URGENCY_SCORES[request.category.value]
    contributions = {
        "severity": severity_score * PRIORITY_WEIGHTS["severity"],
        "people affected": people_score * PRIORITY_WEIGHTS["people_affected"],
        "category urgency": category_score * PRIORITY_WEIGHTS["category_urgency"],
        "location risk": location_risk_score * PRIORITY_WEIGHTS["location_risk"],
    }
    score = round(sum(contributions.values()))
    level = _priority_level(score)
    explanation = [
        f"Severity {request.severity}/5 contributes {contributions['severity']:.1f} points.",
        f"{request.people_affected} people affected contributes {contributions['people affected']:.1f} points.",
        f"{request.category.value} category urgency contributes {contributions['category urgency']:.1f} points.",
        f"{location_reason or 'Nearest synthetic-zone score was used.'} Location contributes {contributions['location risk']:.1f} points.",
        PRIORITY_NOTICE,
    ]
    return score, level, explanation


def _priority_level(score: int) -> PriorityLevel:
    if score <= 30:
        return PriorityLevel.LOW
    if score <= 60:
        return PriorityLevel.MEDIUM
    if score <= 80:
        return PriorityLevel.HIGH
    return PriorityLevel.CRITICAL


def _description_similarity(left: EmergencyReport, request: ReportCreateRequest) -> float:
    existing = f"{left.title} {left.description}".casefold()
    incoming = f"{request.title} {request.description}".casefold()
    return SequenceMatcher(None, existing, incoming).ratio()


def _find_duplicates(request: ReportCreateRequest, reports: list[dict], now: datetime) -> list[str]:
    duplicate_ids: list[str] = []
    for raw_report in reports:
        existing = EmergencyReport.model_validate(raw_report)
        if existing.category != request.category or abs(existing.severity - request.severity) > 1:
            continue
        if existing.status in {ReportStatus.RESOLVED, ReportStatus.REJECTED}:
            continue
        age = abs((now - existing.timestamp).total_seconds())
        if age > timedelta(hours=DUPLICATE_TIME_WINDOW_HOURS).total_seconds():
            continue
        distance_meters = haversine_km(request.latitude, request.longitude, existing.latitude, existing.longitude) * 1_000
        if distance_meters > DUPLICATE_DISTANCE_METERS:
            continue
        if _description_similarity(existing, request) >= DUPLICATE_MIN_DESCRIPTION_SIMILARITY:
            duplicate_ids.append(existing.report_id)
    return duplicate_ids


def list_reports() -> ReportListResponse:
    reports = [EmergencyReport.model_validate(item) for item in REPORTS_STORE.read()]
    reports.sort(key=lambda report: (report.timestamp, report.priority_score), reverse=True)
    return ReportListResponse(reports=reports, count=len(reports), data_label=REPORT_DATA_LABEL)


def get_report(report_id: str) -> EmergencyReport:
    for item in REPORTS_STORE.read():
        if item.get("report_id") == report_id:
            return EmergencyReport.model_validate(item)
    raise ReportNotFoundError("Report not found")


def update_report_processing(report_id: str, **updates) -> EmergencyReport:
    allowed = {
        "risk_assessment",
        "resource_requirements",
        "resource_shortages",
        "allocation_events",
        "event_processing_status",
        "event_processing_error",
    }
    if set(updates) - allowed:
        raise ValueError("Unsupported event processing update")

    def apply(current: list[dict]) -> tuple[list[dict], EmergencyReport]:
        for index, raw_report in enumerate(current):
            if raw_report.get("report_id") != report_id:
                continue
            report = EmergencyReport.model_validate(raw_report)
            changed = EmergencyReport.model_validate({**report.model_dump(mode="python"), **updates})
            current[index] = changed.model_dump(mode="json")
            return current, changed
        raise ReportNotFoundError("Report not found")

    return REPORTS_STORE.update(apply)


def create_report(request: ReportCreateRequest) -> EmergencyReport:
    now = datetime.now(timezone.utc)
    location_risk_score, location_reason = _location_risk(request.latitude, request.longitude)
    score, level, explanation = calculate_priority(
        request, location_risk_score, location_reason
    )
    report_id = f"RPT-{uuid.uuid4().hex[:10].upper()}"

    def append_report(current: list[dict]) -> tuple[list[dict], EmergencyReport]:
        duplicates = _find_duplicates(request, current, now)
        record = EmergencyReport(
            report_id=report_id,
            category=request.category,
            title=request.title.strip(),
            description=request.description.strip(),
            latitude=request.latitude,
            longitude=request.longitude,
            severity=request.severity,
            people_affected=request.people_affected,
            timestamp=now,
            status=ReportStatus.RECEIVED,
            source=request.source,
            priority_score=score,
            priority_level=level,
            priority_explanation=explanation,
            location_risk_score=location_risk_score,
            possible_duplicate=bool(duplicates),
            duplicate_report_ids=duplicates,
            status_history=[ReportStatusEvent(timestamp=now, actor=request.source.value, status=ReportStatus.RECEIVED, reason="Report received")],
            data_label=REPORT_DATA_LABEL,
        )
        return [*current, record.model_dump(mode="json")], record

    return REPORTS_STORE.update(append_report)


def update_report_status(report_id: str, update: ReportStatusUpdate) -> EmergencyReport:
    now = datetime.now(timezone.utc)

    def apply_status_update(current: list[dict]) -> tuple[list[dict], EmergencyReport]:
        for index, raw_report in enumerate(current):
            if raw_report.get("report_id") != report_id:
                continue
            report = EmergencyReport.model_validate(raw_report)
            if update.status not in ALLOWED_STATUS_TRANSITIONS[report.status]:
                raise ReportConflictError(f"Status cannot transition from {report.status.value} to {update.status.value}")
            changed = report.model_copy(update={
                "status": update.status,
                "status_history": [*report.status_history, ReportStatusEvent(timestamp=now, actor=update.actor, status=update.status, reason=update.reason)],
            })
            current[index] = changed.model_dump(mode="json")
            return current, changed
        raise ReportNotFoundError("Report not found")

    return REPORTS_STORE.update(apply_status_update)


def delete_report(report_id: str) -> None:
    def remove(current: list[dict]) -> tuple[list[dict], None]:
        for index, report in enumerate(current):
            if report.get("report_id") == report_id:
                del current[index]
                return current, None
        raise ReportNotFoundError("Report not found")

    REPORTS_STORE.update(remove)
