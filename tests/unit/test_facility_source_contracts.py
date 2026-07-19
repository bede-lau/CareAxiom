from __future__ import annotations

import pytest

from tests.support.oracles import UUID_RE, parse_json_like_array


@pytest.mark.contract
@pytest.mark.gate("G1")
def test_malformed_json_remains_unparseable(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/facility_source_contract_core.json")
    case = next(item for item in fixture["cases"] if item["case_id"] == "facility-malformed-json")
    parsed, status = parse_json_like_array(case["raw_value"])
    assert parsed is None
    assert status == "unparseable"


@pytest.mark.contract
@pytest.mark.gate("G1")
def test_empty_array_is_distinct_from_parse_failure(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/facility_source_contract_core.json")
    empty = next(item for item in fixture["cases"] if item["case_id"] == "facility-empty-array")
    malformed = next(
        item for item in fixture["cases"] if item["case_id"] == "facility-malformed-json"
    )
    assert parse_json_like_array(empty["raw_value"]) == ([], "parsed")
    assert parse_json_like_array(malformed["raw_value"]) == (None, "unparseable")


@pytest.mark.contract
@pytest.mark.gate("G1")
def test_non_uuid_spillover_is_quarantined(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/facility_source_contract_core.json")
    spillover = next(
        item for item in fixture["cases"] if item["case_id"] == "facility-spillover-row"
    )
    assert UUID_RE.fullmatch(spillover["unique_id"]) is None
    assert spillover["disposition"] == "quarantined"


@pytest.mark.contract
@pytest.mark.gate("G1")
def test_exact_duplicate_retains_duplicate_disposition(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/facility_source_contract_core.json")
    duplicates = [
        item
        for item in fixture["cases"]
        if item["unique_id"] == "99999999-9999-4999-8999-999999999999"
    ]
    assert [item["disposition"] for item in duplicates] == ["accepted", "exact_duplicate"]


@pytest.mark.contract
@pytest.mark.gate("G1")
def test_missing_capacity_is_distinct_from_reported_zero(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/facility_source_contract_core.json")
    missing = next(
        item for item in fixture["cases"] if item["case_id"] == "facility-missing-capacity"
    )
    zero = next(item for item in fixture["cases"] if item["case_id"] == "facility-zero-capacity")
    assert missing["expected_parsed"] is None
    assert zero["expected_parsed"] == 0
