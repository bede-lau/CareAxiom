from __future__ import annotations

from datetime import UTC, datetime

from medical_desert.domain.models import (
    Actor,
    Assessability,
    CapabilityId,
    DocumentaryQueryResult,
    Geography,
    IdentityMode,
    MaterializationState,
    ProductRole,
    RegionalClassification,
    Scenario,
)


def actor(actor_id: str = "planner-1") -> Actor:
    return Actor(
        actor_id=actor_id,
        display_name=actor_id,
        roles=[ProductRole.PLANNER, ProductRole.REVIEWER],
        identity_mode=IdentityMode.FULL_RBAC,
    )


def result() -> DocumentaryQueryResult:
    now = datetime(2026, 7, 19, tzinfo=UTC)
    return DocumentaryQueryResult(
        result_id="result-1",
        capability_id=CapabilityId.MATERNAL_EMERGENCY,
        geography=Geography(
            geography_id="district:br:darbhanga",
            geography_type="district",
            name="Darbhanga",
            state="Bihar",
            district="Darbhanga",
        ),
        radius_km=25,
        classification=RegionalClassification.LOW_SUPPORT_EXTERNAL_VALIDATION,
        classification_label="Low nearby documentary support",
        observed_record_assessability=Assessability(
            observed_record_assessability=0.78,
            components=[],
            n_source_rows=15,
            n_structurally_eligible_rows=15,
            n_canonical_facility_entities=15,
            n_region_entities=15,
            n_capability_assessed_entities=15,
            source_bundle_version="fixture",
        ),
        distinct_observed_facilities=15,
        qualifying_facilities=0,
        contradiction_count=2,
        excluded_counts={"geography_conflict": 2},
        facilities=[],
        survey_context=None,
        planning_priority_candidate=True,
        assumptions=["Straight-line distance", "Documentary evidence only"],
        source_bundle_id="fixture",
        policy_version="fixture-policy",
        materialization_version=1,
        materialization_state=MaterializationState.APPLIED,
        trace_id="trace-fixture",
        generated_at=now,
    )


def scenario(*, version: int = 1, notes: str = "") -> Scenario:
    now = datetime(2026, 7, 19, tzinfo=UTC)
    return Scenario(
        scenario_id="scenario-1",
        name="Darbhanga review",
        owner_id="planner-1",
        collaborators=[],
        capability_id=CapabilityId.MATERNAL_EMERGENCY,
        geography_id="district:br:darbhanga",
        radius_km=25,
        map_extent=None,
        selected_region_ids=["district:br:darbhanga"],
        shortlisted_facility_ids=[],
        notes=notes,
        decision_rationale="Review geography conflicts before prioritization.",
        machine_score_version="fixture-score",
        human_review_version=0,
        dataset_snapshot_id="fixture",
        evidence_snapshot_id="fixture-evidence",
        saved_result=result(),
        version=version,
        created_at=now,
        updated_at=now,
    )
