from __future__ import annotations

import pytest


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_source_bundle_contains_exactly_three_frozen_tables(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/source_bundle_contract_core.json")
    assert set(fixture["tables"]) == {
        "facilities",
        "india_post_pincode_directory",
        "nfhs_5_district_health_indicators",
    }


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_source_bundle_exact_row_counts_are_frozen(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/source_bundle_contract_core.json")
    assert {name: value["rows"] for name, value in fixture["tables"].items()} == {
        "facilities": 10088,
        "india_post_pincode_directory": 165627,
        "nfhs_5_district_health_indicators": 706,
    }


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_facility_dispositions_conserve_all_source_rows(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/source_bundle_contract_core.json")
    integrity = fixture["facility_integrity"]
    assert (
        integrity["canonical_uuid_entities"]
        + integrity["exact_duplicate_rows"]
        + integrity["quarantined_non_uuid_rows"]
    ) == fixture["tables"]["facilities"]["rows"]


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_postal_coordinate_dispositions_conserve_all_source_rows(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/source_bundle_contract_core.json")
    postal = fixture["postal_integrity"]
    assert (
        postal["valid_coordinate_rows"]
        + postal["unparseable_or_missing_coordinate_rows"]
        + postal["zero_coordinate_rows"]
        + postal["out_of_envelope_coordinate_rows"]
    ) == fixture["tables"]["india_post_pincode_directory"]["rows"]


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_analysis_origin_counts_conserve_all_distinct_pins(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/source_bundle_contract_core.json")
    postal = fixture["postal_integrity"]
    assert postal["mappable_pins"] + postal["unavailable_origins"] == postal["distinct_pins"]
