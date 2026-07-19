from __future__ import annotations

from typing import Protocol

from medical_desert.demo_data import DemoFacility
from medical_desert.domain.models import (
    CapabilityAssessment,
    CapabilityId,
    EvidenceSpan,
    FacilityDetail,
    Geography,
    SurveyContext,
)


class AnalyticsPort(Protocol):
    @property
    def source_bundle_id(self) -> str: ...

    @property
    def evidence_snapshot_id(self) -> str: ...

    @property
    def policy_version(self) -> str: ...

    @property
    def scoring_version(self) -> str: ...

    @property
    def survey_district_id(self) -> str: ...

    def list_geographies(self) -> list[Geography]: ...

    def get_geography(self, geography_id: str) -> Geography | None: ...

    def list_facilities(self, geography_id: str) -> list[DemoFacility]: ...

    def get_facility(self, facility_id: str) -> FacilityDetail | None: ...

    def get_assessment(
        self, facility_id: str, capability_id: CapabilityId
    ) -> CapabilityAssessment | None: ...

    def get_evidence(
        self, facility_id: str, capability_id: CapabilityId | None = None
    ) -> list[EvidenceSpan]: ...

    def get_survey_context(self, district_id: str) -> SurveyContext | None: ...


class OperationalStatePort(Protocol):
    def initialize(self) -> None: ...
