from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from medical_desert.adapters.databricks_analytics import DatabricksGoldAnalyticsAdapter
from medical_desert.domain.models import (
    CapabilityId,
    SupportBand,
    SurveyContextAvailability,
)


class FakeSQL:
    def __init__(self) -> None:
        self.statements: list[tuple[str, list[Any]]] = []

    def fetch_all(
        self,
        statement: str,
        parameters: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        values = parameters or []
        self.statements.append((statement, values))
        if "silver`.`analysis_origin" in statement:
            return [
                {
                    "analysis_origin_id": "pin:846001",
                    "pincode": "846001",
                    "latitude": 26.16,
                    "longitude": 85.90,
                    "origin_status": "mappable",
                    "unavailable_reason": None,
                    "geography_status": "unambiguous_label_evidence",
                    "coordinate_dispersion_degrees": 0.02,
                    "reference_method": "coordinate_median",
                    "state_candidates": ["bihar"],
                    "district_candidates": ["darbhanga"],
                }
            ]
        if "gold`.`facility_documentary_support" in statement:
            if values[-1] != CapabilityId.EMERGENCY_SURGERY.value:
                return []
            return [
                {
                    "documentary_support_index": 82.0,
                    "support_band": "strongly_supported",
                    "contradiction_state": "none",
                    "direct_evidence_specificity": 30.0,
                    "independent_source_corroboration": 10.0,
                    "source_quality": 10.0,
                    "entity_attribution_quality": 15.0,
                    "freshness": 7.0,
                    "prerequisite_support": 10.0,
                    "exclusion_reasons": [],
                    "evidence_span_ids": ["evidence-1"],
                    "policy_version": "documentary-policy-v1",
                    "calculated_at": datetime(2026, 7, 19, tzinfo=UTC),
                }
            ]
        if "silver`.`evidence_span" in statement:
            return [
                {
                    "evidence_span_id": "evidence-1",
                    "facility_id": "facility-1",
                    "capability_id": CapabilityId.EMERGENCY_SURGERY.value,
                    "source_field": "specialties",
                    "evidence_text": "Emergency medicine and general surgery",
                    "source_url": "https://example.org/facility-1",
                    "publisher": "Example registry",
                    "source_family": "registry",
                    "publication_time": None,
                    "valid_time": None,
                    "retrieval_time": datetime(2026, 7, 19, tzinfo=UTC),
                    "extraction_method": "deterministic-policy",
                    "extraction_version": "v1",
                    "polarity": "positive",
                    "span_hash": "span-hash",
                }
            ]
        if "gold`.`district_context_profile" in statement:
            return [
                {
                    "survey_context_availability": "matched",
                    "context_payload": json.dumps(
                        {
                            "institutional_births_pct": json.dumps(
                                {
                                    "raw_value": "(69.9)",
                                    "numeric_value": 69.9,
                                    "qualifier": "low_sample_25_49",
                                    "parse_status": "parsed",
                                }
                            ),
                            "malformed_indicator": json.dumps(
                                {
                                    "raw_value": "not reported",
                                    "numeric_value": None,
                                    "qualifier": "standard",
                                    "parse_status": "unparseable",
                                }
                            ),
                        }
                    ),
                    "source_version": "nfhs5-district-dais-2026",
                    "calculated_at": datetime(2026, 7, 19, tzinfo=UTC),
                }
            ]
        if "silver`.`facility_normalized" in statement:
            return [
                {
                    "facility_id": "facility-1",
                    "canonical_name": "Darbhanga Medical College",
                    "description": "Observed facility record.",
                    "city_raw": "Darbhanga",
                    "city_normalized": "darbhanga",
                    "state_raw": "Bihar",
                    "state_normalized": "bihar",
                    "pincode": "846001",
                    "latitude": 26.17,
                    "longitude": 85.90,
                    "location_conflict_status": "none",
                    "freshness_status": "known",
                    "raw_payload": json.dumps(
                        {
                            "specialties": ["emergencyMedicine", "generalSurgery"],
                            "capabilities": ["Emergency and surgical care documented"],
                        }
                    ),
                }
            ]
        raise AssertionError(f"Unexpected SQL statement: {statement}")

    def execute(self, statement: str, parameters: list[Any] | None = None) -> None:
        self.statements.append((statement, parameters or []))


def adapter(sql: FakeSQL | None = None) -> DatabricksGoldAnalyticsAdapter:
    return DatabricksGoldAnalyticsAdapter(
        sql or FakeSQL(),
        project_catalog="medical_desert",
        source_bundle_id="bundle-20260719",
        policy_version="documentary-policy-v1",
        scoring_version="documentary-policy-v1",
        focus_state="Bihar",
        focus_district="Darbhanga",
    )


def test_project_catalog_rejects_injected_identifier() -> None:
    with pytest.raises(ValueError):
        DatabricksGoldAnalyticsAdapter(
            FakeSQL(),
            project_catalog="medical_desert; DROP TABLE gold",
            source_bundle_id="bundle",
            policy_version="policy",
            scoring_version="scoring",
            focus_state="Bihar",
            focus_district="Darbhanga",
        )


def test_gold_adapter_maps_geography_facility_evidence_and_survey_context() -> None:
    analytics = adapter()

    geographies = analytics.list_geographies()
    facility = analytics.get_facility("facility-1")
    assessment = analytics.get_assessment(
        "facility-1",
        CapabilityId.EMERGENCY_SURGERY,
    )
    evidence = analytics.get_evidence(
        "facility-1",
        CapabilityId.EMERGENCY_SURGERY,
    )
    survey = analytics.get_survey_context(analytics.survey_district_id)

    assert geographies[0].geography_id == "district:br:darbhanga"
    assert geographies[1].metadata["not_a_centroid"] is True
    assert facility is not None
    assert facility.source_snapshot_id == "bundle-20260719"
    assert assessment is not None
    assert assessment.support_band == SupportBand.STRONGLY_SUPPORTED
    assert assessment.evidence_ids == ["evidence-1"]
    assert str(evidence[0].source_url) == "https://example.org/facility-1"
    assert survey is not None
    assert survey.survey_context_availability == SurveyContextAvailability.MATCHED
    qualifiers = {item.indicator_id: item.qualifier for item in survey.indicators}
    assert qualifiers["institutional_births_pct"] == "low_sample_25_49"
    assert qualifiers["malformed_indicator"] == "unparseable"


def test_missing_materialized_assessment_abstains_instead_of_inventing_support() -> None:
    assessment = adapter().get_assessment(
        "facility-1",
        CapabilityId.MATERNAL_EMERGENCY,
    )

    assert assessment is not None
    assert assessment.support_band == SupportBand.INSUFFICIENT_EVIDENCE
    assert assessment.documentary_support_index is None
    assert assessment.decision_readiness == "abstain"
