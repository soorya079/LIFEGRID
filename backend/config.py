"""Versioned, explainable MVP model configuration."""

RISK_MODEL_VERSION = "flood-mvp-v1"

# Weights sum to 1.00. Inputs are converted to 0-100 risk-oriented values.
RISK_WEIGHTS: dict[str, float] = {
    "rainfall": 0.25,
    "river_level": 0.20,
    "population_density": 0.15,
    "road_accessibility": 0.10,
    "shelter_capacity": 0.10,
    "medical_capacity": 0.10,
    "historical_risk": 0.10,
}

RAINFALL_NORMALIZATION_MAX_MM = 300.0
POPULATION_DENSITY_NORMALIZATION_MAX_PER_KM2 = 10_000.0

RISK_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (30, "LOW"),
    (60, "MEDIUM"),
    (80, "HIGH"),
    (100, "CRITICAL"),
)

DEFAULT_DEMAND_ASSUMPTIONS = {
    "water_litres_per_person": 3.0,
    "food_kits_per_person": 1.0,
    "medical_units_per_person": 0.05,
    "shelter_spaces_per_person": 0.30,
}

AFFECTED_POPULATION_RATIO_PER_RISK_POINT = 0.005
MAX_AFFECTED_POPULATION_RATIO = 0.50

RESOURCE_DEMAND_ASSUMPTIONS = {
    "water_litres_per_person": 3.0,
    "food_kits_per_person": 1.0,
    "medicine_units_per_person": 0.05,
    "shelter_spaces_per_person": 0.30,
    "ambulances_per_person": 1 / 2_500,
}

PRIORITY_WEIGHTS = {
    "severity": 0.40,
    "people_affected": 0.25,
    "category_urgency": 0.20,
    "location_risk": 0.15,
}
PRIORITY_POPULATION_NORMALIZATION_MAX = 1_000
CATEGORY_URGENCY_SCORES = {
    "FLOOD": 90,
    "ROAD_BLOCK": 70,
    "MEDICAL": 100,
    "SHELTER": 75,
    "FOOD": 60,
    "WATER": 65,
    "FIRE": 95,
    "OTHER": 45,
}

DUPLICATE_DISTANCE_METERS = 500
DUPLICATE_TIME_WINDOW_HOURS = 6
DUPLICATE_MIN_DESCRIPTION_SIMILARITY = 0.68
RESOURCE_SEARCH_RADIUS_KM = {
    "LOW": 100.0,
    "MEDIUM": 150.0,
    "HIGH": 200.0,
    "CRITICAL": 250.0,
}
EARTH_RADIUS_KM = 6_371.0088