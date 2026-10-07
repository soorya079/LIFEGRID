import pytest
from pydantic import ValidationError

from backend.models.risk import RiskAnalysisRequest, RiskLevel
from backend.services.risk_engine import analyze_risk


@pytest.mark.parametrize(
    ("inputs", "expected_level"),
    [
        (
            {
                "rainfall_mm": 25,
                "river_level": "LOW",
                "population_density": 900,
                "road_accessibility": 90,
                "shelter_capacity": 85,
                "medical_capacity": 90,
                "historical_risk": 10,
            },
            RiskLevel.LOW,
        ),
        (
            {
                "rainfall_mm": 100,
                "river_level": "MEDIUM",
                "population_density": 5000,
                "road_accessibility": 60,
                "shelter_capacity": 60,
                "medical_capacity": 70,
                "historical_risk": 45,
            },
            RiskLevel.MEDIUM,
        ),
        (
            {
                "rainfall_mm": 210,
                "river_level": "HIGH",
                "population_density": 8000,
                "road_accessibility": 40,
                "shelter_capacity": 35,
                "medical_capacity": 40,
                "historical_risk": 70,
            },
            RiskLevel.HIGH,
        ),
        (
            {
                "rainfall_mm": 300,
                "river_level": "CRITICAL",
                "population_density": 10000,
                "road_accessibility": 10,
                "shelter_capacity": 10,
                "medical_capacity": 15,
                "historical_risk": 95,
            },
            RiskLevel.CRITICAL,
        ),
    ],
)
def test_risk_engine_returns_expected_scenario_level(inputs, expected_level):
    result = analyze_risk(RiskAnalysisRequest(**inputs))

    assert result.risk_level == expected_level
    assert 0 <= result.risk_score <= 100
    assert len(result.factors) == 7
    assert len(result.factor_details) == 7
    assert len(result.explanation) == 7
    assert sum(detail.weight for detail in result.factor_details) == pytest.approx(1.0)
    assert round(sum(detail.contribution for detail in result.factor_details)) == (
        result.risk_score
    )


def test_invalid_risk_input_is_rejected():
    with pytest.raises(ValidationError):
        RiskAnalysisRequest(
            rainfall_mm=501,
            river_level="LOW",
            population_density=100,
            road_accessibility=50,
            shelter_capacity=50,
            medical_capacity=50,
            historical_risk=50,
        )


def test_capacity_and_accessibility_are_inverted_for_risk():
    result = analyze_risk(
        RiskAnalysisRequest(
            rainfall_mm=0,
            river_level="LOW",
            population_density=0,
            road_accessibility=0,
            shelter_capacity=0,
            medical_capacity=0,
            historical_risk=0,
        )
    )

    assert result.factors["road_accessibility"] == RiskLevel.CRITICAL
    assert result.factors["shelter_capacity"] == RiskLevel.CRITICAL
    assert result.factors["medical_capacity"] == RiskLevel.CRITICAL