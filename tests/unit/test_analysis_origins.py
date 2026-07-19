from __future__ import annotations

import pytest


@pytest.mark.contract
@pytest.mark.gate("G1")
def test_zero_nearby_records_origin_is_retained_as_insufficient_corpus_evidence(
    load_fixture,
) -> None:
    fixture = load_fixture("fixtures/contracts/analysis_origin_core.json")
    origin = next(item for item in fixture["cases"] if item["origin_id"] == "pin:000001")
    assert origin["nearby_facility_ids"] == []
    assert origin["expected_status"] == "insufficient_corpus_evidence"
    assert origin["expected_message"] == "no observed records"


@pytest.mark.contract
@pytest.mark.gate("G1")
def test_unmappable_origin_has_explicit_unavailable_reason(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/analysis_origin_core.json")
    origin = next(item for item in fixture["cases"] if item["origin_id"] == "pin:000002")
    assert origin["postal_reference_point"] is None
    assert origin["unavailable_reason"] == "no_valid_postal_coordinate"
