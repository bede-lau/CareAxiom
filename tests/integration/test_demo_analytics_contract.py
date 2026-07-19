from __future__ import annotations

import pytest

from medical_desert import demo_data
from medical_desert.adapters.demo_analytics import DemoAnalyticsAdapter
from medical_desert.domain.models import CapabilityId


@pytest.fixture
def analytics() -> DemoAnalyticsAdapter:
    return DemoAnalyticsAdapter()


@pytest.mark.integration
@pytest.mark.gate("G7")
def test_demo_adapter_exposes_exactly_fifteen_observed_facilities(
    analytics: DemoAnalyticsAdapter,
) -> None:
    assert len(analytics.list_facilities("district:br:darbhanga")) == 15


@pytest.mark.integration
@pytest.mark.gate("G7")
def test_demo_adapter_emergency_surgery_support_set_matches_live_policy(
    analytics: DemoAnalyticsAdapter,
) -> None:
    supported = {
        facility["facility_id"]
        for facility in analytics.list_facilities("district:br:darbhanga")
        if facility["facility_id"] in demo_data.SUPPORTED[CapabilityId.EMERGENCY_SURGERY]
    }
    assert supported == {
        "b69b988a-1179-44df-8349-e0d632ebfb83",
        "b668392a-bc18-4bee-b17e-0155f07e966a",
        "5e0b96cf-e221-4e1f-bd1f-e9b49d3eca7e",
    }


@pytest.mark.integration
@pytest.mark.gate("G7")
def test_demo_adapter_advanced_imaging_support_set_matches_live_policy(
    analytics: DemoAnalyticsAdapter,
) -> None:
    assert demo_data.SUPPORTED[CapabilityId.ADVANCED_IMAGING] == {
        "b69b988a-1179-44df-8349-e0d632ebfb83",
        "b668392a-bc18-4bee-b17e-0155f07e966a",
    }


@pytest.mark.integration
@pytest.mark.gate("G7")
def test_demo_adapter_maternal_support_set_is_empty() -> None:
    assert demo_data.SUPPORTED[CapabilityId.MATERNAL_EMERGENCY] == set()


@pytest.mark.integration
@pytest.mark.gate("G1")
def test_nfhs_context_does_not_change_facility_assessment(
    analytics: DemoAnalyticsAdapter,
) -> None:
    facility_id = "b69b988a-1179-44df-8349-e0d632ebfb83"
    before = analytics.get_assessment(facility_id, CapabilityId.EMERGENCY_SURGERY)
    assert analytics.get_survey_context("district:br:darbhanga") is not None
    after = analytics.get_assessment(facility_id, CapabilityId.EMERGENCY_SURGERY)
    assert before == after


@pytest.mark.integration
@pytest.mark.gate("G1")
def test_geography_conflict_assessment_abstains_without_crashing(
    analytics: DemoAnalyticsAdapter,
) -> None:
    assessment = analytics.get_assessment(
        "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
        CapabilityId.MATERNAL_EMERGENCY,
    )
    assert assessment is not None
    assert assessment.decision_readiness == "abstain"
    assert assessment.contradiction_state.value == "unresolved"
    assert any("Excluded from distance aggregation" in item for item in assessment.contradictions)
