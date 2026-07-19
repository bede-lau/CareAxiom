from __future__ import annotations

import pytest


@pytest.mark.contract
@pytest.mark.gate("G7")
def test_darbhanga_observed_facility_count_is_frozen(load_fixture) -> None:
    demo = load_fixture("fixtures/demo/darbhanga_demo_core.json")
    assert demo["observed_facility_records"] == 15


@pytest.mark.contract
@pytest.mark.gate("G7")
def test_darbhanga_capability_matches_are_frozen(load_fixture) -> None:
    demo = load_fixture("fixtures/demo/darbhanga_demo_core.json")
    assert demo["capability_matches"] == {
        "maternal_emergency_documentation": 0,
        "emergency_surgery_documentation": 3,
        "advanced_imaging_documentation": 2,
    }


@pytest.mark.contract
@pytest.mark.gate("G7")
def test_darbhanga_emergency_surgery_ids_are_frozen(load_fixture) -> None:
    demo = load_fixture("fixtures/demo/darbhanga_demo_core.json")
    matches = demo["capability_match_facilities"]["emergency_surgery_documentation"]
    assert [item["facility_id"] for item in matches] == [
        "b69b988a-1179-44df-8349-e0d632ebfb83",
        "b668392a-bc18-4bee-b17e-0155f07e966a",
        "5e0b96cf-e221-4e1f-bd1f-e9b49d3eca7e",
    ]


@pytest.mark.contract
@pytest.mark.gate("G7")
def test_darbhanga_advanced_imaging_ids_are_first_two_surgery_matches(load_fixture) -> None:
    demo = load_fixture("fixtures/demo/darbhanga_demo_core.json")
    surgery = demo["capability_match_facilities"]["emergency_surgery_documentation"]
    imaging = demo["capability_match_facilities"]["advanced_imaging_documentation"]
    assert imaging == surgery[:2]


@pytest.mark.contract
@pytest.mark.gate("G7")
def test_darbhanga_maternal_emergency_match_set_is_empty(load_fixture) -> None:
    demo = load_fixture("fixtures/demo/darbhanga_demo_core.json")
    assert demo["capability_match_facilities"]["maternal_emergency_documentation"] == []


@pytest.mark.contract
@pytest.mark.gate("G7")
def test_darbhanga_nfhs_values_are_context_only(load_fixture) -> None:
    demo = load_fixture("fixtures/demo/darbhanga_demo_core.json")
    assert demo["nfhs_context"] == {
        "four_plus_anc_percent": 24.9,
        "institutional_birth_percent": 69.9,
        "women_15_49_anaemia_percent": 60.8,
    }
    assert demo["classification"] == "planning_priority_candidate"


@pytest.mark.contract
@pytest.mark.gate("G7")
def test_referral_copilot_is_disabled_in_demo_fixture(load_fixture) -> None:
    demo = load_fixture("fixtures/demo/darbhanga_demo_core.json")
    assert demo["referral_copilot_enabled"] is False
