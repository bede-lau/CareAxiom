from __future__ import annotations

import csv
import io
import json
import math
from hashlib import sha256
from typing import Any
from uuid import uuid4

from medical_desert import __version__, demo_data
from medical_desert.application.errors import ApplicationError
from medical_desert.config.settings import Settings, load_yaml_config
from medical_desert.domain.models import (
    Actor,
    Capability,
    CapabilityAssessment,
    CapabilityId,
    ContradictionState,
    CrisisAnalysis,
    CrisisAnalyzeRequest,
    DocumentaryQuery,
    DocumentaryQueryResult,
    ErrorCode,
    ExternalEvidenceItem,
    ExternalVerificationResult,
    FacilityDetail,
    FacilitySummary,
    HealthComponent,
    HealthResponse,
    MaterializationState,
    OverrideRequest,
    ProductRole,
    ReferralRequest,
    ReferralShortlist,
    ReviewStatus,
    Scenario,
    ScenarioChange,
    ScenarioCreate,
    ScenarioUpdate,
    SupportBand,
    VerificationDecision,
    VerificationItem,
    VerificationItemCreate,
    utc_now,
)
from medical_desert.identity.authorization import require_role, require_scenario_access
from medical_desert.persistence.errors import (
    IdempotencyConflict,
    RecordNotFound,
    VersionConflict,
)
from medical_desert.persistence.sqlite import SQLiteOperationalStore
from medical_desert.ports.analytics import AnalyticsPort
from medical_desert.ports.external import SQLQueryPort, TracingPort, WebVerificationPort
from medical_desert.scoring.engine import (
    AssessabilityInputs,
    calculate_assessability,
    classify_region,
    verification_priority,
)


def request_hash(payload: Any) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def spreadsheet_safe_cell(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return f"'{value}" if value.lstrip().startswith(("=", "+", "-", "@")) else value


class MedicalDesertService:
    def __init__(
        self,
        settings: Settings,
        analytics: AnalyticsPort,
        store: SQLiteOperationalStore,
        tracing: TracingPort,
        web_verification: WebVerificationPort | None = None,
        sql_query: SQLQueryPort | None = None,
    ) -> None:
        self.settings = settings
        self.analytics = analytics
        self.store = store
        self.tracing = tracing
        self.web_verification = web_verification
        self.sql_query = sql_query
        self._trace_canary_id: str | None = None
        self._trace_error: str | None = None
        self._sql_canary_ok: bool | None = None
        self._sql_error: str | None = None
        self.capability_config = load_yaml_config("capabilities.yaml")

    def materialize_pending_events(self) -> dict[str, int]:
        if self.settings.environment == "local":
            return self.store.process_pending_outbox(lambda _event: None)
        if self.sql_query is None:
            return self.store.outbox_summary()
        return self.store.process_pending_outbox(self._materialize_outbox_event)

    def _materialize_outbox_event(self, event: dict[str, Any]) -> None:
        if self.sql_query is None:
            raise RuntimeError("Databricks SQL is required for production materialization.")
        catalog = self.settings.project_catalog
        payload = event["payload"]
        if event["event_type"] == "facility_review_changed":
            self.sql_query.execute(
                f"""
                MERGE INTO `{catalog}`.`gold`.`facility_review_overlay` target
                USING (
                  SELECT
                    CAST(? AS STRING) AS review_id,
                    CAST(? AS STRING) AS source_bundle_id,
                    CAST(? AS STRING) AS facility_id,
                    CAST(? AS STRING) AS capability_id,
                    CAST(? AS STRING) AS verdict,
                    CAST(? AS STRING) AS contradiction_state,
                    CAST(? AS STRING) AS reason,
                    CAST(? AS STRING) AS evidence_ids_json,
                    CAST(? AS STRING) AS actor_id,
                    CAST(? AS BIGINT) AS review_version,
                    CAST(? AS STRING) AS review_status,
                    CAST(? AS TIMESTAMP) AS reviewed_at
                ) source
                ON target.review_id = source.review_id
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
                """,
                [
                    payload["review_id"],
                    self.analytics.source_bundle_id,
                    payload["facility_id"],
                    payload["capability_id"],
                    payload.get("verdict"),
                    payload.get("contradiction_state"),
                    payload["reason"],
                    json.dumps(payload.get("evidence_ids", []), separators=(",", ":")),
                    payload["actor_id"],
                    payload["version"],
                    payload["status"],
                    payload["created_at"],
                ],
            )
        self.sql_query.execute(
            f"""
            MERGE INTO `{catalog}`.`gold`.`operational_event_materialization` target
            USING (
              SELECT
                CAST(? AS STRING) AS event_id,
                CAST(? AS STRING) AS source_bundle_id,
                CAST(? AS STRING) AS stream_id,
                CAST(? AS BIGINT) AS sequence_number,
                CAST(? AS STRING) AS event_type,
                CAST(? AS STRING) AS payload_json,
                current_timestamp() AS materialized_at
            ) source
            ON target.event_id = source.event_id
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
            """,
            [
                event["event_id"],
                self.analytics.source_bundle_id,
                event["stream_id"],
                event["sequence_number"],
                event["event_type"],
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
            ],
        )

    def _record_trace(self, name: str, attributes: dict[str, Any]) -> str:
        try:
            trace_id = self.tracing.record(name, attributes)
            self._trace_canary_id = trace_id
            self._trace_error = None
            return trace_id
        except Exception as error:
            self._trace_error = type(error).__name__
            return f"unpersisted:{self.tracing.trace_id()}"

    def capabilities(self) -> list[Capability]:
        scoring = load_yaml_config("scoring.yaml")
        radii = scoring["regional"]["radius_presets_km"]
        return [
            Capability(
                capability_id=CapabilityId(capability_id),
                label=policy["label"],
                description=policy["description"],
                default_radius_km=policy["default_radius_km"],
                radius_presets_km=radii,
                policy_version=self.capability_config["version"],
            )
            for capability_id, policy in self.capability_config["policies"].items()
        ]

    def _overlay_review(self, assessment: CapabilityAssessment) -> CapabilityAssessment:
        review = self.store.current_review(assessment.facility_id, assessment.capability_id)
        if review is None:
            return assessment
        updated = assessment.model_copy(deep=True)
        if review["verdict"]:
            updated.human_reviewed_verdict = SupportBand(review["verdict"])
            updated.human_review_reason = str(review["reason"])
        if review["contradiction_state"]:
            updated.contradiction_state = ContradictionState(review["contradiction_state"])
        updated.review_version = int(review["version"])
        return updated

    def facility(self, facility_id: str) -> FacilityDetail:
        facility = self.analytics.get_facility(facility_id)
        if facility is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Facility was not found.",
                "Refresh the facility list and retry with a current identifier.",
                status_code=404,
            )
        facility.assessments = [self._overlay_review(item) for item in facility.assessments]
        facility.review_history = self.store.review_history(facility_id)
        return facility

    def evidence(self, facility_id: str, capability_id: CapabilityId | None) -> list[Any]:
        if self.analytics.get_facility(facility_id) is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Facility was not found.",
                "Refresh the facility list and retry with a current identifier.",
                status_code=404,
            )
        return self.analytics.get_evidence(facility_id, capability_id)

    def _distance(self, facility: demo_data.DemoFacility, geography: Any) -> float | None:
        if facility["geography_conflict"]:
            return None
        if geography.geography_id.startswith("pin:") and facility["pin"] != geography.pin:
            return None
        origin_latitude = geography.metadata.get(
            "postal_reference_latitude", demo_data.DARbhanga_CENTER[0]
        )
        origin_longitude = geography.metadata.get(
            "postal_reference_longitude", demo_data.DARbhanga_CENTER[1]
        )
        return haversine_km(
            float(origin_latitude),
            float(origin_longitude),
            float(facility["latitude"]),
            float(facility["longitude"]),
        )

    def query(self, query: DocumentaryQuery) -> DocumentaryQueryResult:
        geography = self.analytics.get_geography(query.geography_id)
        if geography is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Geography was not found.",
                "Use an identifier returned by /api/geographies.",
                status_code=404,
            )
        if not geography.selectable:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "The selected geography is not enabled.",
                geography.unavailable_reason or "Select an enabled geography.",
                status_code=422,
            )
        source_facilities = self.analytics.list_facilities(query.geography_id)
        summaries: list[FacilitySummary] = []
        qualifying = 0
        contradiction_count = 0
        freshness_known = 0
        review_versions: list[int] = []
        materialization_states: list[MaterializationState] = []
        nearest: float | None = None
        excluded = {
            "geography_conflict": 0,
            "outside_radius": 0,
            "insufficient_evidence": 0,
        }
        for facility in source_facilities:
            assessment = self.analytics.get_assessment(
                str(facility["facility_id"]), query.capability_id
            )
            assert assessment is not None
            assessment = self._overlay_review(assessment)
            review_versions.append(assessment.review_version)
            if assessment.review_version > 0:
                materialization_states.append(
                    self.store.review_materialization_state(
                        assessment.facility_id,
                        assessment.capability_id,
                    )
                )
            if assessment.contradiction_state != ContradictionState.NONE:
                contradiction_count += 1
            distance = self._distance(facility, geography)
            if facility["geography_conflict"]:
                excluded["geography_conflict"] += 1
                reason = "Excluded: unresolved high-severity geography conflict."
            elif distance is None or distance > query.radius_km:
                excluded["outside_radius"] += 1
                reason = "Observed record is outside the selected straight-line radius."
            elif assessment.support_band == SupportBand.INSUFFICIENT_EVIDENCE:
                excluded["insufficient_evidence"] += 1
                reason = "Observed record has insufficient capability evidence."
            else:
                reason = "Observed record contributes documentary evidence within the radius."
            effective_band = assessment.human_reviewed_verdict or assessment.support_band
            is_qualifying = (
                distance is not None
                and distance <= query.radius_km
                and effective_band
                in {SupportBand.STRONGLY_SUPPORTED, SupportBand.PARTIALLY_SUPPORTED}
                and assessment.contradiction_state != ContradictionState.CONFIRMED
            )
            if is_qualifying:
                assert distance is not None
                qualifying += 1
                nearest = distance if nearest is None else min(nearest, distance)
            if facility["observed_fields"].get("capabilities"):
                freshness_known += 1
            if query.include_facilities:
                summaries.append(
                    FacilitySummary(
                        facility_id=str(facility["facility_id"]),
                        name=str(facility["name"]),
                        city=str(facility["city"]),
                        district=str(facility["district"]),
                        state=str(facility["state"]),
                        pin=str(facility["pin"]),
                        latitude=float(facility["latitude"]),
                        longitude=float(facility["longitude"]),
                        source_snapshot_id=str(facility["source_snapshot_id"]),
                        assessment=assessment,
                        distance_km=round(distance, 2) if distance is not None else None,
                        contribution_reason=reason,
                    )
                )
        n_region = len(source_facilities)
        assessability = calculate_assessability(
            AssessabilityInputs(
                n_source_rows=n_region,
                n_structurally_eligible_rows=n_region,
                n_canonical_facility_entities=n_region,
                n_region_entities=n_region,
                n_capability_assessed_entities=n_region,
                geography_resolved=n_region - excluded["geography_conflict"],
                traceable_sources=n_region,
                freshness_known=freshness_known,
                unresolved_contradictions=excluded["geography_conflict"],
                ambiguous_geography=excluded["geography_conflict"],
                source_bundle_version=self.analytics.source_bundle_id,
            )
        )
        classification = classify_region(qualifying, assessability.observed_record_assessability)
        survey = (
            self.analytics.get_survey_context(self.analytics.survey_district_id)
            if geography.district == self.settings.focus_district
            or geography.geography_type.value == "district"
            else None
        )
        materialization_version = max(review_versions, default=0)
        materialization_state = MaterializationState.APPLIED
        for state in (
            MaterializationState.BLOCKED_DEPENDENCY,
            MaterializationState.FAILED,
            MaterializationState.PENDING,
        ):
            if state in materialization_states:
                materialization_state = state
                break
        result_seed = {
            "capability": query.capability_id.value,
            "geography": query.geography_id,
            "radius": query.radius_km,
            "reviews": review_versions,
            "snapshot": self.analytics.source_bundle_id,
        }
        result_id = f"result-{request_hash(result_seed)[:16]}"
        labels = {
            "strong_nearby_documentary_support": "Strong nearby documentary support",
            "low_nearby_documentary_support": (
                "Low nearby documentary support; external validation required"
            ),
            "mixed_signal_verification_required": "Mixed signal; verification required",
            "insufficient_corpus_evidence": "Insufficient corpus evidence",
            "unavailable_analysis": "Unavailable analysis",
        }
        summaries.sort(
            key=lambda item: (
                item.distance_km is None,
                item.distance_km if item.distance_km is not None else float("inf"),
                item.name,
            )
        )
        trace_id = self._record_trace(
            "planner.documentary_query",
            {
                "result_id": result_id,
                "capability_id": query.capability_id.value,
                "geography_id": query.geography_id,
                "radius_km": query.radius_km,
                "classification": classification.value,
                "observed_facilities": n_region,
                "qualifying_facilities": qualifying,
                "source_bundle_id": self.analytics.source_bundle_id,
                "policy_version": self.analytics.policy_version,
            },
        )
        return DocumentaryQueryResult(
            result_id=result_id,
            capability_id=query.capability_id,
            geography=geography,
            radius_km=query.radius_km,
            classification=classification,
            classification_label=labels[classification.value],
            observed_record_assessability=assessability,
            distinct_observed_facilities=n_region,
            qualifying_facilities=qualifying,
            contradiction_count=contradiction_count,
            excluded_counts=excluded,
            nearest_qualifying_distance_km=round(nearest, 2) if nearest is not None else None,
            facilities=summaries,
            survey_context=survey,
            planning_priority_candidate=(classification.value == "low_nearby_documentary_support"),
            assumptions=[
                (
                    f"{query.radius_km} km straight-line radius is a planning assumption, "
                    "not a medical standard."
                ),
                "Postal references are not PIN centroids, boundaries, or population origins.",
                (
                    "Documentary support does not prove current staffing, capacity, "
                    "readiness, or availability."
                ),
                "NFHS context is separate and does not affect this classification.",
            ],
            source_bundle_id=self.analytics.source_bundle_id,
            policy_version=self.analytics.policy_version,
            materialization_version=materialization_version,
            materialization_state=materialization_state,
            trace_id=trace_id,
            generated_at=utc_now(),
        )

    def external_verification(
        self,
        item_id: str,
        actor: Actor,
    ) -> ExternalVerificationResult:
        require_role(actor, ProductRole.PLANNER, ProductRole.REVIEWER, ProductRole.ADMINISTRATOR)
        item = self.store.get_verification_item(item_id)
        if item is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Verification item was not found.",
                "Refresh the verification queue and retry.",
                status_code=404,
            )
        if self.web_verification is None:
            raise ApplicationError(
                ErrorCode.CAPABILITY_DISABLED,
                "External verification is disabled.",
                "Enable cached or live Tavily mode for reviewer-triggered verification.",
                status_code=404,
            )
        facility = self.analytics.get_facility(item.facility_id)
        if facility is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Facility was not found.",
                "Refresh the verification queue and retry.",
                status_code=404,
            )
        capability = self.capability_config["policies"][item.capability_id.value]["label"]
        location = ", ".join(
            value for value in (facility.city, facility.district, facility.state) if value
        )
        query = f'"{facility.name}" "{location}" {capability} official facility source'
        raw_results = self.web_verification.search(query)
        results = [
            ExternalEvidenceItem(
                url=str(result["url"]),
                title=str(result["title"]) if result.get("title") else None,
                excerpt=str(result["content"]) if result.get("content") else None,
                score=float(result["score"]) if result.get("score") is not None else None,
                provider_request_id=(
                    str(result["request_id"]) if result.get("request_id") else None
                ),
            )
            for result in raw_results
        ]
        trace_id = self._record_trace(
            "verification.external_search",
            {
                "verification_item_id": item.item_id,
                "facility_id": item.facility_id,
                "capability_id": item.capability_id.value,
                "mode": self.settings.tavily_mode,
                "result_count": len(results),
            },
        )
        limitation = (
            "Cached mode made no external request."
            if self.settings.tavily_mode != "live"
            else (
                "External results are unverified leads. A reviewer must confirm facility "
                "attribution, source quality, and current validity."
            )
        )
        return ExternalVerificationResult(
            verification_item_id=item.item_id,
            mode="live" if self.settings.tavily_mode == "live" else "cached",
            query=query,
            results=results,
            limitation=limitation,
            trace_id=trace_id,
        )

    def override(
        self,
        facility_id: str,
        payload: OverrideRequest,
        actor: Actor,
        idempotency_key: str,
        request_id: str,
    ) -> dict[str, Any]:
        require_role(actor, ProductRole.REVIEWER, ProductRole.ADMINISTRATOR)
        if self.analytics.get_facility(facility_id) is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Facility was not found.",
                "Refresh the facility list and retry.",
                status_code=404,
            )
        try:
            result = self.store.execute_idempotent(
                actor=actor,
                operation=f"facility_override:{facility_id}",
                idempotency_key=idempotency_key,
                request_hash=request_hash(payload),
                request_id=request_id,
                callback=lambda connection: self.store.append_review(
                    connection,
                    facility_id=facility_id,
                    capability_id=payload.capability_id,
                    verdict=payload.verdict,
                    contradiction_state=payload.contradiction_state,
                    reason=payload.reason,
                    evidence_ids=payload.evidence_ids,
                    status=ReviewStatus.CORRECTED,
                    expected_version=payload.expected_review_version,
                    actor=actor,
                    request_id=request_id,
                ),
            )
            self.materialize_pending_events()
            return result
        except (VersionConflict, IdempotencyConflict) as error:
            self._raise_persistence(error)
        raise AssertionError("unreachable")

    def bootstrap_verification_queue(self, actor: Actor) -> None:
        for fixture in demo_data.default_geography_review_items():
            payload = VerificationItemCreate.model_validate(fixture)
            key = f"bootstrap-geography-{payload.facility_id}"
            try:
                self.create_verification_item(payload, actor, key, "startup")
            except ApplicationError as error:
                if error.code not in {ErrorCode.IDEMPOTENCY_CONFLICT, ErrorCode.NOT_FOUND}:
                    raise

    def create_verification_item(
        self,
        payload: VerificationItemCreate,
        actor: Actor,
        idempotency_key: str,
        request_id: str,
    ) -> VerificationItem:
        require_role(actor, ProductRole.PLANNER, ProductRole.REVIEWER, ProductRole.ADMINISTRATOR)
        if self.analytics.get_facility(payload.facility_id) is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Facility was not found.",
                "Use a facility identifier returned by the planner.",
                status_code=404,
            )
        priority = verification_priority(
            payload.classification_flip_potential,
            payload.map_cells_or_regions_affected,
            payload.active_scenario_references,
            payload.evidence_staleness,
            payload.unresolved_contradiction_severity,
        )
        now = utc_now()
        item = VerificationItem(
            item_id=f"verify-{uuid4()}",
            facility_id=payload.facility_id,
            capability_id=payload.capability_id,
            question=payload.question,
            why_it_matters=payload.why_it_matters,
            affected_region_ids=payload.affected_region_ids,
            affected_scenario_ids=payload.affected_scenario_ids,
            priority=priority,
            priority_version="verification-priority-2026-07-19",
            impact_proxy_label=(
                "Affected origins or regions; no population denominator is configured."
            ),
            evidence_ids=payload.evidence_ids,
            recommended_action=payload.recommended_action,
            status=ReviewStatus.OPEN,
            version=1,
            created_at=now,
            updated_at=now,
        )
        try:
            result = self.store.execute_idempotent(
                actor=actor,
                operation="verification_item_create",
                idempotency_key=idempotency_key,
                request_hash=request_hash(payload),
                request_id=request_id,
                callback=lambda connection: self.store.create_verification_item(
                    connection, item, actor, request_id
                ),
            )
            return VerificationItem.model_validate(result)
        except IdempotencyConflict as error:
            self._raise_persistence(error)
        raise AssertionError("unreachable")

    def decide_verification_item(
        self,
        item_id: str,
        payload: VerificationDecision,
        actor: Actor,
        idempotency_key: str,
        request_id: str,
    ) -> VerificationItem:
        require_role(actor, ProductRole.REVIEWER, ProductRole.ADMINISTRATOR)
        item = self.store.get_verification_item(item_id)
        if item is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Verification item was not found.",
                "Refresh the queue and retry.",
                status_code=404,
            )
        updated = item.model_copy(
            update={
                "status": payload.status,
                "owner_id": actor.actor_id,
                "version": item.version + 1,
                "updated_at": utc_now(),
            }
        )

        def commit(connection: Any) -> dict[str, Any]:
            document = self.store.update_verification_item(
                connection, updated, payload.expected_version, actor, request_id
            )
            if payload.corrected_verdict or payload.contradiction_state:
                current = self.store.current_review(item.facility_id, item.capability_id)
                expected_review = int(current["version"]) if current else 0
                self.store.append_review(
                    connection,
                    facility_id=item.facility_id,
                    capability_id=item.capability_id,
                    verdict=payload.corrected_verdict,
                    contradiction_state=payload.contradiction_state,
                    reason=payload.reason,
                    evidence_ids=payload.evidence_ids,
                    status=payload.status,
                    expected_version=expected_review,
                    actor=actor,
                    request_id=request_id,
                )
            return document

        try:
            result = self.store.execute_idempotent(
                actor=actor,
                operation=f"verification_item_decision:{item_id}",
                idempotency_key=idempotency_key,
                request_hash=request_hash(payload),
                request_id=request_id,
                callback=commit,
            )
            self.materialize_pending_events()
            return VerificationItem.model_validate(result)
        except (VersionConflict, IdempotencyConflict, RecordNotFound) as error:
            self._raise_persistence(error)
        raise AssertionError("unreachable")

    def create_scenario(
        self,
        payload: ScenarioCreate,
        actor: Actor,
        idempotency_key: str,
        request_id: str,
    ) -> Scenario:
        require_role(actor, ProductRole.PLANNER, ProductRole.REVIEWER, ProductRole.ADMINISTRATOR)
        if actor.identity_mode.value == "single_team_demo" and payload.collaborators:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Collaboration is disabled in single-team demo mode.",
                "Create the scenario without collaborators.",
                status_code=422,
            )
        result = self.query(
            DocumentaryQuery(
                capability_id=payload.capability_id,
                geography_id=payload.geography_id,
                radius_km=payload.radius_km,
            )
        )
        now = utc_now()
        scenario = Scenario(
            scenario_id=f"scenario-{uuid4()}",
            name=payload.name,
            owner_id=actor.actor_id,
            collaborators=payload.collaborators,
            capability_id=payload.capability_id,
            geography_id=payload.geography_id,
            radius_km=payload.radius_km,
            map_extent=payload.map_extent,
            selected_region_ids=payload.selected_region_ids,
            shortlisted_facility_ids=payload.shortlisted_facility_ids,
            notes=payload.notes,
            decision_rationale=payload.decision_rationale,
            machine_score_version=self.analytics.scoring_version,
            human_review_version=result.materialization_version,
            dataset_snapshot_id=self.analytics.source_bundle_id,
            evidence_snapshot_id=self.analytics.evidence_snapshot_id,
            saved_result=result,
            version=1,
            created_at=now,
            updated_at=now,
        )
        try:
            stored = self.store.execute_idempotent(
                actor=actor,
                operation="scenario_create",
                idempotency_key=idempotency_key,
                request_hash=request_hash(payload),
                request_id=request_id,
                callback=lambda connection: self.store.create_scenario(
                    connection, scenario, actor, request_id
                ),
            )
            return Scenario.model_validate(stored)
        except IdempotencyConflict as error:
            self._raise_persistence(error)
        raise AssertionError("unreachable")

    def update_scenario(
        self,
        scenario_id: str,
        payload: ScenarioUpdate,
        actor: Actor,
        idempotency_key: str,
        request_id: str,
    ) -> Scenario:
        current = self.get_scenario(scenario_id, actor)
        require_scenario_access(actor, current, write=True)
        if actor.identity_mode.value == "single_team_demo" and payload.collaborators:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Collaboration is disabled in single-team demo mode.",
                "Remove collaborators and retry.",
                status_code=422,
            )
        result = self.query(
            DocumentaryQuery(
                capability_id=payload.capability_id,
                geography_id=payload.geography_id,
                radius_km=payload.radius_km,
            )
        )
        updated = current.model_copy(
            update={
                "name": payload.name,
                "collaborators": payload.collaborators,
                "capability_id": payload.capability_id,
                "geography_id": payload.geography_id,
                "radius_km": payload.radius_km,
                "map_extent": payload.map_extent,
                "selected_region_ids": payload.selected_region_ids,
                "shortlisted_facility_ids": payload.shortlisted_facility_ids,
                "notes": payload.notes,
                "decision_rationale": payload.decision_rationale,
                "machine_score_version": self.analytics.scoring_version,
                "human_review_version": result.materialization_version,
                "dataset_snapshot_id": self.analytics.source_bundle_id,
                "evidence_snapshot_id": self.analytics.evidence_snapshot_id,
                "saved_result": result,
                "version": current.version + 1,
                "updated_at": utc_now(),
            }
        )
        try:
            stored = self.store.execute_idempotent(
                actor=actor,
                operation=f"scenario_update:{scenario_id}",
                idempotency_key=idempotency_key,
                request_hash=request_hash(payload),
                request_id=request_id,
                callback=lambda connection: self.store.update_scenario(
                    connection,
                    updated,
                    payload.expected_version,
                    actor,
                    request_id,
                ),
            )
            return Scenario.model_validate(stored)
        except (VersionConflict, IdempotencyConflict, RecordNotFound) as error:
            self._raise_persistence(error)
        raise AssertionError("unreachable")

    def get_scenario(self, scenario_id: str, actor: Actor) -> Scenario:
        scenario = self.store.get_scenario(scenario_id)
        if scenario is None:
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "Scenario was not found.",
                "Refresh the scenario list and retry.",
                status_code=404,
            )
        require_scenario_access(actor, scenario)
        return scenario

    def scenario_changes(self, scenario_id: str, actor: Actor) -> list[ScenarioChange]:
        scenario = self.get_scenario(scenario_id, actor)
        current = self.query(
            DocumentaryQuery(
                capability_id=scenario.capability_id,
                geography_id=scenario.geography_id,
                radius_km=scenario.radius_km,
            )
        )
        changes: list[ScenarioChange] = []
        comparisons = [
            (
                "classification",
                scenario.saved_result.classification.value,
                current.classification.value,
                "Current evidence or review state changed the regional classification.",
            ),
            (
                "qualifying_facilities",
                str(scenario.saved_result.qualifying_facilities),
                str(current.qualifying_facilities),
                "Current facility verdicts changed the qualifying count.",
            ),
            (
                "human_review_version",
                str(scenario.human_review_version),
                str(current.materialization_version),
                "A newer review decision exists.",
            ),
        ]
        for field, prior, latest, reason in comparisons:
            if prior != latest:
                changes.append(
                    ScenarioChange(
                        changed_field=field,
                        prior_version=prior,
                        current_version=latest,
                        reason=reason,
                        affected_result_ids=[
                            scenario.saved_result.result_id,
                            current.result_id,
                        ],
                    )
                )
        return changes

    def export_json(self, scenario_id: str, actor: Actor) -> str:
        scenario = self.get_scenario(scenario_id, actor)
        citations = sorted(
            {
                evidence_id
                for facility in scenario.saved_result.facilities
                for evidence_id in facility.assessment.evidence_ids
            }
        )
        payload = {
            "scenario_id": scenario.scenario_id,
            "assumptions": scenario.saved_result.assumptions,
            "citations": citations,
            "uncertainty": scenario.saved_result.assumptions,
            "source_bundle_id": scenario.dataset_snapshot_id,
            "policy_version": scenario.saved_result.policy_version,
            "saved_snapshot_version": scenario.evidence_snapshot_id,
            "facility_ids": [
                facility.facility_id for facility in scenario.saved_result.facilities
            ],
            "result_classification": scenario.saved_result.classification.value,
            "scenario": scenario.model_dump(mode="json"),
            "changes": [
                item.model_dump(mode="json") for item in self.scenario_changes(scenario_id, actor)
            ],
            "planning_only": True,
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    def export_csv(self, scenario_id: str, actor: Actor) -> str:
        scenario = self.get_scenario(scenario_id, actor)
        assumptions = " | ".join(scenario.saved_result.assumptions)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "scenario_id",
                "facility_id",
                "facility_name",
                "capability_id",
                "result_classification",
                "support_band",
                "documentary_support_index",
                "contradiction_state",
                "distance_km",
                "evidence_ids",
                "assumptions",
                "citations",
                "uncertainty",
                "source_bundle_id",
                "policy_version",
                "saved_snapshot_version",
            ],
        )
        writer.writeheader()
        for facility in scenario.saved_result.facilities:
            writer.writerow(
                {
                    key: spreadsheet_safe_cell(value)
                    for key, value in {
                    "scenario_id": scenario.scenario_id,
                    "facility_id": facility.facility_id,
                    "facility_name": facility.name,
                    "capability_id": scenario.capability_id.value,
                    "result_classification": scenario.saved_result.classification.value,
                    "support_band": facility.assessment.support_band.value,
                    "documentary_support_index": facility.assessment.documentary_support_index,
                    "contradiction_state": facility.assessment.contradiction_state.value,
                    "distance_km": facility.distance_km,
                    "evidence_ids": "|".join(facility.assessment.evidence_ids),
                    "assumptions": assumptions,
                    "citations": "|".join(facility.assessment.evidence_ids),
                    "uncertainty": assumptions,
                    "source_bundle_id": scenario.dataset_snapshot_id,
                    "policy_version": scenario.saved_result.policy_version,
                    "saved_snapshot_version": scenario.evidence_snapshot_id,
                    }.items()
                }
            )
        return output.getvalue()

    def decision_brief(self, scenario_id: str, actor: Actor) -> str:
        scenario = self.get_scenario(scenario_id, actor)
        result = scenario.saved_result
        return (
            f"# {scenario.name}\n\n"
            f"Capability: {scenario.capability_id.value}\n\n"
            f"Saved conclusion: {result.classification_label}.\n\n"
            f"Observed facilities: {result.distinct_observed_facilities}; "
            f"qualifying documentary records: {result.qualifying_facilities}.\n\n"
            "This is planning support only. Documentary support does not confirm current "
            "availability, staffing, capacity, or operational readiness.\n\n"
            f"Source bundle: {scenario.dataset_snapshot_id}\n\n"
            f"Policy version: {result.policy_version}\n\n"
            f"Evidence snapshot: {scenario.evidence_snapshot_id}\n\n"
            "Assumptions and limitations:\n" + "\n".join(f"- {item}" for item in result.assumptions)
        )

    def crisis(self, payload: CrisisAnalyzeRequest) -> CrisisAnalysis:
        if not self.settings.crisis_enabled:
            raise ApplicationError(
                ErrorCode.CAPABILITY_DISABLED,
                "Crisis analysis is disabled.",
                (
                    "Enable MEDICAL_DESERT_CRISIS_ENABLED only after the core "
                    "G0-G7 release gates pass."
                ),
                status_code=404,
            )
        analysis = self.query(
            DocumentaryQuery(
                capability_id=payload.capability_id,
                geography_id=payload.geography_id,
                radius_km=payload.radius_km,
            )
        )
        return CrisisAnalysis(
            incident_id=payload.incident_id,
            source_type=payload.source_type,
            source_time=payload.source_time,
            last_refresh=payload.last_refresh,
            analysis=analysis,
            planning_summary=(
                f"{payload.name}: {analysis.classification_label}. "
                f"{analysis.qualifying_facilities} qualifying documentary records are present."
            ),
            limitations=[
                "Incident geometry is an overlay and does not change facility evidence.",
                "Facility availability must be confirmed outside the application.",
            ],
        )

    def referral(self, payload: ReferralRequest) -> ReferralShortlist:
        if not self.settings.referral_enabled:
            raise ApplicationError(
                ErrorCode.CAPABILITY_DISABLED,
                "Referral Copilot is disabled.",
                "Enable MEDICAL_DESERT_REFERRAL_ENABLED only after G7 remains green.",
                status_code=404,
            )
        result = self.query(
            DocumentaryQuery(
                capability_id=payload.capability_id,
                geography_id=payload.geography_id,
                radius_km=payload.radius_km,
            )
        )
        facilities = [
            item
            for item in result.facilities
            if (item.assessment.human_reviewed_verdict or item.assessment.support_band)
            in {SupportBand.STRONGLY_SUPPORTED, SupportBand.PARTIALLY_SUPPORTED}
            and item.distance_km is not None
        ][: payload.maximum_results]
        return ReferralShortlist(
            facilities=facilities,
            evidence_snapshot_id=self.analytics.evidence_snapshot_id,
        )

    def health(self) -> HealthResponse:
        if self.settings.databricks_enabled and self._sql_canary_ok is None:
            if self.sql_query is None:
                self._sql_canary_ok = False
                self._sql_error = "SQL adapter is not configured."
            else:
                try:
                    self.sql_query.fetch_all("SELECT 1 AS app_oauth_canary")
                    self._sql_canary_ok = True
                    self._sql_error = None
                except Exception as error:
                    self._sql_canary_ok = False
                    self._sql_error = type(error).__name__
        if self.settings.mlflow_enabled and self._trace_canary_id is None and not self._trace_error:
            self._record_trace(
                "health.mlflow_canary",
                {
                    "product": "Medical Desert Planner",
                    "environment": self.settings.environment,
                },
            )
        outbox = self.store.outbox_summary()
        pending = outbox.get(MaterializationState.PENDING.value, 0)
        failed = outbox.get(MaterializationState.FAILED.value, 0)
        blocked = outbox.get(MaterializationState.BLOCKED_DEPENDENCY.value, 0)
        unhealthy_outbox = pending + failed + blocked
        components = {
            "app_process": HealthComponent(status="healthy", detail="FastAPI process is running."),
            "analytical_read": HealthComponent(
                status="healthy",
                detail=(
                    f"Databricks gold read model {self.settings.project_catalog} is configured."
                    if self.settings.databricks_enabled
                    else "Deterministic Darbhanga demo analytical adapter is available offline."
                ),
            ),
            "operational_state": HealthComponent(
                status="healthy", detail=f"{self.store.backend_name}."
            ),
            "outbox": HealthComponent(
                status="healthy" if unhealthy_outbox == 0 else "degraded",
                detail=(
                    f"{pending} pending, {failed} failed, and {blocked} blocked event(s); "
                    "derived aggregates expose their materialization state."
                ),
            ),
            "databricks_sql": HealthComponent(
                status=(
                    "disabled"
                    if not self.settings.databricks_enabled
                    else "healthy"
                    if self._sql_canary_ok
                    else "degraded"
                ),
                detail="Optional adapter is disabled."
                if not self.settings.databricks_enabled
                else (
                    "Databricks App OAuth SQL canary passed."
                    if self._sql_canary_ok
                    else f"SQL canary failed: {self._sql_error}"
                ),
            ),
            "mlflow": HealthComponent(
                status=(
                    "disabled"
                    if not self.settings.mlflow_enabled
                    else "healthy"
                    if self._trace_canary_id and not self._trace_error
                    else "degraded"
                ),
                detail="Optional tracing is disabled."
                if not self.settings.mlflow_enabled
                else (
                    f"Trace write passed: {self._trace_canary_id}."
                    if self._trace_canary_id and not self._trace_error
                    else f"Trace write failed: {self._trace_error}"
                ),
            ),
            "tavily": HealthComponent(
                status="disabled" if self.settings.tavily_mode == "off" else "healthy",
                detail=(
                    f"Tavily mode is {self.settings.tavily_mode}; only explicit reviewer "
                    "actions may request external evidence."
                ),
            ),
            "crisis": HealthComponent(
                status="healthy" if self.settings.crisis_enabled else "disabled",
                detail="Isolated optional route.",
            ),
            "referral": HealthComponent(
                status="healthy" if self.settings.referral_enabled else "disabled",
                detail="Isolated optional route.",
            ),
        }
        overall = (
            "degraded"
            if any(item.status == "degraded" for item in components.values())
            else "healthy"
        )
        return HealthResponse(
            status=overall,
            version=__version__,
            components=components,
            dataset_snapshot_version=self.analytics.source_bundle_id,
            identity_mode=self.settings.identity_mode,
            timestamp=utc_now(),
        )

    @staticmethod
    def _raise_persistence(error: Exception) -> None:
        if isinstance(error, VersionConflict):
            raise ApplicationError(
                ErrorCode.VERSION_CONFLICT,
                str(error),
                "Refresh the record, merge changes, and retry with the current version.",
                status_code=409,
                details={"expected_version": error.expected, "current_version": error.current},
            ) from error
        if isinstance(error, IdempotencyConflict):
            raise ApplicationError(
                ErrorCode.IDEMPOTENCY_CONFLICT,
                str(error),
                "Use the original request body or a new idempotency key.",
                status_code=409,
            ) from error
        if isinstance(error, RecordNotFound):
            raise ApplicationError(
                ErrorCode.NOT_FOUND,
                "The requested record was not found.",
                "Refresh the current collection and retry.",
                status_code=404,
            ) from error
        raise error
