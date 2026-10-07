"""Transparent, configurable resource-demand estimates."""

from math import ceil

from backend.config import DEFAULT_DEMAND_ASSUMPTIONS
from backend.models.risk import DemandAssumptions, DemandEstimate

DEMAND_NOTICE = (
    "Synthetic MVP planning estimate, not an official or medically validated requirement."
)


def calculate_demand(
    affected_population: int,
    assumptions: DemandAssumptions | None = None,
) -> DemandEstimate:
    """Estimate daily resource quantities using explicit per-person assumptions."""
    if affected_population < 0:
        raise ValueError("affected_population must be non-negative")

    selected = assumptions or DemandAssumptions(**DEFAULT_DEMAND_ASSUMPTIONS)
    return DemandEstimate(
        affected_population=affected_population,
        water_litres=round(
            affected_population * selected.water_litres_per_person, 2
        ),
        food_kits=ceil(affected_population * selected.food_kits_per_person),
        medical_units=ceil(affected_population * selected.medical_units_per_person),
        shelter_spaces=ceil(affected_population * selected.shelter_spaces_per_person),
        assumptions=selected,
        notice=DEMAND_NOTICE,
    )