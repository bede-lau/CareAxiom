from __future__ import annotations

import pytest

from medical_desert import demo_data


@pytest.mark.contract
@pytest.mark.gate("G1")
@pytest.mark.parametrize(
    "facility_id",
    [
        "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
        "4ddde88c-fb72-4ed5-bfa0-8bf647bb3044",
    ],
)
def test_live_geography_conflict_is_flagged_for_review(load_fixture, facility_id: str) -> None:
    fixture = load_fixture("fixtures/demo/darbhanga_geography_conflicts.json")
    expected = next(item for item in fixture["cases"] if item["facility_id"] == facility_id)
    facility = demo_data.FACILITY_BY_ID[facility_id]
    quality_signals = facility["observed_fields"]["quality_signals"]
    assert any(
        signal["code"] == expected["expected_quality_flag"]
        and signal["severity"] == expected["expected_review_priority"]
        for signal in quality_signals
    )


@pytest.mark.contract
@pytest.mark.gate("G1")
@pytest.mark.parametrize(
    "facility_id",
    [
        "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
        "4ddde88c-fb72-4ed5-bfa0-8bf647bb3044",
    ],
)
def test_live_geography_conflict_is_not_silently_accepted(load_fixture, facility_id: str) -> None:
    fixture = load_fixture("fixtures/demo/darbhanga_geography_conflicts.json")
    expected = next(item for item in fixture["cases"] if item["facility_id"] == facility_id)
    facility = demo_data.FACILITY_BY_ID[facility_id]
    assert facility["city"] == expected["address_city"]
    assert facility["district"] == expected["joined_district"]
    assert facility["geography_conflict"] is not None
    assert "Excluded from distance aggregation" in facility["geography_conflict"]


@pytest.mark.contract
@pytest.mark.gate("G5")
def test_each_live_geography_conflict_has_a_priority_queue_item() -> None:
    review_items = demo_data.default_geography_review_items()
    assert {item["facility_id"] for item in review_items} == {
        "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
        "4ddde88c-fb72-4ed5-bfa0-8bf647bb3044",
    }
    assert all(item["unresolved_contradiction_severity"] == 1.0 for item in review_items)
