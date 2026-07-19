from __future__ import annotations

from dataclasses import dataclass

from medical_desert.domain.models import (
    Assessability,
    AssessabilityComponent,
    ContradictionState,
    RegionalClassification,
    ScoreFactors,
    SupportBand,
)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def documentary_support_index(factors: ScoreFactors) -> int:
    return max(0, min(100, factors.total))


def support_band(score: int | None) -> SupportBand:
    if score is None:
        return SupportBand.INSUFFICIENT_EVIDENCE
    if score >= 75:
        return SupportBand.STRONGLY_SUPPORTED
    if score >= 50:
        return SupportBand.PARTIALLY_SUPPORTED
    if score >= 25:
        return SupportBand.CLAIM_ONLY_OR_WEAK
    return SupportBand.UNSUPPORTED_OR_VERY_WEAK


def apply_contradiction_policy(
    score: int | None, contradiction_state: ContradictionState
) -> tuple[int | None, SupportBand, str]:
    if score is None:
        return None, SupportBand.INSUFFICIENT_EVIDENCE, "abstain"
    if contradiction_state == ContradictionState.CONFIRMED:
        return score, SupportBand.UNSUPPORTED_OR_VERY_WEAK, "review_required"
    if contradiction_state == ContradictionState.UNRESOLVED:
        capped = min(score, 49)
        return capped, support_band(capped), "review_required"
    return score, support_band(score), "ready" if score >= 50 else "review_required"


@dataclass(frozen=True)
class AssessabilityInputs:
    n_source_rows: int
    n_structurally_eligible_rows: int
    n_canonical_facility_entities: int
    n_region_entities: int
    n_capability_assessed_entities: int
    geography_resolved: int
    traceable_sources: int
    freshness_known: int
    unresolved_contradictions: int
    ambiguous_geography: int
    source_bundle_version: str


def _component(
    name: str, numerator: int, denominator: int, excluded: int, weight: float
) -> AssessabilityComponent:
    rate = numerator / denominator if denominator else 0.0
    return AssessabilityComponent(
        component=name,
        rate=clamp(rate),
        numerator=numerator,
        denominator=denominator,
        excluded_count=excluded,
        weight=weight,
    )


def calculate_assessability(inputs: AssessabilityInputs) -> Assessability:
    source_denominator = max(inputs.n_source_rows, 0)
    region_denominator = max(inputs.n_region_entities, 0)
    components = [
        _component(
            "source_structural_integrity_rate",
            inputs.n_structurally_eligible_rows,
            source_denominator,
            source_denominator - inputs.n_structurally_eligible_rows,
            0.15,
        ),
        _component(
            "geography_resolution_rate",
            inputs.geography_resolved,
            region_denominator,
            region_denominator - inputs.geography_resolved,
            0.25,
        ),
        _component(
            "traceable_source_rate",
            inputs.traceable_sources,
            region_denominator,
            region_denominator - inputs.traceable_sources,
            0.20,
        ),
        _component(
            "capability_assessment_completion_rate",
            inputs.n_capability_assessed_entities,
            region_denominator,
            region_denominator - inputs.n_capability_assessed_entities,
            0.20,
        ),
        _component(
            "entity_resolution_rate",
            inputs.n_canonical_facility_entities,
            max(inputs.n_structurally_eligible_rows, 0),
            max(inputs.n_structurally_eligible_rows - inputs.n_canonical_facility_entities, 0),
            0.10,
        ),
        _component(
            "freshness_known_rate",
            inputs.freshness_known,
            region_denominator,
            region_denominator - inputs.freshness_known,
            0.10,
        ),
        _component(
            "unresolved_contradiction_rate",
            inputs.unresolved_contradictions,
            region_denominator,
            0,
            -0.15,
        ),
        _component(
            "ambiguous_geography_rate",
            inputs.ambiguous_geography,
            region_denominator,
            0,
            -0.15,
        ),
    ]
    value = clamp(sum(component.rate * component.weight for component in components))
    return Assessability(
        observed_record_assessability=round(value, 4),
        components=components,
        n_source_rows=inputs.n_source_rows,
        n_structurally_eligible_rows=inputs.n_structurally_eligible_rows,
        n_canonical_facility_entities=inputs.n_canonical_facility_entities,
        n_region_entities=inputs.n_region_entities,
        n_capability_assessed_entities=inputs.n_capability_assessed_entities,
        source_bundle_version=inputs.source_bundle_version,
    )


def classify_region(
    qualifying_facilities: int, assessability: float, high_threshold: float = 0.65
) -> RegionalClassification:
    has_support = qualifying_facilities > 0
    high_assessability = assessability >= high_threshold
    if has_support and high_assessability:
        return RegionalClassification.STRONG_SUPPORT
    if has_support and not high_assessability:
        return RegionalClassification.MIXED_SIGNAL
    if not has_support and high_assessability:
        return RegionalClassification.LOW_SUPPORT_EXTERNAL_VALIDATION
    return RegionalClassification.INSUFFICIENT_CORPUS_EVIDENCE


def verification_priority(
    classification_flip_potential: float,
    map_cells_or_regions_affected: float,
    active_scenario_references: float,
    evidence_staleness: float,
    unresolved_contradiction_severity: float,
) -> float:
    value = (
        0.40 * classification_flip_potential
        + 0.25 * map_cells_or_regions_affected
        + 0.20 * active_scenario_references
        + 0.10 * evidence_staleness
        + 0.05 * unresolved_contradiction_severity
    )
    return round(clamp(value), 6)
