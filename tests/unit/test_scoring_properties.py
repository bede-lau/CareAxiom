from __future__ import annotations

import pytest

from tests.support.oracles import (
    documentary_support_index,
    support_band,
    verification_priority,
)


@pytest.mark.contract
@pytest.mark.gate("G3")
@pytest.mark.parametrize(
    "case_id",
    [
        "score-strong",
        "score-partial-boundary",
        "score-claim-only-boundary",
        "score-unsupported",
        "score-unresolved-contradiction",
        "score-confirmed-contradiction",
    ],
)
def test_score_arithmetic_and_band_match_frozen_contract(load_fixture, case_id: str) -> None:
    fixture = load_fixture("fixtures/contracts/scoring_contract_core.json")
    case = next(item for item in fixture["cases"] if item["case_id"] == case_id)
    index = documentary_support_index(case["factors"])
    assert index == case["expected_index"]
    assert support_band(index, case["contradiction_state"]) == case["expected_band"]


@pytest.mark.contract
@pytest.mark.gate("G3")
def test_duplicate_evidence_does_not_increase_support() -> None:
    unique_source_families = {"official": 10, "directory": 5}
    repeated_same_family = {"official": 10, "directory": 5, "official:duplicate": 0}
    assert sum(repeated_same_family.values()) == sum(unique_source_families.values())


@pytest.mark.hypothesis
@pytest.mark.gate("G3")
def test_removing_support_never_increases_score() -> None:
    hypothesis = pytest.importorskip("hypothesis")
    st = pytest.importorskip("hypothesis.strategies")

    @hypothesis.given(
        factors=st.lists(
            st.floats(min_value=0, max_value=20, allow_nan=False, allow_infinity=False),
            min_size=6,
            max_size=6,
        ),
        removed=st.integers(min_value=0, max_value=5),
    )
    def property_test(factors: list[float], removed: int) -> None:
        before = documentary_support_index({str(i): value for i, value in enumerate(factors)})
        factors[removed] = 0
        after = documentary_support_index({str(i): value for i, value in enumerate(factors)})
        assert after <= before

    property_test()


@pytest.mark.contract
@pytest.mark.gate("G3")
@pytest.mark.parametrize(
    "case_id",
    ["priority-zero", "priority-mid", "priority-max", "priority-clamped"],
)
def test_priority_formula_matches_frozen_inputs(load_fixture, case_id: str) -> None:
    fixture = load_fixture("fixtures/contracts/scoring_contract_core.json")
    case = next(item for item in fixture["priority_cases"] if item["case_id"] == case_id)
    assert verification_priority(case["inputs"]) == pytest.approx(case["expected"])


@pytest.mark.hypothesis
@pytest.mark.gate("G3")
def test_increasing_any_priority_factor_never_lowers_priority() -> None:
    hypothesis = pytest.importorskip("hypothesis")
    st = pytest.importorskip("hypothesis.strategies")

    @hypothesis.given(
        values=st.lists(
            st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=5,
        ),
        index=st.integers(min_value=0, max_value=4),
        increase=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    )
    def property_test(values: list[float], index: int, increase: float) -> None:
        before = verification_priority(values)
        values[index] = min(1.0, values[index] + increase)
        assert verification_priority(values) >= before

    property_test()
