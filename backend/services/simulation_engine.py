"""Flood simulation built from the deterministic risk and demand services."""

from math import ceil

from backend.config import (
    AFFECTED_POPULATION_RATIO_PER_RISK_POINT,
    MAX_AFFECTED_POPULATION_RATIO,
)
from backend.models.risk import (
    FloodSimulationRequest,
    RiskAnalysisRequest,
    RiskLevel,
    SimulationResult,
)
from backend.services.demand_engine import calculate_demand
from backend.services.risk_engine import analyze_risk

SIMULATION_DATA_LABEL = "SYNTHETIC DEMO SIMULATION - not a live or official forecast."

SCENARIOS: dict[str, dict[str, object]] = {
    "LOW": {
        "total_population": 8_000,
        "rainfall_mm": 25,
        "river_level": "LOW",
        "population_density": 900,
        "road_accessibility": 90,
        "shelter_capacity": 85,
        "medical_capacity": 90,
        "historical_risk": 10,
    },
    "MEDIUM": {
        "total_population": 12_000,
        "rainfall_mm": 100,
        "river_level": "MEDIUM",
        "population_density": 5_000,
        "road_accessibility": 60,
        "shelter_capacity": 60,
        "medical_capacity": 70,
        "historical_risk": 45,
    },
    "HIGH": {
        "total_population": 18_000,
        "rainfall_mm": 210,
        "river_level": "HIGH",
        "population_density": 8_000,
        "road_accessibility": 40,
        "shelter_capacity": 35,
        "medical_capacity": 40,
        "historical_risk": 70,
    },
    "CRITICAL": {
        "total_population": 24_000,
        "rainfall_mm": 300,
        "river_level": "CRITICAL",
        "population_density": 10_000,
        "road_accessibility": 10,
        "shelter_capacity": 10,
        "medical_capacity": 15,
        "historical_risk": 95,
    },
}

ACTION_PLANS: dict[RiskLevel, list[str]] = {
    RiskLevel.LOW: [
        "Continue monitoring rainfall and river-level inputs",
        "Confirm zone contact and shelter information is current",
    ],
    RiskLevel.MEDIUM: [
        "Prepare designated shelters and verify current capacity",
        "Inspect known drainage and access constraints",
        "Ask the coordinator to review updated conditions",
    ],
    RiskLevel.HIGH: [
        "Ask the emergency coordinator to review early-action options",
        "Pre-position available water and essential supplies near the zone",
        "Verify shelter and medical capacity before issuing instructions",
        "Monitor road reports and official weather guidance",
    ],
    RiskLevel.CRITICAL: [
        "Escalate the synthetic risk result for immediate human review",
        "Coordinate shelter and medical readiness with responsible operators",
        "Review official evacuation guidance and accessible routes",
        "Prioritize resource staging while checking live conditions",
    ],
}


def _analysis_request(values: dict[str, object]) -> RiskAnalysisRequest:
    return RiskAnalysisRequest.model_validate(values)


def simulate_flood(request: FloodSimulationRequest) -> SimulationResult:
    """Run a named synthetic scenario or explicit user-provided flood inputs."""
    if request.scenario is not None:
        values = dict(SCENARIOS[request.scenario])
        if request.total_population is not None:
            values["total_population"] = request.total_population
        scenario_name = request.scenario
    else:
        values = request.model_dump(exclude_none=True)
        scenario_name = "CUSTOM"

    total_population = int(values.pop("total_population"))
    risk = analyze_risk(_analysis_request(values))
    affected_ratio = min(
        MAX_AFFECTED_POPULATION_RATIO,
        risk.risk_score * AFFECTED_POPULATION_RATIO_PER_RISK_POINT,
    )
    affected_population = min(
        total_population,
        ceil(total_population * affected_ratio),
    )
    demand = calculate_demand(affected_population)
    return SimulationResult(
        scenario=scenario_name,
        risk=risk,
        affected_population=affected_population,
        demand=demand,
        recommended_actions=ACTION_PLANS[risk.risk_level],
        assumptions=[
            "Affected population = total population x min(risk score x 0.005, 0.50), rounded up.",
            "Demand is estimated for one day using the included per-person assumptions.",
            "Named scenario inputs and all resulting values are synthetic demo data.",
        ],
        data_label=SIMULATION_DATA_LABEL,
    )