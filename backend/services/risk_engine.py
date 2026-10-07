"""Deterministic, explainable urban-flood MVP risk scoring."""

from backend.config import (
    POPULATION_DENSITY_NORMALIZATION_MAX_PER_KM2,
    RAINFALL_NORMALIZATION_MAX_MM,
    RISK_MODEL_VERSION,
    RISK_THRESHOLDS,
    RISK_WEIGHTS,
)
from backend.models.risk import (
    FactorExplanation,
    RiskAnalysisRequest,
    RiskAnalysisResult,
    RiskLevel,
)

MODEL_NOTICE = (
    "MVP decision-support estimate only; not scientifically validated, "
    "an official forecast, or an emergency warning."
)

RIVER_LEVEL_SCORES = {"LOW": 15.0, "MEDIUM": 45.0, "HIGH": 75.0, "CRITICAL": 100.0}


def _bounded_score(value: float, maximum: float) -> float:
    return min(100.0, max(0.0, value / maximum * 100.0))


def _risk_level(score: float) -> RiskLevel:
    for threshold, level in RISK_THRESHOLDS:
        if score <= threshold:
            return RiskLevel(level)
    return RiskLevel.CRITICAL


def _reason(factor: str, level: RiskLevel) -> str:
    reasons = {
        "rainfall": {
            RiskLevel.LOW: "Rainfall is within the model's lower-risk range",
            RiskLevel.MEDIUM: "Moderate rainfall contributes to runoff risk",
            RiskLevel.HIGH: "Heavy rainfall increases flood risk",
            RiskLevel.CRITICAL: "Extreme rainfall strongly increases flood risk",
        },
        "river_level": {
            RiskLevel.LOW: "River level is relatively low",
            RiskLevel.MEDIUM: "Elevated river level contributes to overflow risk",
            RiskLevel.HIGH: "High river level increases overflow probability",
            RiskLevel.CRITICAL: "Critical river level indicates severe overflow potential",
        },
        "population_density": {
            RiskLevel.LOW: "Lower population density limits potential exposure",
            RiskLevel.MEDIUM: "Moderate population density increases potential impact",
            RiskLevel.HIGH: "High population density increases potential impact",
            RiskLevel.CRITICAL: "Very high population density increases potential impact",
        },
        "road_accessibility": {
            RiskLevel.LOW: "Road accessibility supports evacuation and response",
            RiskLevel.MEDIUM: "Partial road constraints may slow response",
            RiskLevel.HIGH: "Low road accessibility increases evacuation difficulty",
            RiskLevel.CRITICAL: "Very low road accessibility severely limits evacuation",
        },
        "shelter_capacity": {
            RiskLevel.LOW: "Shelter capacity appears adequate in this model",
            RiskLevel.MEDIUM: "Shelter capacity may be constrained",
            RiskLevel.HIGH: "Limited shelter capacity increases vulnerability",
            RiskLevel.CRITICAL: "Very limited shelter capacity increases vulnerability",
        },
        "medical_capacity": {
            RiskLevel.LOW: "Medical capacity appears adequate in this model",
            RiskLevel.MEDIUM: "Medical capacity may be constrained",
            RiskLevel.HIGH: "Limited medical capacity increases response risk",
            RiskLevel.CRITICAL: "Very limited medical capacity increases response risk",
        },
        "historical_risk": {
            RiskLevel.LOW: "Historical-risk index is low",
            RiskLevel.MEDIUM: "Historical-risk index adds moderate concern",
            RiskLevel.HIGH: "Elevated historical risk adds concern",
            RiskLevel.CRITICAL: "Very high historical risk adds substantial concern",
        },
    }
    return reasons[factor][level]


def analyze_risk(request: RiskAnalysisRequest) -> RiskAnalysisResult:
    """Score a validated zone input and retain each factor's contribution."""
    factor_inputs: dict[str, tuple[float | str, float]] = {
        "rainfall": (
            request.rainfall_mm,
            _bounded_score(request.rainfall_mm, RAINFALL_NORMALIZATION_MAX_MM),
        ),
        "river_level": (
            request.river_level.value,
            RIVER_LEVEL_SCORES[request.river_level.value],
        ),
        "population_density": (
            request.population_density,
            _bounded_score(
                request.population_density,
                POPULATION_DENSITY_NORMALIZATION_MAX_PER_KM2,
            ),
        ),
        "road_accessibility": (
            request.road_accessibility,
            100.0 - request.road_accessibility,
        ),
        "shelter_capacity": (
            request.shelter_capacity,
            100.0 - request.shelter_capacity,
        ),
        "medical_capacity": (
            request.medical_capacity,
            100.0 - request.medical_capacity,
        ),
        "historical_risk": (request.historical_risk, request.historical_risk),
    }

    details: list[FactorExplanation] = []
    weighted_score = 0.0
    for factor, (input_value, normalized_risk) in factor_inputs.items():
        rating = _risk_level(normalized_risk)
        weight = RISK_WEIGHTS[factor]
        contribution = normalized_risk * weight
        weighted_score += contribution
        details.append(
            FactorExplanation(
                factor=factor,
                input_value=input_value,
                normalized_risk=round(normalized_risk, 2),
                weight=weight,
                contribution=round(contribution, 2),
                rating=rating,
                reason=_reason(factor, rating),
            )
        )

    score = max(0, min(100, round(weighted_score)))
    factors = {detail.factor: detail.rating for detail in details}
    return RiskAnalysisResult(
        risk_score=score,
        risk_level=_risk_level(score),
        factors=factors,
        factor_details=details,
        explanation=[detail.reason for detail in details],
        model_version=RISK_MODEL_VERSION,
        model_notice=MODEL_NOTICE,
    )