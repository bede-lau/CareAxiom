# G0-G7 Test Strategy

## Scope

The suite uses an offline-first pyramid:

- Unit and property tests: parsers, coordinate dispositions, NFHS qualifiers, scoring, assessability, priority, identity, and immutable fixture contracts.
- Integration tests: demo and Databricks analytics, SQLite/Lakebase-compatible scenarios,
  idempotency, optimistic concurrency, review audit, outbox creation, and Delta overlay
  materialization.
- Contract tests: source counts, FastAPI/OpenAPI, health, exports, hierarchy, default-off referral behavior, and connected catalog checks.
- E2E tests: planner, Facility Trust Desk, separate NFHS context, geography conflicts, scenario save/reopen, and navigation.

## Gate Mapping

| Gate | Automated evidence |
| --- | --- |
| G0 | Fixture SHA256, exact source inventory, canonical contract names, OpenAPI/health when app exists |
| G1 | Facility parsing states, coordinate dispositions, NFHS qualifiers, origin retention, geography conflicts |
| G2 | Fixture framework for exact evidence spans and production extraction adapters as they land |
| G3 | Score arithmetic, contradiction separation, monotonicity, priority formula |
| G4 | Product hierarchy, embedded Trust Desk, planner browser workflow, separate survey context |
| G5 | Scenario round-trip, idempotency, concurrency conflict, immutable history, audit/outbox, exports |
| G6 | Cached optional-service defaults, deterministic fallback contracts, connected tests isolated |
| G7 | Darbhanga exact values and IDs, browser workflow, Referral Copilot disabled/default-hidden |

## Connected Tests

Tests marked `connected` never run by default. They require:

- `DATABRICKS_SERVER_HOSTNAME`
- `DATABRICKS_HTTP_PATH`
- `DATABRICKS_TOKEN`

CI keeps the connected job disabled until protected secrets and an explicit release trigger are configured.

## Fixture Rules

- Every JSON fixture must be listed in `fixtures/manifest.sha256`.
- Parse failure is not empty evidence.
- Missing numeric values are not reported zero.
- Repeated post offices cannot increase facility cardinality.
- NFHS values never change facility support or regional documentary classification.
- Geography conflicts remain reviewable and excluded from confident distance/district aggregation.
- Saved snapshots remain immutable after review events.

## Stop Condition

G0-G7 is releasable only after all offline tests pass, connected checks pass in the deployment environment, Chromium desktop/mobile pass, and ten one-minute rehearsals finish at or below 60 seconds.
