from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from medical_desert.adapters.demo_analytics import DemoAnalyticsAdapter
from medical_desert.adapters.tracing import NoopTracingAdapter
from medical_desert.application.services import MedicalDesertService
from medical_desert.config.settings import Settings
from medical_desert.domain.models import (
    CapabilityId,
    ContradictionState,
    MaterializationState,
    ReviewStatus,
    SupportBand,
)
from medical_desert.persistence.errors import IdempotencyConflict, VersionConflict
from medical_desert.persistence.sqlite import SQLiteOperationalStore
from tests.support.factories import actor, scenario


class RecordingSQL:
    def __init__(self) -> None:
        self.executions: list[tuple[str, list[object]]] = []

    def execute(self, statement: str, parameters: list[object] | None = None) -> None:
        self.executions.append((statement, parameters or []))

    def fetch_all(
        self,
        statement: str,
        parameters: list[object] | None = None,
    ) -> list[dict[str, object]]:
        return [{"app_oauth_canary": 1}]


@pytest.fixture
def store(tmp_path: Path) -> SQLiteOperationalStore:
    value = SQLiteOperationalStore(tmp_path / "operational.db")
    value.initialize()
    return value


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_duplicate_idempotency_request_returns_same_logical_result(
    store: SQLiteOperationalStore,
) -> None:
    calls = 0

    def callback(connection: sqlite3.Connection) -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"scenario_id": "scenario-1"}

    first = store.execute_idempotent(
        actor=actor(),
        operation="scenario.create",
        idempotency_key="key-1",
        request_hash="hash-1",
        request_id="request-1",
        callback=callback,
    )
    second = store.execute_idempotent(
        actor=actor(),
        operation="scenario.create",
        idempotency_key="key-1",
        request_hash="hash-1",
        request_id="request-2",
        callback=callback,
    )
    assert first == second
    assert calls == 1


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_reused_idempotency_key_with_different_body_is_rejected(
    store: SQLiteOperationalStore,
) -> None:
    store.execute_idempotent(
        actor=actor(),
        operation="scenario.create",
        idempotency_key="key-1",
        request_hash="hash-1",
        request_id="request-1",
        callback=lambda connection: {"scenario_id": "scenario-1"},
    )
    with pytest.raises(IdempotencyConflict):
        store.execute_idempotent(
            actor=actor(),
            operation="scenario.create",
            idempotency_key="key-1",
            request_hash="hash-2",
            request_id="request-2",
            callback=lambda connection: {"scenario_id": "scenario-2"},
        )


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_scenario_create_round_trips_without_mutating_saved_snapshot(
    store: SQLiteOperationalStore,
) -> None:
    saved = scenario()
    store.execute_idempotent(
        actor=actor(),
        operation="scenario.create",
        idempotency_key="create-1",
        request_hash="hash-create",
        request_id="request-create",
        callback=lambda connection: store.create_scenario(
            connection, saved, actor(), "request-create"
        ),
    )
    assert store.get_scenario(saved.scenario_id) == saved


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_concurrent_updates_cannot_silently_overwrite(store: SQLiteOperationalStore) -> None:
    original = scenario()
    store.execute_idempotent(
        actor=actor(),
        operation="scenario.create",
        idempotency_key="create-1",
        request_hash="hash-create",
        request_id="request-create",
        callback=lambda connection: store.create_scenario(
            connection, original, actor(), "request-create"
        ),
    )

    def update(notes: str) -> str:
        try:
            store.execute_idempotent(
                actor=actor(),
                operation="scenario.update",
                idempotency_key=f"update-{notes}",
                request_hash=f"hash-{notes}",
                request_id=f"request-{notes}",
                callback=lambda connection: store.update_scenario(
                    connection,
                    scenario(version=2, notes=notes),
                    1,
                    actor(),
                    f"request-{notes}",
                ),
            )
            return "success"
        except VersionConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(update, ["first", "second"]))
    assert sorted(outcomes) == ["conflict", "success"]


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_review_commit_creates_audit_and_pending_outbox_atomically(
    store: SQLiteOperationalStore,
) -> None:
    payload = store.execute_idempotent(
        actor=actor(),
        operation="review.append",
        idempotency_key="review-1",
        request_hash="review-hash",
        request_id="review-request",
        callback=lambda connection: store.append_review(
            connection,
            facility_id="facility-1",
            capability_id=CapabilityId.MATERNAL_EMERGENCY,
            verdict=SupportBand.CLAIM_ONLY_OR_WEAK,
            contradiction_state=ContradictionState.UNRESOLVED,
            reason="Geography conflict requires source confirmation.",
            evidence_ids=["evidence-1"],
            status=ReviewStatus.UNRESOLVED,
            expected_version=0,
            actor=actor(),
            request_id="review-request",
        ),
    )
    aggregate_id = f"facility-1:{CapabilityId.MATERNAL_EMERGENCY.value}"
    assert payload["materialization_state"] == "pending"
    assert len(store.audit_events(aggregate_id)) == 1
    assert store.outbox_summary() == {"pending": 1}


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_outbox_consumer_applies_and_blocks_after_bounded_retries(
    store: SQLiteOperationalStore,
) -> None:
    store.execute_idempotent(
        actor=actor(),
        operation="review.outbox",
        idempotency_key="review-outbox",
        request_hash="review-outbox-hash",
        request_id="review-outbox-request",
        callback=lambda connection: store.append_review(
            connection,
            facility_id="facility-outbox",
            capability_id=CapabilityId.MATERNAL_EMERGENCY,
            verdict=SupportBand.PARTIALLY_SUPPORTED,
            contradiction_state=ContradictionState.NONE,
            reason="Verified source.",
            evidence_ids=["evidence-outbox"],
            status=ReviewStatus.CONFIRMED,
            expected_version=0,
            actor=actor(),
            request_id="review-outbox-request",
        ),
    )

    assert store.process_pending_outbox(lambda _event: None) == {"applied": 1}
    assert (
        store.review_materialization_state(
            "facility-outbox", CapabilityId.MATERNAL_EMERGENCY
        )
        == MaterializationState.APPLIED
    )

    store.execute_idempotent(
        actor=actor(),
        operation="review.blocked",
        idempotency_key="review-blocked",
        request_hash="review-blocked-hash",
        request_id="review-blocked-request",
        callback=lambda connection: store.append_review(
            connection,
            facility_id="facility-blocked",
            capability_id=CapabilityId.MATERNAL_EMERGENCY,
            verdict=SupportBand.CLAIM_ONLY_OR_WEAK,
            contradiction_state=ContradictionState.UNRESOLVED,
            reason="Dependency unavailable.",
            evidence_ids=[],
            status=ReviewStatus.UNRESOLVED,
            expected_version=0,
            actor=actor(),
            request_id="review-blocked-request",
        ),
    )

    def fail(_event) -> None:
        raise RuntimeError("materializer unavailable")

    for _attempt in range(3):
        store.process_pending_outbox(fail)
    assert store.outbox_summary() == {"applied": 1, "blocked_dependency": 1}
    assert (
        store.review_materialization_state(
            "facility-blocked", CapabilityId.MATERNAL_EMERGENCY
        )
        == MaterializationState.BLOCKED_DEPENDENCY
    )


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_review_history_preserves_original_decision_after_reversal(
    store: SQLiteOperationalStore,
) -> None:
    for version, status in [(0, ReviewStatus.CONFIRMED), (1, ReviewStatus.REVERSED)]:
        store.execute_idempotent(
            actor=actor(),
            operation="review.append",
            idempotency_key=f"review-{version}",
            request_hash=f"review-hash-{version}",
            request_id=f"review-request-{version}",
            callback=lambda connection, version=version, status=status: store.append_review(
                connection,
                facility_id="facility-1",
                capability_id=CapabilityId.ADVANCED_IMAGING,
                verdict=SupportBand.STRONGLY_SUPPORTED,
                contradiction_state=ContradictionState.NONE,
                reason="Evidence-backed decision retained in immutable history.",
                evidence_ids=["evidence-1"],
                status=status,
                expected_version=version,
                actor=actor(),
                request_id=f"review-request-{version}",
            ),
        )
    history = store.review_history("facility-1")
    assert {item["status"] for item in history} == {"confirmed", "reversed"}


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_production_outbox_marks_applied_only_after_delta_overlay_merges(
    store: SQLiteOperationalStore,
) -> None:
    facility_id = "b69b988a-1179-44df-8349-e0d632ebfb83"
    store.execute_idempotent(
        actor=actor(),
        operation="review.materialize",
        idempotency_key="review-materialize",
        request_hash="review-materialize-hash",
        request_id="review-materialize-request",
        callback=lambda connection: store.append_review(
            connection,
            facility_id=facility_id,
            capability_id=CapabilityId.EMERGENCY_SURGERY,
            verdict=SupportBand.STRONGLY_SUPPORTED,
            contradiction_state=ContradictionState.NONE,
            reason="Validated evidence supports the correction.",
            evidence_ids=["evidence-1"],
            status=ReviewStatus.CONFIRMED,
            expected_version=0,
            actor=actor(),
            request_id="review-materialize-request",
        ),
    )
    sql = RecordingSQL()
    service = MedicalDesertService(
        Settings(environment="production"),
        DemoAnalyticsAdapter(),
        store,
        NoopTracingAdapter(),
        sql_query=sql,
    )

    assert service.materialize_pending_events() == {"applied": 1}
    assert len(sql.executions) == 2
    assert "facility_review_overlay" in sql.executions[0][0]
    assert "operational_event_materialization" in sql.executions[1][0]
    assert (
        store.review_materialization_state(
            facility_id,
            CapabilityId.EMERGENCY_SURGERY,
        )
        == MaterializationState.APPLIED
    )


@pytest.mark.integration
@pytest.mark.gate("G5")
def test_production_outbox_remains_pending_without_databricks_sql(
    store: SQLiteOperationalStore,
) -> None:
    store.execute_idempotent(
        actor=actor(),
        operation="review.pending",
        idempotency_key="review-pending",
        request_hash="review-pending-hash",
        request_id="review-pending-request",
        callback=lambda connection: store.append_review(
            connection,
            facility_id="facility-pending",
            capability_id=CapabilityId.MATERNAL_EMERGENCY,
            verdict=SupportBand.CLAIM_ONLY_OR_WEAK,
            contradiction_state=ContradictionState.UNRESOLVED,
            reason="The materializer dependency is not configured.",
            evidence_ids=["evidence-pending"],
            status=ReviewStatus.UNRESOLVED,
            expected_version=0,
            actor=actor(),
            request_id="review-pending-request",
        ),
    )
    service = MedicalDesertService(
        Settings(environment="production"),
        DemoAnalyticsAdapter(),
        store,
        NoopTracingAdapter(),
    )

    assert service.materialize_pending_events() == {"pending": 1}
