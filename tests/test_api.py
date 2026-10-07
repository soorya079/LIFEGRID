from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok", "mode": "local"},
    }


def test_local_frontend_origin_is_allowed_by_cors():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_root_and_openapi_docs_are_available():
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_zones_endpoint_returns_synthetic_fixtures():
    response = client.get("/api/v1/zones")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["zones"]) >= 5
    assert "SYNTHETIC DEMO DATA" in body["data"]["data_label"]


def test_risk_api_returns_explanation_and_weighted_details():
    response = client.post(
        "/api/v1/risk/analyze",
        json={
            "rainfall_mm": 300,
            "river_level": "CRITICAL",
            "population_density": 10000,
            "road_accessibility": 10,
            "shelter_capacity": 10,
            "medical_capacity": 15,
            "historical_risk": 95,
        },
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["risk_level"] == "CRITICAL"
    assert len(result["factor_details"]) == 7
    assert "rainfall" in result["explanation"][0].lower()
    assert "increases flood risk" in result["explanation"][0]


def test_invalid_risk_request_returns_structured_validation_error():
    response = client.post(
        "/api/v1/risk/analyze",
        json={"rainfall_mm": -1, "river_level": "EXTREME"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


def test_flood_simulation_named_scenario_returns_demand_and_actions():
    response = client.post(
        "/api/v1/simulation/flood", json={"scenario": "HIGH"}
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["scenario"] == "HIGH"
    assert result["risk"]["risk_level"] == "HIGH"
    assert result["affected_population"] > 0
    assert result["demand"]["water_litres"] > 0
    assert result["recommended_actions"]
    assert "SYNTHETIC DEMO" in result["data_label"]


def test_simulation_requires_complete_custom_inputs():
    response = client.post("/api/v1/simulation/flood", json={"rainfall_mm": 100})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"