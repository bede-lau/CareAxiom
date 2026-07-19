from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class CapabilityId(StrEnum):
    MATERNAL_EMERGENCY = "maternal_emergency_documentation"
    EMERGENCY_SURGERY = "emergency_surgery_documentation"
    ADVANCED_IMAGING = "advanced_imaging_documentation"


class ProductRole(StrEnum):
    PLANNER = "planner"
    REVIEWER = "reviewer"
    ADMINISTRATOR = "administrator"


class IdentityMode(StrEnum):
    FULL_RBAC = "full_rbac"
    SINGLE_TEAM_DEMO = "single_team_demo"


class SupportBand(StrEnum):
    STRONGLY_SUPPORTED = "strongly_supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CLAIM_ONLY_OR_WEAK = "claim_only_or_weak"
    UNSUPPORTED_OR_VERY_WEAK = "unsupported_or_very_weak"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ContradictionState(StrEnum):
    NONE = "none"
    UNRESOLVED = "unresolved"
    CONFIRMED = "confirmed"


class RegionalClassification(StrEnum):
    LOW_SUPPORT_EXTERNAL_VALIDATION = "low_nearby_documentary_support"
    INSUFFICIENT_CORPUS_EVIDENCE = "insufficient_corpus_evidence"
    STRONG_SUPPORT = "strong_nearby_documentary_support"
    MIXED_SIGNAL = "mixed_signal_verification_required"
    UNAVAILABLE = "unavailable_analysis"


class SurveyContextAvailability(StrEnum):
    MATCHED = "matched"
    CROSSWALKED = "crosswalked"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"
    UNAVAILABLE = "unavailable"


class ReviewStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    DEFERRED = "deferred"
    UNRESOLVED = "unresolved"
    SOURCE_ATTACHED = "source_attached"
    REVERSED = "reversed"


class MaterializationState(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    BLOCKED_DEPENDENCY = "blocked_dependency"


class CrisisSourceType(StrEnum):
    LIVE = "live"
    UPLOADED = "uploaded"
    DEMO = "demo"


class GeographyType(StrEnum):
    STATE = "state"
    DISTRICT = "district"
    CITY = "city"
    PIN = "pin"
    MAP_AREA = "map_area"


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"
    UNTRUSTED_ACTOR = "untrusted_actor"
    IDEMPOTENCY_KEY_REQUIRED = "idempotency_key_required"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    VERSION_CONFLICT = "version_conflict"
    CAPABILITY_DISABLED = "capability_disabled"
    OPTIONAL_SERVICE_UNAVAILABLE = "optional_service_unavailable"
    INTERNAL_ERROR = "internal_error"


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class Actor(APIModel):
    actor_id: str
    display_name: str
    roles: list[ProductRole]
    trusted: bool = True
    identity_mode: IdentityMode


class Capability(APIModel):
    capability_id: CapabilityId
    label: str
    description: str
    default_radius_km: int
    radius_presets_km: list[int]
    policy_version: str


class Geography(APIModel):
    geography_id: str
    geography_type: GeographyType
    name: str
    state: str | None = None
    district: str | None = None
    pin: str | None = None
    selectable: bool = True
    unavailable_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSpan(APIModel):
    evidence_id: str
    facility_id: str
    capability_id: CapabilityId
    source_field: str
    exact_text: str
    source_url: HttpUrl | None = None
    publisher: str
    source_family: str
    publication_time: datetime | None = None
    valid_time: datetime | None = None
    retrieval_time: datetime | None = None
    extraction_method: str
    extraction_version: str
    entity_attribution_confidence: float = Field(ge=0, le=1)
    polarity: Literal["positive", "negative", "uncertain"] = "positive"
    content_hash: str


class ExternalEvidenceItem(APIModel):
    url: HttpUrl
    title: str | None = None
    excerpt: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    provider_request_id: str | None = None


class ExternalVerificationResult(APIModel):
    verification_item_id: str
    mode: Literal["cached", "live"]
    query: str
    results: list[ExternalEvidenceItem]
    limitation: str
    trace_id: str


class ScoreFactors(APIModel):
    direct_evidence_specificity: int = Field(ge=0, le=30)
    independent_source_corroboration: int = Field(ge=0, le=20)
    source_quality: int = Field(ge=0, le=15)
    entity_attribution_quality: int = Field(ge=0, le=15)
    freshness: int = Field(ge=0, le=10)
    prerequisite_support: int = Field(ge=0, le=10)

    @property
    def total(self) -> int:
        return sum(self.model_dump().values())


class CapabilityAssessment(APIModel):
    facility_id: str
    capability_id: CapabilityId
    documentary_support_index: int | None = Field(default=None, ge=0, le=100)
    support_band: SupportBand
    contradiction_state: ContradictionState
    evidence_sufficiency: Literal["sufficient", "limited", "insufficient"]
    decision_readiness: Literal["ready", "review_required", "abstain"]
    score_factors: ScoreFactors | None = None
    missing_prerequisites: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    rule_version: str
    machine_assessed_at: datetime
    human_reviewed_verdict: SupportBand | None = None
    human_review_reason: str | None = None
    review_version: int = 0


class FacilitySummary(APIModel):
    facility_id: str
    name: str
    city: str | None = None
    district: str | None = None
    state: str
    pin: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_snapshot_id: str
    assessment: CapabilityAssessment
    distance_km: float | None = None
    contribution_reason: str


class FacilityDetail(APIModel):
    facility_id: str
    name: str
    description: str
    city: str | None = None
    district: str | None = None
    state: str
    pin: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_snapshot_id: str
    observed_fields: dict[str, Any]
    assessments: list[CapabilityAssessment]
    review_history: list[dict[str, Any]] = Field(default_factory=list)


class AssessabilityComponent(APIModel):
    component: str
    rate: float = Field(ge=0, le=1)
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    weight: float


class Assessability(APIModel):
    observed_record_assessability: float = Field(ge=0, le=1)
    components: list[AssessabilityComponent]
    n_source_rows: int
    n_structurally_eligible_rows: int
    n_canonical_facility_entities: int
    n_region_entities: int
    n_capability_assessed_entities: int
    source_bundle_version: str
    statement: str = (
        "Observed-record assessability describes the supplied corpus only; "
        "it does not estimate the real facility universe."
    )


class SurveyIndicator(APIModel):
    indicator_id: str
    label: str
    raw_value: str
    numeric_value: float | None = None
    qualifier: Literal["standard", "low_sample_25_49", "suppressed_lt_25", "unparseable"]
    unit: str = "percent"
    survey_period: str = "2019-2021"
    source_version: str = "NFHS-5"


class SurveyContext(APIModel):
    district_id: str
    district: str
    state: str
    survey_context_availability: SurveyContextAvailability
    indicators: list[SurveyIndicator]
    crosswalk_version: str
    limitations: list[str]


class DocumentaryQuery(APIModel):
    capability_id: CapabilityId
    geography_id: str
    radius_km: Literal[10, 25, 50] = 25
    include_facilities: bool = True
    map_bounds: list[float] | None = None

    @field_validator("map_bounds")
    @classmethod
    def validate_bounds(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and len(value) != 4:
            raise ValueError("map_bounds must contain west, south, east, north")
        return value


class DocumentaryQueryResult(APIModel):
    result_id: str
    capability_id: CapabilityId
    geography: Geography
    radius_km: int
    distance_method: Literal["straight_line"] = "straight_line"
    classification: RegionalClassification
    classification_label: str
    observed_record_assessability: Assessability
    distinct_observed_facilities: int
    qualifying_facilities: int
    contradiction_count: int
    excluded_counts: dict[str, int]
    nearest_qualifying_distance_km: float | None = None
    facilities: list[FacilitySummary]
    survey_context: SurveyContext | None = None
    planning_priority_candidate: bool
    external_validation_required: bool = True
    medical_desert_candidate_enabled: bool = False
    assumptions: list[str]
    source_bundle_id: str
    policy_version: str
    materialization_version: int
    materialization_state: MaterializationState
    trace_id: str
    generated_at: datetime


class OverrideRequest(APIModel):
    capability_id: CapabilityId
    verdict: SupportBand
    contradiction_state: ContradictionState
    reason: str = Field(min_length=8, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1)
    expected_review_version: int = Field(ge=0)


class VerificationItemCreate(APIModel):
    facility_id: str
    capability_id: CapabilityId
    question: str = Field(min_length=5, max_length=1000)
    why_it_matters: str = Field(min_length=5, max_length=2000)
    affected_region_ids: list[str] = Field(default_factory=list)
    affected_scenario_ids: list[str] = Field(default_factory=list)
    classification_flip_potential: float = Field(ge=0, le=1)
    map_cells_or_regions_affected: float = Field(ge=0, le=1)
    active_scenario_references: float = Field(ge=0, le=1)
    evidence_staleness: float = Field(ge=0, le=1)
    unresolved_contradiction_severity: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    recommended_action: str


class VerificationDecision(APIModel):
    status: ReviewStatus
    reason: str = Field(min_length=8, max_length=2000)
    corrected_verdict: SupportBand | None = None
    contradiction_state: ContradictionState | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    expected_version: int = Field(ge=1)


class VerificationItem(APIModel):
    item_id: str
    facility_id: str
    capability_id: CapabilityId
    question: str
    why_it_matters: str
    affected_region_ids: list[str]
    affected_scenario_ids: list[str]
    priority: float = Field(ge=0, le=1)
    priority_version: str
    impact_proxy_label: str
    evidence_ids: list[str]
    recommended_action: str
    owner_id: str | None = None
    status: ReviewStatus
    version: int
    created_at: datetime
    updated_at: datetime


class ScenarioCreate(APIModel):
    name: str = Field(min_length=1, max_length=200)
    capability_id: CapabilityId
    geography_id: str
    radius_km: Literal[10, 25, 50] = 25
    map_extent: list[float] | None = None
    selected_region_ids: list[str] = Field(default_factory=list)
    shortlisted_facility_ids: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=10000)
    decision_rationale: str = Field(default="", max_length=10000)
    collaborators: list[str] = Field(default_factory=list)


class ScenarioUpdate(ScenarioCreate):
    expected_version: int = Field(ge=1)


class Scenario(APIModel):
    scenario_id: str
    name: str
    owner_id: str
    collaborators: list[str]
    capability_id: CapabilityId
    geography_id: str
    radius_km: int
    map_extent: list[float] | None
    selected_region_ids: list[str]
    shortlisted_facility_ids: list[str]
    notes: str
    decision_rationale: str
    machine_score_version: str
    human_review_version: int
    dataset_snapshot_id: str
    evidence_snapshot_id: str
    saved_result: DocumentaryQueryResult
    version: int
    created_at: datetime
    updated_at: datetime


class ScenarioChange(APIModel):
    changed_field: str
    prior_version: str
    current_version: str
    reason: str
    affected_result_ids: list[str]


class CrisisAnalyzeRequest(APIModel):
    incident_id: str
    name: str
    source_type: CrisisSourceType
    source_time: datetime
    last_refresh: datetime
    geometry: dict[str, Any]
    capability_id: CapabilityId
    geography_id: str
    radius_km: Literal[10, 25, 50] = 25


class CrisisAnalysis(APIModel):
    incident_id: str
    source_type: CrisisSourceType
    source_time: datetime
    last_refresh: datetime
    analysis: DocumentaryQueryResult
    planning_summary: str
    limitations: list[str]


class ReferralRequest(APIModel):
    capability_id: CapabilityId
    geography_id: str
    radius_km: Literal[10, 25, 50] = 25
    maximum_results: int = Field(default=5, ge=1, le=10)
    scenario_id: str | None = None


class ReferralShortlist(APIModel):
    facilities: list[FacilitySummary]
    distance_method: Literal["straight_line"] = "straight_line"
    availability_statement: str = (
        "Current service availability, staffing, capacity, and patient acceptance "
        "must be confirmed outside this application."
    )
    evidence_snapshot_id: str


class HealthComponent(APIModel):
    status: Literal["healthy", "degraded", "disabled", "unavailable"]
    detail: str


class HealthResponse(APIModel):
    status: Literal["healthy", "degraded"]
    product: str = "Medical Desert Planner"
    version: str
    components: dict[str, HealthComponent]
    dataset_snapshot_version: str
    identity_mode: IdentityMode
    timestamp: datetime


class ErrorBody(APIModel):
    code: ErrorCode
    message: str
    recovery: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str
