"""Focused synthetic tests for the Phase 6 event pipeline."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from backend.events.event_bus import LocalEventBus, set_event_bus_for_tests
from backend.events.event_models import DomainEvent, EventType
from backend.events.handlers import register_default_handlers
from backend.events.idempotency import IdempotencyStore
from backend.main import app
from backend.services import report_service, resource_service
from backend.services.json_store import JsonFileStore


@pytest.fixture
def isolated_event_app(tmp_path, monkeypatch):
    reports = JsonFileStore(tmp_path / "reports.json", [])
    resources = JsonFileStore(tmp_path / "resources.json", [])
    fixture = Path(__file__).parents[1] / "backend" / "data" / "resources.json"
    resources.write(json.loads(fixture.read_text(encoding="utf-8")))
    allocations = JsonFileStore(tmp_path / "allocations.json", [])
    events = JsonFileStore(tmp_path / "events.json", [])
    processed = JsonFileStore(tmp_path / "processed.json", [])
    failures = JsonFileStore(tmp_path / "failed.json", [])
    bus = LocalEventBus(events, failures, IdempotencyStore(processed))
    register_default_handlers(bus)
    monkeypatch.setattr(report_service, "REPORTS_STORE", reports)
    monkeypatch.setattr(resource_service, "REPORTS_STORE", reports)
    monkeypatch.setattr(resource_service, "RESOURCES_STORE", resources)
    monkeypatch.setattr(resource_service, "ALLOCATIONS_STORE", allocations)
    set_event_bus_for_tests(bus)
    yield TestClient(app), bus, reports, processed, failures
    set_event_bus_for_tests(None)


def test_event_schema_validation_and_utc_serialization():
    event = DomainEvent(
        event_type=EventType.REPORT_CREATED,
        source="lifegrid.test",
        timestamp=datetime.fromisoformat("2026-01-02T03:04:05+05:30"),
        payload={"synthetic": True},
    )
    encoded = event.model_dump(mode="json")
    assert encoded["timestamp"].endswith("Z")
    assert DomainEvent.model_validate_json(json.dumps(encoded)).event_id == event.event_id
    with pytest.raises(ValidationError):
        DomainEvent(event_type="NOT_AN_EVENT", source="test")
    with pytest.raises(ValidationError):
        DomainEvent(event_type=EventType.REPORT_CREATED, source="test", timestamp=datetime(2026, 1, 1))


def test_report_creation_drives_risk_resource_and_shortage_chain(isolated_event_app):
    client, bus, reports, processed, _ = isolated_event_app
    response = client.post("/api/v1/reports", json={
        "category": "FLOOD", "title": "Synthetic flood test", "description": "Synthetic water impact test area.",
        "latitude": 19.096, "longitude": 72.8977, "severity": 5, "people_affected": 100000,
    })
    assert response.status_code == 201
    report_id = response.json()["data"]["report_id"]
    stored = json.loads(reports.path.read_text(encoding="utf-8"))[0]
    assert stored["risk_assessment"]
    assert stored["resource_requirements"]["water_required"] == 300000
    assert stored["event_processing_status"] == "SHORTAGE_DETECTED"
    assert stored["resource_shortages"]
    assert [item["event_type"] for item in bus.events_store.read()] == [
        "REPORT_CREATED", "RISK_ASSESSED", "RESOURCE_SHORTAGE"
    ]
    history = bus.events_store.read()
    assert history[1]["event_id"] == f"{history[0]['event_id']}:RISK_ASSESSED"
    assert history[2]["event_id"] == f"{history[1]['event_id']}:RESOURCE_SHORTAGE"
    assert all(item["event_id"] in {row["event_id"] for row in history} for item in processed.read())
    assert report_id == stored["report_id"]


def test_duplicate_delivery_is_idempotent(isolated_event_app):
    client, bus, reports, processed, _ = isolated_event_app
    result = client.post("/api/v1/reports", json={
        "category": "FLOOD", "title": "Duplicate event report", "description": "Synthetic duplicate test area.",
        "latitude": 19.096, "longitude": 72.8977, "severity": 4, "people_affected": 10,
    })
    report_id = result.json()["data"]["report_id"]
    event = DomainEvent.model_validate(bus.events_store.read()[0])
    before = len(processed.read())
    duplicate = bus.publish(event)
    assert duplicate.accepted
    assert duplicate.handlers[0].already_processed
    assert len(processed.read()) == before
    assert len([row for row in reports.read() if row["report_id"] == report_id]) == 1
    assert len([row for row in bus.events_store.read() if row["event_id"] == event.event_id]) == 1


def test_failed_handler_is_logged_and_retry_result_reported(tmp_path):
    failures = JsonFileStore(tmp_path / "failures.json", [])
    bus = LocalEventBus(JsonFileStore(tmp_path / "events.json", []), failures,
                        IdempotencyStore(JsonFileStore(tmp_path / "processed.json", [])), max_attempts=1)
    bus.subscribe(EventType.REPORT_VERIFIED, "BrokenHandler", lambda _event, _bus: 1 / 0)
    event = DomainEvent(event_type=EventType.REPORT_VERIFIED, source="lifegrid.test")
    result = bus.publish(event)
    assert not result.accepted
    assert not result.handlers[0].success
    assert result.handlers[0].attempts == 1
    assert failures.read()[0]["event_id"] == event.event_id
    assert "ZeroDivisionError" in failures.read()[0]["error"]


def test_status_and_allocation_operations_emit_events(isolated_event_app):
    client, bus, _reports, _processed, _failures = isolated_event_app
    created = client.post("/api/v1/reports", json={
        "category": "FLOOD", "title": "Status and allocation", "description": "Synthetic event flow test.",
        "latitude": 19.096, "longitude": 72.8977, "severity": 3, "people_affected": 10,
    }).json()["data"]
    report_id = created["report_id"]
    allocation = client.post("/api/v1/resources/allocate", json={
        "resource_id": "RES-WAT-A", "quantity": 1, "report_id": report_id, "reason": "Synthetic allocation",
    })
    assert allocation.status_code == 201
    for status, reason in [("VALIDATING", "Initial review"), ("VERIFIED", "Synthetic verification"),
                           ("DISPATCHED", "Synthetic dispatch"), ("RESOLVED", "Synthetic resolution")]:
        assert client.patch(f"/api/v1/reports/{report_id}/status", json={"status": status, "reason": reason}).status_code == 200
    types = [row["event_type"] for row in bus.events_store.read()]
    assert "REPORT_VERIFIED" in types
    assert "INCIDENT_RESOLVED" in types
    assert "RESOURCE_ALLOCATED" in types
