from __future__ import annotations

import pytest

from medical_desert.domain.models import ContradictionState, ScoreFactors, SupportBand
from medical_desert.scoring.engine import (
    AssessabilityInputs,
    apply_contradiction_policy,
    calculate_assessability,
    classify_region,
    documentary_support_index,
    verification_priority,
)


def test_documentary_support_index_sums_all_factors() -> None:
    factors = ScoreFactors(
        direct_evidence_specificity=20,
        independent_source_corroboration=10,
        source_quality=8,
        entity_attribution_quality=7,
        freshness=3,
        prerequisite_support=2,
    )
    assert documentary_support_index(factors) == 50


def test_unresolved_contradiction_caps_score_without_erasing_raw_evidence() -> None:
    score, band, readiness = apply_contradiction_policy(82, ContradictionState.UNRESOLVED)
    assert score == 49
    assert band == SupportBand.CLAIM_ONLY_OR_WEAK
    assert readiness == "review_required"


def test_confirmed_contradiction_keeps_numeric_score_but_displays_unsupported() -> None:
    score, band, readiness = apply_contradiction_policy(82, ContradictionState.CONFIRMED)
    assert score == 82
    assert band == SupportBand.UNSUPPORTED_OR_VERY_WEAK
    assert readiness == "review_required"


def test_zero_region_entities_classify_as_insufficient_corpus_evidence() -> None:
    result = calculate_assessability(
        AssessabilityInputs(
            n_source_rows=100,
            n_structurally_eligible_rows=100,
            n_canonical_facility_entities=99,
            n_region_entities=0,
            n_capability_assessed_entities=0,
            geography_resolved=0,
            traceable_sources=0,
            freshness_known=0,
            unresolved_contradictions=0,
            ambiguous_geography=0,
            source_bundle_version="fixture",
        )
    )
    assert classify_region(0, result.observed_record_assessability).value == (
        "insufficient_corpus_evidence"
    )


def test_more_ambiguous_geography_never_increases_assessability() -> None:
    base = dict(
        n_source_rows=20,
        n_structurally_eligible_rows=20,
        n_canonical_facility_entities=20,
        n_region_entities=10,
        n_capability_assessed_entities=10,
        geography_resolved=10,
        traceable_sources=10,
        freshness_known=10,
        unresolved_contradictions=0,
        source_bundle_version="fixture",
    )
    clear = calculate_assessability(AssessabilityInputs(**base, ambiguous_geography=0))
    ambiguous = calculate_assessability(AssessabilityInputs(**base, ambiguous_geography=5))
    assert ambiguous.observed_record_assessability <= clear.observed_record_assessability


def test_priority_formula_uses_frozen_weights() -> None:
    assert verification_priority(0.5, 0.4, 0.3, 0.2, 0.1) == pytest.approx(0.385)
