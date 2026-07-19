from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from medical_desert import demo_data
from medical_desert.domain.models import (
    CapabilityAssessment,
    CapabilityId,
    ContradictionState,
    EvidenceSpan,
    FacilityDetail,
    Geography,
    ScoreFactors,
    SupportBand,
    SurveyContext,
)
from medical_desert.scoring.engine import apply_contradiction_policy, documentary_support_index


class DemoAnalyticsAdapter:
    source_bundle_id = demo_data.SOURCE_BUNDLE_ID
    evidence_snapshot_id = demo_data.EVIDENCE_SNAPSHOT_ID
    policy_version = demo_data.POLICY_VERSION
    scoring_version = demo_data.SCORING_VERSION
    survey_district_id = "district:br:darbhanga"

    def list_geographies(self) -> list[Geography]:
        return [Geography.model_validate(item) for item in demo_data.GEOGRAPHIES]

    def get_geography(self, geography_id: str) -> Geography | None:
        return next(
            (
                Geography.model_validate(item)
                for item in demo_data.GEOGRAPHIES
                if item["geography_id"] == geography_id
            ),
            None,
        )

    def list_facilities(self, geography_id: str) -> list[demo_data.DemoFacility]:
        geography = self.get_geography(geography_id)
        if geography is None:
            return []
        facilities = list(demo_data.FACILITIES)
        if geography.pin:
            facilities = [facility for facility in facilities if facility["pin"] == geography.pin]
        return facilities

    def _base_assessment(
        self, facility_id: str, capability_id: CapabilityId
    ) -> CapabilityAssessment:
        facility = demo_data.FACILITY_BY_ID[facility_id]
        matched = facility_id in demo_data.SUPPORTED[capability_id]
        evidence = self.get_evidence(facility_id, capability_id)
        geography_conflict = facility["geography_conflict"]
        if matched:
            factors = ScoreFactors(
                direct_evidence_specificity=28,
                independent_source_corroboration=12,
                source_quality=12,
                entity_attribution_quality=14,
                freshness=6,
                prerequisite_support=10,
            )
            raw_score = documentary_support_index(factors)
            contradiction = ContradictionState.NONE
            score, band, readiness = apply_contradiction_policy(raw_score, contradiction)
            sufficiency = "sufficient"
            missing: list[str] = []
        else:
            texts = demo_data.evidence_texts(facility, capability_id)
            contradiction = ContradictionState.NONE
            if texts:
                factors = ScoreFactors(
                    direct_evidence_specificity=14,
                    independent_source_corroboration=0,
                    source_quality=7,
                    entity_attribution_quality=12,
                    freshness=3,
                    prerequisite_support=0,
                )
                raw_score = documentary_support_index(factors)
                score, band, readiness = apply_contradiction_policy(raw_score, contradiction)
                sufficiency = "limited"
            else:
                factors = None
                score = None
                band = SupportBand.INSUFFICIENT_EVIDENCE
                readiness = "abstain"
                sufficiency = "insufficient"
            missing = self._missing_prerequisites(capability_id, facility)
        if geography_conflict:
            contradiction = ContradictionState.UNRESOLVED
            if score is not None:
                score, band, readiness = apply_contradiction_policy(score, contradiction)
            else:
                readiness = "abstain"
        contradictions = [geography_conflict] if geography_conflict else []
        return CapabilityAssessment(
            facility_id=facility_id,
            capability_id=capability_id,
            documentary_support_index=score,
            support_band=band,
            contradiction_state=contradiction,
            evidence_sufficiency=sufficiency,
            decision_readiness=readiness,
            score_factors=factors,
            missing_prerequisites=missing,
            contradictions=contradictions,
            evidence_ids=[item.evidence_id for item in evidence],
            rule_version=demo_data.SCORING_VERSION,
            machine_assessed_at=demo_data.MACHINE_ASSESSED_AT,
        )

    def _missing_prerequisites(
        self, capability_id: CapabilityId, facility: demo_data.DemoFacility
    ) -> list[str]:
        fields = facility["observed_fields"]
        text = str(fields).lower()
        if capability_id == CapabilityId.MATERNAL_EMERGENCY:
            missing = []
            if "gynecologyandobstetrics" not in text and "obstetric" not in text:
                missing.append("obstetrics")
            if "c-section" not in text and "caesarean" not in text and "cesarean" not in text:
                missing.append("c_section")
            return missing
        if capability_id == CapabilityId.EMERGENCY_SURGERY:
            missing = []
            if "emergencymedicine" not in text:
                missing.append("emergency_medicine")
            if "generalsurgery" not in text:
                missing.append("general_surgery")
            return missing
        missing = []
        if "ct scanner" not in text:
            missing.append("ct")
        if "mri scanner" not in text:
            missing.append("mri")
        return missing

    def get_assessment(
        self, facility_id: str, capability_id: CapabilityId
    ) -> CapabilityAssessment | None:
        if facility_id not in demo_data.FACILITY_BY_ID:
            return None
        return self._base_assessment(facility_id, capability_id)

    def get_facility(self, facility_id: str) -> FacilityDetail | None:
        facility = demo_data.FACILITY_BY_ID.get(facility_id)
        if facility is None:
            return None
        return FacilityDetail(
            facility_id=facility_id,
            name=str(facility["name"]),
            description=str(facility["description"]),
            city=str(facility["city"]),
            district=str(facility["district"]),
            state=str(facility["state"]),
            pin=str(facility["pin"]),
            latitude=float(facility["latitude"]),
            longitude=float(facility["longitude"]),
            source_snapshot_id=str(facility["source_snapshot_id"]),
            observed_fields=dict(facility["observed_fields"]),
            assessments=[
                self._base_assessment(facility_id, capability) for capability in CapabilityId
            ],
        )

    def get_evidence(
        self, facility_id: str, capability_id: CapabilityId | None = None
    ) -> list[EvidenceSpan]:
        facility = demo_data.FACILITY_BY_ID.get(facility_id)
        if facility is None:
            return []
        capabilities = [capability_id] if capability_id else list(CapabilityId)
        result: list[EvidenceSpan] = []
        for selected_capability in capabilities:
            assert selected_capability is not None
            for ordinal, (source_field, text) in enumerate(
                demo_data.evidence_texts(facility, selected_capability), start=1
            ):
                result.append(
                    EvidenceSpan(
                        evidence_id=demo_data.evidence_id(
                            facility_id, selected_capability, ordinal
                        ),
                        facility_id=facility_id,
                        capability_id=selected_capability,
                        source_field=source_field,
                        exact_text=text,
                        source_url=None,
                        publisher="Virtue Foundation DAIS 2026 shared catalog",
                        source_family="virtue-dais-2026",
                        retrieval_time=datetime(2026, 7, 19, tzinfo=UTC),
                        extraction_method="deterministic-demo-policy",
                        extraction_version=demo_data.POLICY_VERSION,
                        entity_attribution_confidence=1.0,
                        content_hash=sha256(text.encode()).hexdigest(),
                    )
                )
        return result

    def get_survey_context(self, district_id: str) -> SurveyContext | None:
        if district_id != self.survey_district_id:
            return None
        return SurveyContext.model_validate(demo_data.NFHS_CONTEXT)
