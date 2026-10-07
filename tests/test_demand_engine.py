import pytest
from pydantic import ValidationError

from backend.models.risk import DemandAssumptions
from backend.services.demand_engine import calculate_demand


def test_default_demand_calculations_include_assumptions():
    result = calculate_demand(100)

    assert result.water_litres == 300
    assert result.food_kits == 100
    assert result.medical_units == 5
    assert result.shelter_spaces == 30
    assert result.assumptions.water_litres_per_person == 3
    assert "not an official" in result.notice


def test_custom_demand_assumptions_are_applied_and_whole_units_rounded_up():
    assumptions = DemandAssumptions(
        water_litres_per_person=2.5,
        food_kits_per_person=0.5,
        medical_units_per_person=0.1,
        shelter_spaces_per_person=0.25,
    )

    result = calculate_demand(3, assumptions)

    assert result.water_litres == 7.5
    assert result.food_kits == 2
    assert result.medical_units == 1
    assert result.shelter_spaces == 1
    assert result.assumptions == assumptions


def test_negative_population_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        calculate_demand(-1)


def test_invalid_assumption_is_rejected():
    with pytest.raises(ValidationError):
        DemandAssumptions(water_litres_per_person=-1)