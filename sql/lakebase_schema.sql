-- Operational command store for Medical Desert Planner.
-- SQLite is the local adapter; these PostgreSQL-compatible definitions shape Lakebase.

CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    document_json JSONB NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    verdict TEXT,
    contradiction_state TEXT,
    reason TEXT NOT NULL,
    evidence_ids_json JSONB NOT NULL,
    actor_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (facility_id, capability_id, version)
);

CREATE TABLE IF NOT EXISTS verification_items (
    item_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    document_json JSONB NOT NULL,
    priority DOUBLE PRECISION NOT NULL CHECK (priority BETWEEN 0 AND 1),
    status TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_roles_json JSONB NOT NULL,
    request_id TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox_events (
    event_id TEXT PRIMARY KEY,
    stream_id TEXT NOT NULL,
    sequence_number BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (stream_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    actor_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (actor_id, operation, idempotency_key)
);

CREATE INDEX IF NOT EXISTS reviews_facility_capability_version_idx
    ON reviews (facility_id, capability_id, version DESC);
CREATE INDEX IF NOT EXISTS verification_priority_idx
    ON verification_items (priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS outbox_pending_idx
    ON outbox_events (status, stream_id, sequence_number);
CREATE INDEX IF NOT EXISTS audit_aggregate_idx
    ON audit_events (aggregate_type, aggregate_id, created_at);
