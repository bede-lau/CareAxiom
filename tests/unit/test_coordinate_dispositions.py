from __future__ import annotations

import pytest

from tests.support.oracles import coordinate_disposition


@pytest.mark.contract
@pytest.mark.gate("G1")
@pytest.mark.parametrize(
    "case_id",
    [
        "pin-valid",
        "pin-valid-boundary-min",
        "pin-valid-boundary-max",
        "pin-zero-string",
        "pin-zero-decimal",
        "pin-na",
        "pin-blank",
        "pin-malformed",
        "pin-outside-latitude",
        "pin-outside-longitude",
        "pin-negative",
    ],
)
def test_coordinate_case_has_expected_exclusive_disposition(load_fixture, case_id: str) -> None:
    fixture = load_fixture("fixtures/contracts/pincode_office_contract_core.json")
    case = next(item for item in fixture["cases"] if item["case_id"] == case_id)
    assert coordinate_disposition(case["latitude"], case["longitude"]) == case[
        "expected_disposition"
    ]


@pytest.mark.hypothesis
@pytest.mark.gate("G1")
def test_valid_coordinates_never_classify_as_zero_or_outside() -> None:
    hypothesis = pytest.importorskip("hypothesis")
    st = pytest.importorskip("hypothesis.strategies")

    @hypothesis.given(
        latitude=st.floats(min_value=6.5, max_value=39, allow_nan=False, allow_infinity=False),
        longitude=st.floats(min_value=68, max_value=98, allow_nan=False, allow_infinity=False),
    )
    def property_test(latitude: float, longitude: float) -> None:
        assert coordinate_disposition(latitude, longitude) == "valid"

    property_test()
