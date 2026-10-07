"""Synthetic resource requirements, geographic matching, and safe allocation."""

import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.config import RESOURCE_DEMAND_ASSUMPTIONS, RESOURCE_SEARCH_RADIUS_KM
from backend.models.report import EmergencyReport, ReportStatus
from backend.models.resource import (
    AllocationRecord,
    AllocationRequest,
    ResourceMatchRequest,
    ResourceMatchResult,
    ResourceRecord,
    ResourceRecommendation,
    ResourceRequirements,
    ResourceStatus,
    ResourceSummary,
    ResourceType,
    ResourceTypeSummary,
    ShortageSummary,
)
from backend.services.json_store import DataStoreError, JsonFileStore, STORE_LOCK
from backend.services.report_service import REPORTS_STORE, ReportNotFoundError, get_report, haversine_km

DATA_DIR = Path(os.getenv("LIFEGRID_DATA_DIR", Path(__file__).parents[1] / "data"))
RESOURCES_STORE = JsonFileStore(DATA_DIR / "resources.json", [])
ALLOCATIONS_STORE = JsonFileStore(DATA_DIR / "allocations.json", [])
RESOURCE_DATA_LABEL = "SYNTHETIC DEMO DATA - inventory values are fictional, not operational stock."
MATCHING_METHOD = "LIFEGRID MVP resource matching heuristic"
MATCHING_NOTICE = "Nearest-first recommendations only; not globally optimal. Human confirmation required."

RESOURCE_UNITS = {
    ResourceType.WATER: "litres",
    ResourceType.FOOD: "kits",
    ResourceType.MEDICINE: "units",
    ResourceType.SHELTER: "spaces",
    ResourceType.AMBULANCE: "vehicles",
}
DEMAND_FIELDS = {
    ResourceType.WATER: "water_required",
    ResourceType.FOOD: "food_required",
    ResourceType.MEDICINE: "medicine_required",
    ResourceType.SHELTER: "shelter_required",
    ResourceType.AMBULANCE: "ambulances_required",
}


class ResourceNotFoundError(LookupError):
    pass


class AllocationConflictError(ValueError):
    pass


def calculate_requirements(affected_population: int) -> ResourceRequirements:
    if affected_population < 0:
        raise ValueError("affected_population must be non-negative")
    return ResourceRequirements(
        water_required=math.ceil(affected_population * RESOURCE_DEMAND_ASSUMPTIONS["water_litres_per_person"]),
        food_required=math.ceil(affected_population * RESOURCE_DEMAND_ASSUMPTIONS["food_kits_per_person"]),
        medicine_required=math.ceil(affected_population * RESOURCE_DEMAND_ASSUMPTIONS["medicine_units_per_person"]),
        shelter_required=math.ceil(affected_population * RESOURCE_DEMAND_ASSUMPTIONS["shelter_spaces_per_person"]),
        ambulances_required=math.ceil(affected_population * RESOURCE_DEMAND_ASSUMPTIONS["ambulances_per_person"]),
        assumptions=dict(RESOURCE_DEMAND_ASSUMPTIONS),
        formula="Each quantity = ceil(affected_population x configured per-person assumption).",
    )


def _raw_resources() -> list[ResourceRecord]:
    try:
        raw = RESOURCES_STORE.read()
        return [ResourceRecord.model_validate(item) for item in raw]
    except ValueError as error:
        raise DataStoreError("Resource data failed schema validation") from error


def _allocations() -> list[AllocationRecord]:
    try:
        raw = ALLOCATIONS_STORE.read()
        return [AllocationRecord.model_validate(item) for item in raw]
    except ValueError as error:
        raise DataStoreError("Allocation data failed schema validation") from error


def _effective_resources(resources: list[ResourceRecord], allocations: list[AllocationRecord]) -> list[ResourceRecord]:
    spent: dict[str, float] = {}
    for allocation in allocations:
        spent[allocation.resource_id] = spent.get(allocation.resource_id, 0) + allocation.quantity
    effective: list[ResourceRecord] = []
    for resource in resources:
        remaining = max(0.0, round(resource.available_quantity - spent.get(resource.resource_id, 0), 6))
        if resource.status == ResourceStatus.UNAVAILABLE:
            status = ResourceStatus.UNAVAILABLE
        elif remaining <= 0:
            status = ResourceStatus.EXHAUSTED
        elif spent.get(resource.resource_id, 0) > 0:
            status = ResourceStatus.LIMITED
        else:
            status = resource.status
        effective.append(resource.model_copy(update={"available_quantity": remaining, "status": status}))
    return effective


def list_resources() -> tuple[list[ResourceRecord], str]:
    with STORE_LOCK:
        resources = _effective_resources(_raw_resources(), _allocations())
    return resources, RESOURCE_DATA_LABEL


def get_resource(resource_id: str) -> ResourceRecord:
    resources, _ = list_resources()
    for resource in resources:
        if resource.resource_id == resource_id:
            return resource
    raise ResourceNotFoundError("Resource not found")


def _active_reports() -> list[EmergencyReport]:
    try:
        reports = [EmergencyReport.model_validate(item) for item in REPORTS_STORE.read()]
    except ValueError as error:
        raise DataStoreError("Report data failed schema validation") from error
    return [report for report in reports if report.status not in {ReportStatus.RESOLVED, ReportStatus.REJECTED}]


def _required_totals(reports: list[EmergencyReport]) -> ResourceRequirements:
    requirements = [calculate_requirements(report.people_affected) for report in reports]
    return ResourceRequirements(
        water_required=sum(item.water_required for item in requirements),
        food_required=sum(item.food_required for item in requirements),
        medicine_required=sum(item.medicine_required for item in requirements),
        shelter_required=sum(item.shelter_required for item in requirements),
        ambulances_required=sum(item.ambulances_required for item in requirements),
        assumptions=dict(RESOURCE_DEMAND_ASSUMPTIONS),
        formula="Sum of per-report ceil(population x configured assumption); active reports only.",
    )


def _type_summaries(reports: list[EmergencyReport], resources: list[ResourceRecord]) -> list[ResourceTypeSummary]:
    requirements = _required_totals(reports)
    summaries = []
    for resource_type in ResourceType:
        required = float(getattr(requirements, DEMAND_FIELDS[resource_type]))
        matching = [resource for resource in resources if resource.type == resource_type]
        available = sum(
            resource.available_quantity
            for resource in matching
            if resource.status in {ResourceStatus.AVAILABLE, ResourceStatus.LIMITED}
        )
        coverage = min(100.0, round(available / required * 100, 1)) if required else (100.0 if available else 0.0)
        summaries.append(ResourceTypeSummary(
            type=resource_type,
            unit=RESOURCE_UNITS[resource_type],
            required=required,
            available=round(available, 3),
            coverage_percent=coverage,
            shortage=round(max(0.0, required - available), 3),
            resource_count=len(matching),
        ))
    return summaries


def resource_summary() -> ResourceSummary:
    with STORE_LOCK:
        reports = _active_reports()
        resources = _effective_resources(_raw_resources(), _allocations())
    return ResourceSummary(
        requirements=_required_totals(reports),
        resources=_type_summaries(reports, resources),
        open_report_count=len(reports),
        data_label=RESOURCE_DATA_LABEL,
    )


def resource_shortages() -> ShortageSummary:
    summary = resource_summary()
    return ShortageSummary(
        shortages=[item for item in summary.resources if item.shortage > 0],
        assumptions=dict(RESOURCE_DEMAND_ASSUMPTIONS),
        formula="shortage = max(0, required - available); required uses ceil(population x configured per-person assumption)",
        data_label=RESOURCE_DATA_LABEL,
    )


def report_resource_shortages(report_id: str) -> list[ResourceTypeSummary]:
    report = get_report(report_id)
    with STORE_LOCK:
        resources = _effective_resources(_raw_resources(), _allocations())
    return [
        summary
        for summary in _type_summaries([report], resources)
        if summary.shortage > 0
    ]


def match_resources(request: ResourceMatchRequest) -> ResourceMatchResult:
    if request.report_id:
        report = next(
            (item for item in _active_reports() if item.report_id == request.report_id),
            None,
        )
        if report is None:
            raise ReportNotFoundError("Active report not found")
        request = request.model_copy(update={
            "latitude": report.latitude,
            "longitude": report.longitude,
            "affected_population": max(1, report.people_affected),
            "risk_level": report.priority_level,
        })
    requirements = calculate_requirements(request.affected_population)
    required = float(getattr(requirements, DEMAND_FIELDS[request.resource_type]))
    radius = RESOURCE_SEARCH_RADIUS_KM[request.risk_level.value]
    resources, _ = list_resources()
    candidates = []
    for resource in resources:
        if resource.type != request.resource_type or resource.status not in {ResourceStatus.AVAILABLE, ResourceStatus.LIMITED}:
            continue
        distance = haversine_km(request.latitude, request.longitude, resource.latitude, resource.longitude)
        if distance <= radius:
            candidates.append((distance, resource))
    candidates.sort(key=lambda item: (item[0], -item[1].available_quantity, item[1].resource_id))

    remaining = required
    recommendations = []
    for distance, resource in candidates:
        if remaining <= 0:
            break
        recommended = min(remaining, resource.available_quantity)
        if recommended <= 0:
            continue
        recommendations.append(ResourceRecommendation(
            resource_id=resource.resource_id,
            name=resource.name,
            type=resource.type,
            unit=resource.unit,
            latitude=resource.latitude,
            longitude=resource.longitude,
            distance_km=round(distance, 2),
            available_quantity=resource.available_quantity,
            required_quantity=required,
            recommended_quantity=round(recommended, 3),
            reason=f"Within {radius:g} km; nearest-first selection with {resource.available_quantity:g} {resource.unit} available and {recommended:g} recommended.",
        ))
        remaining = max(0.0, remaining - recommended)
    recommended_total = round(required - remaining, 3)
    return ResourceMatchResult(
        report_id=request.report_id,
        resource_type=request.resource_type,
        risk_level=request.risk_level,
        required_quantity=required,
        recommended_quantity=recommended_total,
        shortage_quantity=round(remaining, 3),
        recommendations=recommendations,
        assumptions=dict(RESOURCE_DEMAND_ASSUMPTIONS),
        method=MATCHING_METHOD,
        notice=MATCHING_NOTICE,
    )


def allocation_history() -> list[AllocationRecord]:
    allocations = _allocations()
    allocations.sort(key=lambda allocation: allocation.timestamp, reverse=True)
    return allocations


def allocate_resource(request: AllocationRequest) -> AllocationRecord:
    with STORE_LOCK:
        prior_allocations = _allocations()
        resources = _effective_resources(_raw_resources(), prior_allocations)
        resource = next((item for item in resources if item.resource_id == request.resource_id), None)
        if resource is None:
            raise ResourceNotFoundError("Resource not found")
        if resource.status in {ResourceStatus.UNAVAILABLE, ResourceStatus.EXHAUSTED}:
            raise AllocationConflictError(f"Resource is {resource.status.value.lower()} and cannot be allocated")
        if request.quantity > resource.available_quantity:
            raise AllocationConflictError(f"Requested quantity exceeds available inventory ({resource.available_quantity:g} {resource.unit})")
        if request.report_id:
            report = next((item for item in _active_reports() if item.report_id == request.report_id), None)
            if report is None:
                raise ReportNotFoundError("Active report not found")
            required = float(getattr(calculate_requirements(report.people_affected), DEMAND_FIELDS[resource.type]))
            allocated_before = sum(
                item.quantity
                for item in prior_allocations
                if item.report_id == request.report_id and item.resource_type == resource.type
            )
        else:
            aggregate_requirements = _required_totals(_active_reports())
            required = float(getattr(aggregate_requirements, DEMAND_FIELDS[resource.type]))
            allocated_before = sum(
                item.quantity for item in prior_allocations if item.resource_type == resource.type
            )

        remaining = round(resource.available_quantity - request.quantity, 6)
        record = AllocationRecord(
            allocation_id=f"ALC-{uuid.uuid4().hex[:10].upper()}",
            resource_id=resource.resource_id,
            resource_name=resource.name,
            resource_type=resource.type,
            quantity=request.quantity,
            unit=resource.unit,
            report_id=request.report_id,
            actor=request.actor,
            reason=request.reason,
            timestamp=datetime.now(timezone.utc),
            remaining_inventory=remaining,
            shortage_quantity=round(max(0.0, required - allocated_before - request.quantity), 3),
            assumptions=dict(RESOURCE_DEMAND_ASSUMPTIONS),
            shortage_formula="max(0, required for linked report or active reports - prior allocations - this allocation)",
        )
        ALLOCATIONS_STORE.update(lambda current: ([*current, record.model_dump(mode="json")], record))
        return record