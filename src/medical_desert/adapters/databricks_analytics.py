from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any, Literal, cast

from pydantic import HttpUrl, TypeAdapter, ValidationError

from medical_desert.demo_data import DemoFacility
from medical_desert.domain.models import (
    CapabilityAssessment,
    CapabilityId,
    ContradictionState,
    EvidenceSpan,
    FacilityDetail,
    Geography,
    GeographyType,
    ScoreFactors,
    SupportBand,
    SurveyContext,
    SurveyContextAvailability,
    SurveyIndicator,
)
from medical_desert.ports.external import SQLQueryPort

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_STATE_CODES = {"bihar": "br"}
_HTTP_URL = TypeAdapter(HttpUrl)


class DatabricksGoldAnalyticsAdapter:
    def __init__(
        self,
        sql: SQLQueryPort,
        *,
        project_catalog: str,
        source_bundle_id: str,
        policy_version: str,
        scoring_version: str,
        focus_state: str,
        focus_district: str,
    ) -> None:
        if not _IDENTIFIER.fullmatch(project_catalog):
            raise ValueError("Project catalog must be a simple SQL identifier.")
        self.sql = sql
        self.project_catalog = project_catalog
        self.source_bundle_id = source_bundle_id
        self.policy_version = policy_version
        self.scoring_version = scoring_version
        self.focus_state = focus_state
        self.focus_district = focus_district

    @property
    def evidence_snapshot_id(self) -> str:
        return f"{self.source_bundle_id}:evidence"

    @property
    def survey_district_id(self) -> str:
        return self.district_id

    def _table(self, schema: str, name: str) -> str:
        return f"`{self.project_catalog}`.`{schema}`.`{name}`"

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    @staticmethod
    def _source_url(value: Any) -> HttpUrl | None:
        if not value:
            return None
        try:
            return _HTTP_URL.validate_python(value)
        except ValidationError:
            return None

    @staticmethod
    def _polarity(value: Any) -> Literal["positive", "negative", "uncertain"]:
        if value in {"positive", "negative", "uncertain"}:
            return cast(Literal["positive", "negative", "uncertain"], value)
        return "uncertain"

    @staticmethod
    def _array_values(value: Any) -> list[Any]:
        return [] if value is None else list(value)

    @staticmethod
    def _qualifier(
        value: Any,
    ) -> Literal["standard", "low_sample_25_49", "suppressed_lt_25", "unparseable"]:
        if value in {
            "standard",
            "low_sample_25_49",
            "suppressed_lt_25",
            "unparseable",
        }:
            return cast(
                Literal[
                    "standard",
                    "low_sample_25_49",
                    "suppressed_lt_25",
                    "unparseable",
                ],
                value,
            )
        return "unparseable"

    @property
    def district_id(self) -> str:
        state_code = _STATE_CODES.get(
            self.focus_state.lower(), self._slug(self.focus_state)[:2]
        )
        return f"district:{state_code}:{self._slug(self.focus_district)}"

    def _origin_rows(self) -> list[dict[str, Any]]:
        return self.sql.fetch_all(
            f"""
            SELECT
              origin.analysis_origin_id,
              origin.pincode,
              origin.latitude,
              origin.longitude,
              origin.origin_status,
              origin.unavailable_reason,
              origin.geography_status,
              reference.coordinate_dispersion_degrees,
              reference.reference_method,
              reference.state_candidates,
              reference.district_candidates
            FROM {self._table("silver", "analysis_origin")} origin
            LEFT JOIN {self._table("silver", "pin_postal_reference")} reference
              ON origin.source_bundle_id = reference.source_bundle_id
             AND origin.pincode = reference.pincode
            WHERE origin.source_bundle_id = ?
              AND array_contains(reference.state_candidates, ?)
              AND array_contains(reference.district_candidates, ?)
            ORDER BY origin.pincode
            """,
            [
                self.source_bundle_id,
                self.focus_state.lower(),
                self.focus_district.lower(),
            ],
        )

    def list_geographies(self) -> list[Geography]:
        origins = self._origin_rows()
        mappable = [
            row
            for row in origins
            if row["origin_status"] == "mappable"
            and row["latitude"] is not None
            and row["longitude"] is not None
        ]
        center_latitude = (
            sum(float(row["latitude"]) for row in mappable) / len(mappable)
            if mappable
            else None
        )
        center_longitude = (
            sum(float(row["longitude"]) for row in mappable) / len(mappable)
            if mappable
            else None
        )
        district = Geography(
            geography_id=self.district_id,
            geography_type=GeographyType.DISTRICT,
            name=self.focus_district,
            state=self.focus_state,
            district=self.focus_district,
            selectable=bool(mappable),
            unavailable_reason=None if mappable else "No mappable postal references are available.",
            metadata={
                "analysis_origin_type": "postal_reference_point",
                "postal_reference_method": "mean of mappable versioned PIN reference points",
                "postal_reference_latitude": center_latitude,
                "postal_reference_longitude": center_longitude,
            },
        )
        pins = [
            Geography(
                geography_id=f"pin:{row['pincode']}",
                geography_type=GeographyType.PIN,
                name=str(row["pincode"]),
                state=self.focus_state,
                district=self.focus_district,
                pin=str(row["pincode"]),
                selectable=row["origin_status"] == "mappable",
                unavailable_reason=(
                    None
                    if row["origin_status"] == "mappable"
                    else str(row["unavailable_reason"] or "Postal reference is unavailable.")
                ),
                metadata={
                    "analysis_origin_id": row["analysis_origin_id"],
                    "postal_reference_latitude": row["latitude"],
                    "postal_reference_longitude": row["longitude"],
                    "postal_reference_method": row["reference_method"],
                    "dispersion_km": (
                        float(row["coordinate_dispersion_degrees"]) * 111.0
                        if row["coordinate_dispersion_degrees"] is not None
                        else 0.0
                    ),
                    "ambiguity": row["geography_status"],
                    "not_a_centroid": True,
                },
            )
            for row in origins
        ]
        return [
            district,
            *pins,
            Geography(
                geography_id=f"city:{self._slug(self.focus_district)}",
                geography_type=GeographyType.CITY,
                name=self.focus_district,
                state=self.focus_state,
                district=self.focus_district,
                selectable=False,
                unavailable_reason="City normalization quality has not passed activation review.",
            ),
        ]

    def get_geography(self, geography_id: str) -> Geography | None:
        return next(
            (item for item in self.list_geographies() if item.geography_id == geography_id),
            None,
        )

    def _facility_rows(
        self,
        *,
        pin: str | None = None,
        facility_id: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = ["facility.source_bundle_id = ?"]
        parameters: list[Any] = [self.source_bundle_id]
        if pin:
            filters.append("facility.pincode = ?")
            parameters.append(pin)
        elif facility_id:
            filters.append("facility.facility_id = ?")
            parameters.append(facility_id)
        else:
            filters.extend(
                [
                    "array_contains(reference.state_candidates, ?)",
                    "array_contains(reference.district_candidates, ?)",
                ]
            )
            parameters.extend([self.focus_state.lower(), self.focus_district.lower()])
        filters.extend(
            [
                "facility.latitude IS NOT NULL",
                "facility.longitude IS NOT NULL",
            ]
        )
        return self.sql.fetch_all(
            f"""
            SELECT
              facility.facility_id,
              facility.canonical_name,
              facility.description,
              facility.city_raw,
              facility.city_normalized,
              facility.state_raw,
              facility.state_normalized,
              facility.pincode,
              facility.latitude,
              facility.longitude,
              facility.location_conflict_status,
              facility.freshness_status,
              source.raw_payload
            FROM {self._table("silver", "facility_normalized")} facility
            JOIN {self._table("silver", "facility_entity")} entity
              ON facility.source_bundle_id = entity.source_bundle_id
             AND facility.facility_id = entity.facility_id
            LEFT JOIN {self._table("bronze", "facility_source_snapshot")} source
              ON entity.source_bundle_id = source.source_bundle_id
             AND entity.canonical_source_row_id = source.source_row_id
            LEFT JOIN {self._table("silver", "pin_postal_reference")} reference
              ON facility.source_bundle_id = reference.source_bundle_id
             AND facility.pincode = reference.pincode
            WHERE {" AND ".join(filters)}
            ORDER BY facility.canonical_name, facility.facility_id
            """,
            parameters,
        )

    def _map_facility(self, row: dict[str, Any]) -> DemoFacility:
        raw_payload = row.get("raw_payload")
        try:
            observed_fields = (
                json.loads(raw_payload) if isinstance(raw_payload, str) else dict(raw_payload or {})
            )
        except (TypeError, ValueError):
            observed_fields = {"raw_payload_status": "unparseable"}
        observed_fields["freshness_status"] = row.get("freshness_status")
        conflict_status = str(row.get("location_conflict_status") or "none")
        return cast(
            DemoFacility,
            {
                "facility_id": str(row["facility_id"]),
                "name": str(row.get("canonical_name") or row["facility_id"]),
                "city": str(row.get("city_raw") or row.get("city_normalized") or ""),
                "district": self.focus_district,
                "state": str(
                    row.get("state_raw")
                    or row.get("state_normalized")
                    or self.focus_state
                ),
                "pin": str(row.get("pincode") or ""),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "description": str(row.get("description") or "Observed facility record."),
                "source_snapshot_id": self.source_bundle_id,
                "observed_fields": observed_fields,
                "geography_conflict": (
                    None if conflict_status == "none" else conflict_status
                ),
            },
        )

    def list_facilities(self, geography_id: str) -> list[DemoFacility]:
        pin = geography_id.removeprefix("pin:") if geography_id.startswith("pin:") else None
        return [self._map_facility(row) for row in self._facility_rows(pin=pin)]

    def get_assessment(
        self, facility_id: str, capability_id: CapabilityId
    ) -> CapabilityAssessment | None:
        rows = self.sql.fetch_all(
            f"""
            SELECT *
            FROM {self._table("gold", "facility_documentary_support")}
            WHERE source_bundle_id = ? AND facility_id = ? AND capability_id = ?
            ORDER BY calculated_at DESC
            LIMIT 1
            """,
            [self.source_bundle_id, facility_id, capability_id.value],
        )
        if not rows:
            if not self._facility_rows(facility_id=facility_id):
                return None
            return CapabilityAssessment(
                facility_id=facility_id,
                capability_id=capability_id,
                documentary_support_index=None,
                support_band=SupportBand.INSUFFICIENT_EVIDENCE,
                contradiction_state=ContradictionState.NONE,
                evidence_sufficiency="insufficient",
                decision_readiness="abstain",
                missing_prerequisites=["No validated capability evidence was materialized."],
                rule_version="unmaterialized",
                machine_assessed_at=datetime.now(UTC),
            )
        row = rows[0]
        band = SupportBand(str(row["support_band"]))
        contradiction = ContradictionState(str(row["contradiction_state"]))
        sufficient = band in {
            SupportBand.STRONGLY_SUPPORTED,
            SupportBand.PARTIALLY_SUPPORTED,
        }
        return CapabilityAssessment(
            facility_id=facility_id,
            capability_id=capability_id,
            documentary_support_index=(
                round(float(row["documentary_support_index"]))
                if row["documentary_support_index"] is not None
                else None
            ),
            support_band=band,
            contradiction_state=contradiction,
            evidence_sufficiency=(
                "sufficient"
                if sufficient
                else "insufficient"
                if band
                in {
                    SupportBand.INSUFFICIENT_EVIDENCE,
                    SupportBand.UNSUPPORTED_OR_VERY_WEAK,
                }
                else "limited"
            ),
            decision_readiness=(
                "ready"
                if sufficient and contradiction == ContradictionState.NONE
                else "abstain"
                if band == SupportBand.INSUFFICIENT_EVIDENCE
                else "review_required"
            ),
            score_factors=ScoreFactors(
                direct_evidence_specificity=round(float(row["direct_evidence_specificity"])),
                independent_source_corroboration=round(
                    float(row["independent_source_corroboration"])
                ),
                source_quality=round(float(row["source_quality"])),
                entity_attribution_quality=round(float(row["entity_attribution_quality"])),
                freshness=round(float(row["freshness"])),
                prerequisite_support=round(float(row["prerequisite_support"])),
            ),
            missing_prerequisites=self._array_values(row.get("exclusion_reasons")),
            contradictions=(
                [] if contradiction == ContradictionState.NONE else [contradiction.value]
            ),
            evidence_ids=self._array_values(row.get("evidence_span_ids")),
            rule_version=str(row["policy_version"]),
            machine_assessed_at=row["calculated_at"],
        )

    def get_facility(self, facility_id: str) -> FacilityDetail | None:
        rows = self._facility_rows(facility_id=facility_id)
        if not rows:
            return None
        facility = self._map_facility(rows[0])
        return FacilityDetail(
            facility_id=facility_id,
            name=facility["name"],
            description=facility["description"],
            city=facility["city"] or None,
            district=facility["district"],
            state=facility["state"],
            pin=facility["pin"] or None,
            latitude=facility["latitude"],
            longitude=facility["longitude"],
            source_snapshot_id=self.source_bundle_id,
            observed_fields=facility["observed_fields"],
            assessments=[
                assessment
                for capability in CapabilityId
                if (assessment := self.get_assessment(facility_id, capability)) is not None
            ],
        )

    def get_evidence(
        self, facility_id: str, capability_id: CapabilityId | None = None
    ) -> list[EvidenceSpan]:
        capability_filter = ""
        parameters: list[Any] = [self.source_bundle_id, facility_id]
        if capability_id is not None:
            capability_filter = "AND claim.capability_id = ?"
            parameters.append(capability_id.value)
        rows = self.sql.fetch_all(
            f"""
            SELECT
              span.evidence_span_id,
              claim.facility_id,
              claim.capability_id,
              span.source_field,
              span.evidence_text,
              artifact.source_url,
              artifact.publisher,
              artifact.source_family,
              artifact.publication_time,
              artifact.valid_time,
              artifact.retrieval_time,
              claim.extraction_method,
              claim.extraction_version,
              claim.polarity,
              span.span_hash
            FROM {self._table("silver", "evidence_span")} span
            JOIN {self._table("silver", "facility_claim")} claim
              ON span.claim_id = claim.claim_id
            JOIN {self._table("silver", "source_artifact")} artifact
              ON span.source_artifact_id = artifact.source_artifact_id
            WHERE claim.source_bundle_id = ?
              AND claim.facility_id = ?
              {capability_filter}
            ORDER BY claim.capability_id, span.evidence_span_id
            """,
            parameters,
        )
        return [
            EvidenceSpan(
                evidence_id=str(row["evidence_span_id"]),
                facility_id=str(row["facility_id"]),
                capability_id=CapabilityId(str(row["capability_id"])),
                source_field=str(row["source_field"]),
                exact_text=str(row["evidence_text"]),
                source_url=self._source_url(row.get("source_url")),
                publisher=str(row.get("publisher") or "Observed source"),
                source_family=str(row.get("source_family") or "unknown"),
                publication_time=row.get("publication_time"),
                valid_time=row.get("valid_time"),
                retrieval_time=row.get("retrieval_time"),
                extraction_method=str(row["extraction_method"]),
                extraction_version=str(row["extraction_version"]),
                entity_attribution_confidence=1.0,
                polarity=self._polarity(row.get("polarity")),
                content_hash=str(row["span_hash"]),
            )
            for row in rows
        ]

    def get_survey_context(self, district_id: str) -> SurveyContext | None:
        if district_id != self.district_id:
            return None
        rows = self.sql.fetch_all(
            f"""
            SELECT *
            FROM {self._table("gold", "district_context_profile")}
            WHERE source_bundle_id = ?
              AND normalized_state = ?
              AND normalized_district = ?
            ORDER BY calculated_at DESC
            LIMIT 1
            """,
            [
                self.source_bundle_id,
                self.focus_state.lower(),
                self.focus_district.lower(),
            ],
        )
        if not rows:
            return None
        row = rows[0]
        payload = row["context_payload"]
        context = json.loads(payload) if isinstance(payload, str) else dict(payload)
        indicators: list[SurveyIndicator] = []
        for indicator_id, raw in sorted(context.items()):
            value = json.loads(raw) if isinstance(raw, str) else dict(raw)
            parse_status = str(value.get("parse_status") or "unparseable")
            raw_qualifier = (
                "unparseable"
                if parse_status == "unparseable"
                else str(value.get("qualifier") or "standard")
            )
            indicators.append(
                SurveyIndicator(
                    indicator_id=indicator_id,
                    label=indicator_id.replace("_", " ").title(),
                    raw_value=str(value.get("raw_value") or ""),
                    numeric_value=value.get("numeric_value"),
                    qualifier=self._qualifier(raw_qualifier),
                    unit="percent" if indicator_id.endswith("_pct") else "reported_value",
                )
            )
        return SurveyContext(
            district_id=district_id,
            district=self.focus_district,
            state=self.focus_state,
            survey_context_availability=SurveyContextAvailability(
                str(row["survey_context_availability"])
            ),
            indicators=indicators,
            crosswalk_version=str(row["source_version"]),
            limitations=[
                "NFHS-5 is district survey context and does not change facility evidence.",
                "Survey sample counts are not population denominators.",
            ],
        )
