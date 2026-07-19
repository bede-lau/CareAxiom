from __future__ import annotations

import pytest

from tests.support.oracles import parse_nfhs_value


@pytest.mark.contract
@pytest.mark.gate("G1")
@pytest.mark.parametrize(
    "case_id",
    [
        "nfhs-plain",
        "nfhs-whitespace",
        "nfhs-low-sample",
        "nfhs-suppressed",
        "nfhs-blank",
        "nfhs-whitespace-blank",
        "nfhs-zero",
        "nfhs-unrecognized-decoration",
        "nfhs-malformed-parenthesis",
        "nfhs-negative-impossible",
        "nfhs-over-100",
    ],
)
def test_nfhs_value_preserves_numeric_qualifier_and_status(load_fixture, case_id: str) -> None:
    fixture = load_fixture("fixtures/contracts/nfhs_indicator_contract_core.json")
    case = next(item for item in fixture["cases"] if item["case_id"] == case_id)
    actual = parse_nfhs_value(case["raw_value"])
    assert actual == {
        "numeric_value": case["numeric_value"],
        "qualifier": case["qualifier"],
        "parse_status": case["parse_status"],
    }


@pytest.mark.contract
@pytest.mark.gate("G1")
def test_suppressed_nfhs_value_is_not_zero(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/nfhs_indicator_contract_core.json")
    case = next(item for item in fixture["cases"] if item["case_id"] == "nfhs-suppressed")
    assert case["numeric_value"] is None
    assert case["parse_status"] == "unavailable"
