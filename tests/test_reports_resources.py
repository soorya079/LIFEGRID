import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.report import ReportCreateRequest
from backend.services import report_service, resource_service
from backend.events.event_bus import LocalEventBus, set_event_bus_for_tests
from backend.events.handlers import register_default_handlers
from backend.events.idempotency import IdempotencyStore
from backend.services.json_store import DataStoreError, JsonFileStore
from backend.services.report_service import calculate_priority, haversine_km

client = TestClient(app)


@pytest.fixture
def isolated_data(tmp_path, monkeypatch, request):
    reports_store = JsonFileStore(tmp_path / "reports.json", [])
    resources_fixture = Path(__file__).parents[1] / "backend" / "data" / "resources.json"
    resources_store = JsonFileStore(tmp_path / "resources.json", [])
    resources_store.write(json.loads(resources_fixture.read_text(encoding="utf-8")))
    allocations_store = JsonFileStore(tmp_path / "allocations.json", [])
    event_store = JsonFileStore(tmp_path / "events.json", [])
    processed_store = JsonFileStore(tmp_path / "processed.json", [])
    failed_store = JsonFileStore(tmp_path / "failed.json", [])
    local_bus = LocalEventBus(
        events_store=event_store,
        failed_store=failed_store,
        idempotency=IdempotencyStore(processed_store),
    )
    register_default_handlers(local_bus)
    set_event_bus_for_tests(local_bus)
    request.addfinalizer(lambda: set_event_bus_for_tests(None))
    monkeypatch.setattr(report_service, "REPORTS_STORE", reports_store)
    monkeypatch.setattr(resource_service, "REPORTS_STORE", reports_store)
    monkeypatch.setattr(resource_service, "RESOURCES_STORE", resources_store)
    monkeypatch.setattr(resource_service, "ALLOCATIONS_STORE", allocations_store)
    return reports_store, resources_store, allocations_store


def valid_report(**overrides):
    values = {
        "category": "FLOOD",
        "title": "Flood water entering homes",
        "description": "Water is entering ground floor homes beside the canal.",
        "latitude": 19.096,
        "longitude": 72.8977,
        "severity": 4,
        "people_affected": 25,
    }
    values.update(overrides)
    return values


def test_report_create_get_list_and_server_fields(isolated_data):
    created_response = client.post("/api/v1/reports", json=valid_report())

    assert created_response.status_code == 201
    created = created_response.json()["data"]
    assert created["report_id"].startswith("RPT-")
    assert created["status"] == "RECEIVED"
    assert created["source"] == "CITIZEN"
    assert created["timestamp"]
    assert created["priority_score"] in range(101)
    assert created["priority_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert created["priority_explanation"]
    assert created["possible_duplicate"] is False

    get_response = client.get(f"/api/v1/reports/{created['report_id']}")
    list_response = client.get("/api/v1/reports")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["report_id"] == created["report_id"]
    assert list_response.json()["data"]["count"] == 1


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"latitude": 91},
        {"longitude": -181},
        {"severity": 0},
        {"people_affected": -2},
        {"category": "TORNADO"},
        {"title": "x"},
        {"source": "UNKNOWN"},
    ],
)
def test_invalid_report_payload_returns_structured_validation_error(
    isolated_data, invalid_fields
):
    response = client.post("/api/v1/reports", json=valid_report(**invalid_fields))

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_priority_is_deterministic_and_medical_beats_other(isolated_data):
    medical = ReportCreateRequest(**valid_report(category="MEDICAL", severity=5))
    other = ReportCreateRequest(**valid_report(category="OTHER", severity=5))

    medical_score, medical_level, explanation = calculate_priority(medical, 70)
    other_score, _, _ = calculate_priority(other, 70)

    assert medical_score > other_score
    assert medical_level in {"HIGH", "CRITICAL"}
    assert any("LIFEGRID MVP decision-support heuristic" in item for item in explanation)
    assert calculate_priority(medical, 70)[0] == medical_score


def test_possible_duplicate_is_flagged_but_both_reports_are_kept(isolated_data):
    first = client.post("/api/v1/reports", json=valid_report()).json()["data"]
    second = client.post(
        "/api/v1/reports",
        json=valid_report(
            title="Flood water entering nearby homes",
            description="Water is entering ground floor homes next to the canal.",
            latitude=19.0962,
            longitude=72.8978,
        ),
    ).json()["data"]

    assert second["possible_duplicate"] is True
    assert first["report_id"] in second["duplicate_report_ids"]
    assert client.get("/api/v1/reports").json()["data"]["count"] == 2


def test_report_status_transition_and_conflict(isolated_data):
    report = client.post("/api/v1/reports", json=valid_report()).json()["data"]
    response = client.patch(
        f"/api/v1/reports/{report['report_id']}/status",
        json={"status": "VALIDATING", "actor": "operator-1", "reason": "Reviewing submitted details"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "VALIDATING"
    assert len(response.json()["data"]["status_history"]) == 2

    conflict = client.patch(
        f"/api/v1/reports/{report['report_id']}/status",
        json={"status": "RESOLVED", "reason": "Invalid direct transition"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CONFLICT"


def test_report_not_found_and_explicit_delete(isolated_data):
    missing = client.get("/api/v1/reports/RPT-MISSING")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"

    report = client.post("/api/v1/reports", json=valid_report()).json()["data"]
    deleted = client.delete(f"/api/v1/reports/{report['report_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
    assert client.get("/api/v1/reports").json()["data"]["count"] == 0


def test_json_store_tolerates_missing_and_empty_files(tmp_path):
    store = JsonFileStore(tmp_path / "missing.json", [])
    assert store.read() == []
    store.path.write_text("  ", encoding="utf-8")
    assert store.read() == []


def test_corrupt_json_returns_structured_error_without_stopping_api(
    isolated_data, monkeypatch, tmp_path
):
    corrupt_store = JsonFileStore(tmp_path / "corrupt.json", [])
    corrupt_store.path.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(report_service, "REPORTS_STORE", corrupt_store)
    monkeypatch.setattr(resource_service, "REPORTS_STORE", corrupt_store)

    response = client.get("/api/v1/reports")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "DATA_STORE_ERROR"
    assert client.get("/health").status_code == 200
    with pytest.raises(DataStoreError):
        corrupt_store.read()


def test_haversine_distance_uses_geographic_distance():
    assert haversine_km(0, 0, 0, 0) == 0
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.2, abs=0.3)


def test_resource_list_requirements_summary_and_shortages(isolated_data):
    resource_list = client.get("/api/v1/resources")
    requirements = client.post(
        "/api/v1/resources/requirements", json={"affected_population": 100}
    )
    summary = client.get("/api/v1/resources/summary")
    shortages = client.get("/api/v1/resources/shortages")

    assert resource_list.status_code == 200
    assert len(resource_list.json()["data"]["resources"]) >= 10
    assert "SYNTHETIC DEMO DATA" in resource_list.json()["data"]["data_label"]
    assert next(item for item in resource_list.json()["data"]["resources"] if item["resource_id"] == "RES-WAT-A")["status"] == "AVAILABLE"
    assert requirements.json()["data"] == {
        "water_required": 300,
        "food_required": 100,
        "medicine_required": 5,
        "shelter_required": 30,
        "ambulances_required": 1,
        "assumptions": {
            "water_litres_per_person": 3.0,
            "food_kits_per_person": 1.0,
            "medicine_units_per_person": 0.05,
            "shelter_spaces_per_person": 0.3,
            "ambulances_per_person": 0.0004,
        },
        "formula": "Each quantity = ceil(affected_population x configured per-person assumption).",
    }
    assert summary.status_code == 200
    assert summary.json()["data"]["open_report_count"] == 0
    assert len(summary.json()["data"]["resources"]) == 5
    assert shortages.status_code == 200
    assert shortages.json()["data"]["shortages"] == []
    assert shortages.json()["data"]["assumptions"]["water_litres_per_person"] == 3
    assert shortages.json()["data"]["formula"]


def test_resource_matching_is_nearest_first_and_reports_shortage(isolated_data):
    response = client.post(
        "/api/v1/resources/match",
        json={
            "latitude": 19.096,
            "longitude": 72.8977,
            "affected_population": 30_000,
            "risk_level": "CRITICAL",
            "resource_type": "WATER",
        },
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["method"] == "LIFEGRID MVP resource matching heuristic"
    assert result["required_quantity"] == 90_000
    assert result["recommendations"][0]["resource_id"] == "RES-WAT-B"
    assert result["recommendations"][0]["recommended_quantity"] > 0
    assert result["shortage_quantity"] > 0
    assert all(item["distance_km"] >= 0 and item["reason"] for item in result["recommendations"])


def test_match_with_report_uses_persisted_report_context(isolated_data):
    report = client.post("/api/v1/reports", json=valid_report(people_affected=50)).json()["data"]
    result = client.post(
        "/api/v1/resources/match",
        json={
            "report_id": report["report_id"],
            "latitude": -20,
            "longitude": -20,
            "affected_population": 1,
            "risk_level": "LOW",
            "resource_type": "WATER",
        },
    ).json()["data"]

    assert result["report_id"] == report["report_id"]
    assert result["required_quantity"] == 150


def test_allocation_updates_derived_inventory_and_history(isolated_data):
    report = client.post("/api/v1/reports", json=valid_report()).json()["data"]
    before = client.get("/api/v1/resources/RES-WAT-A").json()["data"]
    response = client.post(
        "/api/v1/resources/allocate",
        json={
            "resource_id": "RES-WAT-A",
            "quantity": 1200,
            "report_id": report["report_id"],
            "reason": "Stage water for the reported flood zone",
        },
    )
    after = client.get("/api/v1/resources/RES-WAT-A").json()["data"]
    history = client.get("/api/v1/resources/allocations").json()["data"]

    assert response.status_code == 201
    assert response.json()["data"]["remaining_inventory"] == before["available_quantity"] - 1200
    assert response.json()["data"]["shortage_quantity"] == 0
    assert response.json()["data"]["assumptions"]["water_litres_per_person"] == 3
    assert response.json()["data"]["shortage_formula"]
    assert after["available_quantity"] == before["available_quantity"] - 1200
    assert after["status"] == "LIMITED"
    assert history["count"] == 1
    assert history["allocations"][0]["report_id"] == report["report_id"]


def test_allocation_rejects_overdraw_and_unavailable_inventory(isolated_data):
    too_much = client.post(
        "/api/v1/resources/allocate",
        json={"resource_id": "RES-WAT-A", "quantity": 42_001, "reason": "Overdraw attempt"},
    )
    assert too_much.status_code == 409
    assert too_much.json()["error"]["code"] == "CONFLICT"
    assert client.get("/api/v1/resources/RES-WAT-A").json()["data"]["available_quantity"] == 42_000

    resources = resource_service.RESOURCES_STORE.read()
    resources[0]["status"] = "UNAVAILABLE"
    resource_service.RESOURCES_STORE.write(resources)
    unavailable = client.post(
        "/api/v1/resources/allocate",
        json={"resource_id": "RES-WAT-A", "quantity": 1, "reason": "Unavailable check"},
    )
    assert unavailable.status_code == 409


def test_allocation_validation_and_unknown_resource_errors(isolated_data):
    invalid = client.post(
        "/api/v1/resources/allocate",
        json={"resource_id": "RES-WAT-A", "quantity": -1, "reason": "Invalid amount"},
    )
    missing = client.post(
        "/api/v1/resources/allocate",
        json={"resource_id": "RES-UNKNOWN", "quantity": 1, "reason": "Unknown resource"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
