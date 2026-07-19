from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar, cast
from uuid import uuid4

from medical_desert.domain.models import (
    Actor,
    CapabilityId,
    ContradictionState,
    MaterializationState,
    ReviewStatus,
    Scenario,
    SupportBand,
    VerificationItem,
)
from medical_desert.persistence.errors import (
    IdempotencyConflict,
    RecordNotFound,
    VersionConflict,
)

T = TypeVar("T")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


class SQLiteOperationalStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    @property
    def backend_name(self) -> str:
        return f"SQLite operational store at {self.path}"

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    scenario_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    document_json TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    facility_id TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    verdict TEXT,
                    contradiction_state TEXT,
                    reason TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(facility_id, capability_id, version)
                );
                CREATE TABLE IF NOT EXISTS verification_items (
                    item_id TEXT PRIMARY KEY,
                    facility_id TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    document_json TEXT NOT NULL,
                    priority REAL NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    aggregate_type TEXT NOT NULL,
                    aggregate_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_roles_json TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outbox_events (
                    event_id TEXT PRIMARY KEY,
                    stream_id TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    UNIQUE(stream_id, sequence_number)
                );
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    actor_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(actor_id, operation, idempotency_key)
                );
                """
            )
            connection.commit()

    def execute_idempotent(
        self,
        *,
        actor: Actor,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        request_id: str,
        callback: Callable[[sqlite3.Connection], T],
    ) -> T:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT request_hash, response_json
                FROM idempotency_records
                WHERE actor_id=? AND operation=? AND idempotency_key=?
                """,
                (actor.actor_id, operation, idempotency_key),
            ).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise IdempotencyConflict(
                        "The idempotency key was already used with a different request body."
                    )
                return cast(T, json.loads(existing["response_json"]))
            response = callback(connection)
            connection.execute(
                """
                INSERT INTO idempotency_records(
                    actor_id, operation, idempotency_key, request_hash, response_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    actor.actor_id,
                    operation,
                    idempotency_key,
                    request_hash,
                    _json(response),
                    _now(),
                ),
            )
            connection.commit()
            return response

    def _audit(
        self,
        connection: sqlite3.Connection,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        actor: Actor,
        request_id: str,
        payload: dict[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_events(
                event_id, aggregate_type, aggregate_id, event_type, actor_id,
                actor_roles_json, request_id, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"audit-{uuid4()}",
                aggregate_type,
                aggregate_id,
                event_type,
                actor.actor_id,
                _json([role.value for role in actor.roles]),
                request_id,
                _json(payload),
                _now(),
            ),
        )

    def _outbox(
        self,
        connection: sqlite3.Connection,
        *,
        stream_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        sequence = connection.execute(
            """
            SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_sequence
            FROM outbox_events
            WHERE stream_id=?
            """,
            (stream_id,),
        ).fetchone()["next_sequence"]
        connection.execute(
            """
            INSERT INTO outbox_events(
                event_id, stream_id, sequence_number, event_type,
                payload_json, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"outbox-{uuid4()}",
                stream_id,
                sequence,
                event_type,
                _json(payload),
                MaterializationState.PENDING.value,
                _now(),
            ),
        )

    def create_scenario(
        self,
        connection: sqlite3.Connection,
        scenario: Scenario,
        actor: Actor,
        request_id: str,
    ) -> dict[str, Any]:
        document = scenario.model_dump(mode="json")
        connection.execute(
            """
            INSERT INTO scenarios(
                scenario_id, owner_id, document_json, version, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                scenario.scenario_id,
                scenario.owner_id,
                _json(document),
                scenario.version,
                scenario.created_at.isoformat(),
                scenario.updated_at.isoformat(),
            ),
        )
        self._audit(
            connection,
            aggregate_type="scenario",
            aggregate_id=scenario.scenario_id,
            event_type="scenario_created",
            actor=actor,
            request_id=request_id,
            payload=document,
        )
        return document

    def update_scenario(
        self,
        connection: sqlite3.Connection,
        scenario: Scenario,
        expected_version: int,
        actor: Actor,
        request_id: str,
    ) -> dict[str, Any]:
        row = connection.execute(
            "SELECT version FROM scenarios WHERE scenario_id=?", (scenario.scenario_id,)
        ).fetchone()
        if row is None:
            raise RecordNotFound(scenario.scenario_id)
        current = int(row["version"])
        if current != expected_version:
            raise VersionConflict(expected_version, current)
        document = scenario.model_dump(mode="json")
        cursor = connection.execute(
            """
            UPDATE scenarios
            SET document_json=?, version=?, updated_at=?
            WHERE scenario_id=? AND version=?
            """,
            (
                _json(document),
                scenario.version,
                scenario.updated_at.isoformat(),
                scenario.scenario_id,
                expected_version,
            ),
        )
        if cursor.rowcount != 1:
            fresh = connection.execute(
                "SELECT version FROM scenarios WHERE scenario_id=?", (scenario.scenario_id,)
            ).fetchone()
            raise VersionConflict(expected_version, int(fresh["version"]))
        self._audit(
            connection,
            aggregate_type="scenario",
            aggregate_id=scenario.scenario_id,
            event_type="scenario_updated",
            actor=actor,
            request_id=request_id,
            payload=document,
        )
        return document

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT document_json FROM scenarios WHERE scenario_id=?", (scenario_id,)
            ).fetchone()
        return Scenario.model_validate_json(row["document_json"]) if row else None

    def list_scenarios(self, actor_id: str) -> list[Scenario]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT document_json FROM scenarios ORDER BY updated_at DESC"
            ).fetchall()
        scenarios = [Scenario.model_validate_json(row["document_json"]) for row in rows]
        return [
            scenario
            for scenario in scenarios
            if scenario.owner_id == actor_id or actor_id in scenario.collaborators
        ]

    def append_review(
        self,
        connection: sqlite3.Connection,
        *,
        facility_id: str,
        capability_id: CapabilityId,
        verdict: SupportBand | None,
        contradiction_state: ContradictionState | None,
        reason: str,
        evidence_ids: list[str],
        status: ReviewStatus,
        expected_version: int,
        actor: Actor,
        request_id: str,
    ) -> dict[str, Any]:
        current = connection.execute(
            """
            SELECT COALESCE(MAX(version), 0) AS version
            FROM reviews WHERE facility_id=? AND capability_id=?
            """,
            (facility_id, capability_id.value),
        ).fetchone()["version"]
        current = int(current)
        if current != expected_version:
            raise VersionConflict(expected_version, current)
        version = current + 1
        created_at = _now()
        review_id = f"review-{uuid4()}"
        payload = {
            "review_id": review_id,
            "facility_id": facility_id,
            "capability_id": capability_id.value,
            "verdict": verdict.value if verdict else None,
            "contradiction_state": contradiction_state.value if contradiction_state else None,
            "reason": reason,
            "evidence_ids": evidence_ids,
            "actor_id": actor.actor_id,
            "version": version,
            "status": status.value,
            "created_at": created_at,
            "materialization_state": MaterializationState.PENDING.value,
        }
        connection.execute(
            """
            INSERT INTO reviews(
                review_id, facility_id, capability_id, verdict, contradiction_state,
                reason, evidence_ids_json, actor_id, version, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                facility_id,
                capability_id.value,
                payload["verdict"],
                payload["contradiction_state"],
                reason,
                _json(evidence_ids),
                actor.actor_id,
                version,
                status.value,
                created_at,
            ),
        )
        self._audit(
            connection,
            aggregate_type="facility_review",
            aggregate_id=f"{facility_id}:{capability_id.value}",
            event_type="review_decision_committed",
            actor=actor,
            request_id=request_id,
            payload=payload,
        )
        self._outbox(
            connection,
            stream_id=f"facility:{facility_id}:{capability_id.value}",
            event_type="facility_review_changed",
            payload=payload,
        )
        return payload

    def current_review(
        self, facility_id: str, capability_id: CapabilityId
    ) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM reviews
                WHERE facility_id=? AND capability_id=?
                ORDER BY version DESC LIMIT 1
                """,
                (facility_id, capability_id.value),
            ).fetchone()
        return self._review_row(row) if row else None

    def review_history(self, facility_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM reviews WHERE facility_id=? ORDER BY created_at DESC",
                (facility_id,),
            ).fetchall()
        return [self._review_row(row) for row in rows]

    @staticmethod
    def _review_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "review_id": row["review_id"],
            "facility_id": row["facility_id"],
            "capability_id": row["capability_id"],
            "verdict": row["verdict"],
            "contradiction_state": row["contradiction_state"],
            "reason": row["reason"],
            "evidence_ids": json.loads(row["evidence_ids_json"]),
            "actor_id": row["actor_id"],
            "version": row["version"],
            "status": row["status"],
            "created_at": row["created_at"],
        }

    def create_verification_item(
        self,
        connection: sqlite3.Connection,
        item: VerificationItem,
        actor: Actor,
        request_id: str,
    ) -> dict[str, Any]:
        document = item.model_dump(mode="json")
        connection.execute(
            """
            INSERT INTO verification_items(
                item_id, facility_id, capability_id, document_json, priority,
                status, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.item_id,
                item.facility_id,
                item.capability_id.value,
                _json(document),
                item.priority,
                item.status.value,
                item.version,
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
            ),
        )
        self._audit(
            connection,
            aggregate_type="verification_item",
            aggregate_id=item.item_id,
            event_type="verification_item_created",
            actor=actor,
            request_id=request_id,
            payload=document,
        )
        return document

    def list_verification_items(self) -> list[VerificationItem]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT document_json FROM verification_items
                ORDER BY priority DESC, created_at ASC, item_id ASC
                """
            ).fetchall()
        return [VerificationItem.model_validate_json(row["document_json"]) for row in rows]

    def get_verification_item(self, item_id: str) -> VerificationItem | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT document_json FROM verification_items WHERE item_id=?", (item_id,)
            ).fetchone()
        return VerificationItem.model_validate_json(row["document_json"]) if row else None

    def update_verification_item(
        self,
        connection: sqlite3.Connection,
        item: VerificationItem,
        expected_version: int,
        actor: Actor,
        request_id: str,
    ) -> dict[str, Any]:
        row = connection.execute(
            "SELECT version FROM verification_items WHERE item_id=?", (item.item_id,)
        ).fetchone()
        if row is None:
            raise RecordNotFound(item.item_id)
        current = int(row["version"])
        if current != expected_version:
            raise VersionConflict(expected_version, current)
        document = item.model_dump(mode="json")
        connection.execute(
            """
            UPDATE verification_items
            SET document_json=?, status=?, version=?, updated_at=?
            WHERE item_id=? AND version=?
            """,
            (
                _json(document),
                item.status.value,
                item.version,
                item.updated_at.isoformat(),
                item.item_id,
                expected_version,
            ),
        )
        self._audit(
            connection,
            aggregate_type="verification_item",
            aggregate_id=item.item_id,
            event_type="verification_item_decided",
            actor=actor,
            request_id=request_id,
            payload=document,
        )
        self._outbox(
            connection,
            stream_id=f"verification:{item.item_id}",
            event_type="verification_decision_changed",
            payload=document,
        )
        return document

    def outbox_summary(self) -> dict[str, int]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM outbox_events GROUP BY status"
            ).fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}

    def process_pending_outbox(
        self,
        handler: Callable[[dict[str, Any]], None],
        *,
        limit: int = 100,
        max_attempts: int = 3,
    ) -> dict[str, int]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM outbox_events
                WHERE status IN (?, ?) AND attempts < ?
                ORDER BY stream_id, sequence_number
                LIMIT ?
                """,
                (
                    MaterializationState.PENDING.value,
                    MaterializationState.FAILED.value,
                    max_attempts,
                    limit,
                ),
            ).fetchall()
        for row in rows:
            event = {
                **dict(row),
                "payload": json.loads(row["payload_json"]),
            }
            attempts = int(row["attempts"]) + 1
            try:
                handler(event)
                status = MaterializationState.APPLIED.value
            except Exception:
                status = (
                    MaterializationState.BLOCKED_DEPENDENCY.value
                    if attempts >= max_attempts
                    else MaterializationState.FAILED.value
                )
            with self._connection() as connection:
                connection.execute(
                    """
                    UPDATE outbox_events
                    SET status=?, attempts=?
                    WHERE event_id=? AND status IN (?, ?)
                    """,
                    (
                        status,
                        attempts,
                        row["event_id"],
                        MaterializationState.PENDING.value,
                        MaterializationState.FAILED.value,
                    ),
                )
                connection.commit()
        return self.outbox_summary()

    def review_materialization_state(
        self,
        facility_id: str,
        capability_id: CapabilityId,
    ) -> MaterializationState:
        stream_id = f"facility:{facility_id}:{capability_id.value}"
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT status
                FROM outbox_events
                WHERE stream_id=? AND event_type='facility_review_changed'
                ORDER BY sequence_number DESC
                """,
                (stream_id,),
            ).fetchall()
        statuses = {str(row["status"]) for row in rows}
        for state in (
            MaterializationState.BLOCKED_DEPENDENCY,
            MaterializationState.FAILED,
            MaterializationState.PENDING,
        ):
            if state.value in statuses:
                return state
        return MaterializationState.APPLIED

    def audit_events(self, aggregate_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM audit_events WHERE aggregate_id=?
                ORDER BY created_at ASC
                """,
                (aggregate_id,),
            ).fetchall()
        return [
            {
                **dict(row),
                "actor_roles": json.loads(row["actor_roles_json"]),
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]
