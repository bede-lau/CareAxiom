# Verification Specification: Medical Desert Planner

Status: Data-grounded draft for implementation
Date: 2026-07-19
Related PRD: `.omx/plans/prd-medical-desert-planner.md`
Authenticated data profile: `.omx/plans/data-profile-databricks-virtue-dais-2026.md`

## 1. Purpose

This specification defines the evidence required to advance each delivery stage and release the live Databricks App.

No gate may pass on screenshots or a scripted happy path alone. Tests must verify:

- Source conservation.
- Source-specific structural and parse dispositions.
- Exact evidence traceability.
- Facility attribution.
- Trust behavior.
- Documentary evidence, survey context, and medical-desert separation.
- Scenario persistence.
- Failure recovery.
- MLflow trace correlation.
- Demo reliability on Databricks Free Edition.

## 2. Quality Principles

1. Missing data must not be interpreted as absent care.
2. Removing support cannot increase confidence.
3. Adding an unresolved contradiction cannot increase support.
4. Duplicate evidence or multiple fields from one source family cannot count as independent corroboration.
5. Every displayed conclusion has evidence or an insufficiency label.
6. Every aggregate can be reconstructed from contributing facilities.
7. A human override cannot erase the original machine assessment.
8. External web content is untrusted input.
9. Optional services must have deterministic fallbacks.
10. A gate failure blocks the next stage.
11. A post-office point is not a PIN centroid, boundary, or population origin.
12. An NFHS estimate is district survey context, not a population count or facility-demand quantity.
13. Join multiplicity must never change facility counts or regional documentary results.
14. Parse failure must remain distinguishable from an empty or negative value.
15. Analysis origins must exist independently of observed facility points.
16. Adding, removing, or remapping NFHS context must not change facility support, observed-record assessability, or the regional documentary classification.

## 3. Test Fixtures

G0-G7 uses a time-bounded core suite covering only the three initial demo capabilities selected in G0.

| Core fixture | Required size | Contents | Purpose |
| --- | ---: | --- | --- |
| `gold_extraction_core` | 80 | Annotated records stratified across the selected capabilities, geography, sparsity, and source format; at least 24 records per flagship capability | Extraction and citation release gate |
| `facility_source_contract_core` | 48 | Valid arrays, empty arrays, `"null"`, malformed JSON-like values, escaped delimiters, shifted columns, non-UUID spillover rows, exact duplicate UUID rows | Facility integrity, parsing, quarantine, and deduplication |
| `pincode_office_contract_core` | 40 | Repeated offices, exact duplicates, conflicting state/district labels, valid coordinates, `0`, `0.0`, `NA`, blank, malformed, and out-of-range coordinates | Postal reference and join-cardinality contract |
| `nfhs_indicator_contract_core` | 48 | Plain numerics, outer whitespace, parenthesized low-sample values, `*` suppression, blanks, and unrecognized decorations | NFHS qualifier and context parsing |
| `trust_pairs_core` | 40 pairs | Two-reviewer facility ranking with adjudication; at least 12 pairs per flagship capability and 4 cross-capability or tie-break pairs | Trust ranking release gate |
| `geo_oracle_core` | 120 | Hand-calculated records across at least two states, four districts, eight PINs, repeated-office PINs, ambiguous district mappings, unavailable coordinates, and every radius preset | Geographic aggregation release gate |
| `retrieval_queries_core` | 50 | Synonyms, negation, typo, geography, multilingual, and empty-result queries with adjudicated relevant, preferred, and forbidden document IDs | SQL and optional AI Search quality |
| `uncertainty_core` | 60 variants | Deleted, contradicted, duplicated, stale, or moved evidence | Monotonicity and abstention |
| `adversarial_core` | 30 | Prompt injection, malicious URLs, oversized text, script, SQL payloads, invalid coordinates | Focused security and resilience |
| `scenario_concurrency_core` | 12 workflows | Multiple users creating and updating scenarios | Full identity/RBAC profile only |
| `demo_snapshot` | 100-200 | Immutable records supporting the rehearsed demo, including one malformed facility field, one unavailable coordinate, one ambiguous PIN, and one qualified NFHS value | Demo fallback and honest degradation |
| `darbhanga_demo_core` | 1 immutable scenario | Source-bundle ID, policy version, 15 observed facility records, 0 maternal-policy matches, 3 emergency-surgery matches, 2 advanced-imaging matches, and NFHS values `24.9`, `69.9`, and `60.8` | Rehearsed one-minute demo regression |

Every source-contract fixture records expected:

- Raw value.
- Normalized or parsed value.
- Parse status.
- Quality flags.
- Accepted, partially parsed, quarantined, duplicate, or unavailable disposition.
- Exclusion or quarantine reason.

Each `retrieval_queries_core` row records `query_id`, query text, capability, geography filter, relevant document IDs, preferred top-tier IDs, forbidden IDs, and empty-result expectation. Recall@10 and MRR@10 are computed only from this frozen judgment set.

Post-G7 expansion is non-blocking for the hackathon release:

| Expansion fixture | Target size |
| --- | ---: |
| `gold_extraction` | 300 |
| `trust_pairs` | 250 pairs |
| `geo_oracle` | 500 |
| `retrieval_queries` | 150 |
| `uncertainty_perturbations` | 200+ variants |
| `adversarial_sources` | 100 |
| `scenario_concurrency` | 50 workflows |

The expansion suite covers emergency, ICU, NICU, maternity, trauma, oncology, surgery, and diagnostic imaging.

## 4. Annotation Protocol

Each annotated claim records:

- Facility ID and canonical name.
- Source record and source field.
- Source publisher and source-family identifier.
- Exact evidence text.
- Start and end offsets where possible.
- Capability or fact type.
- Positive, negative, or uncertain polarity.
- Explicit vs inferred.
- Entity-attribution confidence.
- Reviewer confidence.
- Disagreement reason.
- Publication time, valid time, and retrieval time where known.

Use two independent reviewers for `trust_pairs_core` and a 30-record claim-presence subset of `gold_extraction_core`.

Per-capability minimums in `gold_extraction_core`:

- At least 24 records for each of the three flagship documentary policies.
- At least 10 supported-positive claims, 6 negative or negated cases, 4 contradicted cases, and 4 stale, ambiguous, or abstention cases per capability; categories may overlap.
- Metrics report claim-level TP, FP, FN, citation denominator, and unsupported-claim count per capability as well as pooled.

Each `trust_pairs_core` row records capability, left/right facility IDs, adjudicated ordering or tie, reviewer orderings, disagreement reason, and rule version. Report exact agreements and disagreements per capability.

Targets:

- Cohen's kappa >=0.75 for claim presence.
- Weighted kappa >=0.70 for ordinal support band.
- Resolve disagreements by documented adjudication.

Authorization test profiles:

- Full identity/RBAC profile runs multi-user concurrency, ownership, collaboration, cross-user isolation, and role-boundary tests.
- Single-team demo profile uses one fixed trusted actor, hides collaboration, rejects alternate identities, and does not assert multi-user isolation.
- `scenario_concurrency` is required only for the full identity/RBAC profile.
- The core release gates use `scenario_concurrency_core`; the larger fixture remains post-G7.

## 5. Verification Matrix

| Area | Required tests | Acceptance threshold |
| --- | --- | --- |
| Unit | Parsers, normalizers, scoring components, confidence bands, geography keys, aggregators, serializers | >=90% branch coverage for scoring and aggregation; >=80% overall |
| Mutation | Core: targeted mutations for weights, penalties, duplicate handling, and abstention; expansion: broad mutation run | Core kills all listed high-risk mutations; post-G7 target >=75% |
| Contract | Bronze raw, parsed silver, consumer eligibility, Pydantic, enums, nullability; OpenAPI and generated frontend types in React branch | 100% schema-valid outputs; no silent coercion; parse failure never becomes empty evidence |
| Data quality | Exact row counts, IDs, structural shifts, JSON-like fields, duplicates, URLs, PINs, post-office coordinates, NFHS qualifiers, impossible values | Zero duplicate canonical facility IDs; zero invalid or ambiguous geography consumed by aggregates; all exclusions counted |
| Source conservation | Bronze values and row counts match the three-table source bundle | Exact counts `10,088`, `165,627`, `706`; 100% row disposition; raw value recoverability |
| Extraction | Attribution, claims, negation, quantities, exact evidence | Precision >=95%; recall >=85%; unsupported claims <=2% |
| Citation | Text and offsets resolve to preserved source | Citation-span accuracy >=95% |
| Trust scoring | Arithmetic, factors, contradictions, duplicates, caps, floors | Every score reproducible and factors sum exactly |
| Ranking | Facility pair order against adjudicated reviewers | Agreement >=85% |
| Uncertainty | Deleted support, conflicts, sparse records, abstention | >=95% of intentionally ambiguous cases show uncertainty or abstain |
| Calibration | Core: proxy-label agreement and perturbation stability; expansion: risk-coverage and bootstrap analysis | Do not claim probability calibration; ECE <=0.10 is a post-G7 target only if an adequate adjudicated set exists |
| Retrieval | SQL, AI Search hybrid/full-text if enabled, filters, freshness | Recall@10 >=0.90; MRR@10 >=0.75; geography precision 100% |
| Geographic aggregation | Facility-to-region mapping, one-row-per-PIN derivation, parent-child conservation, crosswalks, exclusions | Exact match to SQL oracle; no facility cardinality increase; documentary-summary error <=1 percentage point |
| District survey context | NFHS raw/numeric/qualifier parsing, state+district crosswalk, unmatched accounting, display isolation | All 706 rows accounted for; suppressed values unavailable; zero NFHS contribution to facility support |
| Orchestration | State transitions, retries, loop limits, validation order, idempotency | Validator always runs before publish; no repeated identical external call |
| Lakebase | CRUD, idempotency, restart, and selected authorization profile; multi-user concurrency in full identity/RBAC mode | 100% round-trip; no silent overwrite; full mode has no cross-user access; single-team mode rejects alternate identities |
| Security | Secrets, SQL injection, XSS, SSRF, prompt injection, authorization | Zero critical or high findings |
| MLflow | Trace/span structure, correlation, redaction, latency metadata | >=99% evaluated requests traced; zero secrets |
| Tavily | Mock contracts, allowlists, timeout, 401, 429, 5xx, malformed result | Max two calls per action; graceful cached/internal fallback |
| Accessibility | Keyboard, focus, labels, table alternative, contrast, reduced motion | WCAG 2.2 AA target; zero critical/serious automated issues |
| E2E | Complete planner and review workflows | 100% pass in Chromium desktop and one mobile viewport |
| Deployment | Health, SQL, Delta, Lakebase, MLflow, optional AI Search/Tavily | Required dependencies green within three minutes |
| Failure injection | Search outage, DB idle, model timeout, bad extraction, quota exhaustion | No fabricated result; saved work preserved; explicit degraded state |
| Demo | Cold and warm rehearsals | Required 10/10 passes; target 20/20; median <=52 s; maximum <=60 s |

## 6. Property Tests

Trust properties:

```text
support(evidence + qualifying_independent_source) >= support(evidence)
support(evidence - supporting_item) <= support(evidence)
support(evidence + contradiction) <= support(evidence)
support(evidence + duplicate_item) == support(evidence)
support(evidence + same_source_family_repeat) == support(evidence)
```

Assessability properties:

```text
missing_capacity != capacity_zero
missing_doctor_count != doctor_count_zero
malformed_json != empty_evidence
invalid_coordinate != valid_coordinate_at_zero
missing_nfhs_indicator != indicator_zero
suppressed_nfhs_indicator != indicator_zero
fewer_observed_records -> same_or_lower_assessability
more_unresolved_contradictions -> same_or_lower_assessability
ambiguous_geography -> same_or_lower_assessability
zero_region_entities -> insufficient_corpus_evidence
observed_record_assessability does_not_claim facility_universe_completeness
unparseable_nfhs_indicator -> no_medical_desert_candidate
nfhs_removed_or_remapped -> same_facility_support
nfhs_removed_or_remapped -> same_observed_record_assessability
nfhs_removed_or_remapped -> same_regional_documentary_classification
```

Aggregate properties:

```text
regional_result = deterministic(contributing_facilities, rules, snapshot)
analysis_origin_universe = independent_of(observed_facility_points)
zero_nearby_facilities_origin -> retained_with_insufficient_corpus_evidence
repeated_pincode_office does_not_change facility_count
join_row_multiplication does_not_change support_or_regional_summary
raw_canonical_facility_count, not joined_row_count, defines N_region_entities
child_counts + explicit_unknowns = parent_counts
saved_snapshot does not change after later review
current_result changes only through versioned input or review events
```

## 7. Source and Data Tests

### 7.1 Authenticated source inspection

The initial profile is complete. G0 automation must reproduce:

- Exactly three source tables in `virtue_foundation_dataset`.
- `facilities`: 10,088 rows and 51 columns.
- `india_post_pincode_directory`: 165,627 rows and 11 columns.
- `nfhs_5_district_health_indicators`: 706 rows and 109 columns.
- Schema fingerprints and source-bundle version.
- Facility integrity counts: 10,000 UUID-shaped rows, 9,989 distinct valid UUIDs, 11 exact duplicate rows beyond the first, and 88 quarantined non-UUID rows.
- Facility field counts among UUID rows: 10,000 descriptions, 9,944 non-empty capability arrays, 9,216 non-empty procedure arrays, 7,680 non-empty equipment arrays, 3,630 numeric doctor counts, 2,516 numeric capacity values, 4,777 valid establishment years, 3,535 parseable update dates, 9,964 broad-envelope coordinates, and 9,766 strict PINs.
- Postal counts: 19,586 distinct PINs, two exact duplicate office rows, 151,015 broad-envelope coordinate rows, 12,015 unparseable or missing coordinate rows, 13 zero-coordinate rows, 2,584 numeric non-zero out-of-envelope rows, 19,550 PINs with a valid coordinate, and ambiguous state/district counts.
- NFHS counts: 706 unique normalized state/district keys, string-indicator inventory, and qualifier profile.

The canonical contract inventory must exactly include:

- Bronze: `source_bundle_manifest`, `facility_source_snapshot`, `india_post_office_snapshot`, `nfhs5_district_snapshot`.
- Silver: `facility_row_integrity`, `facility_entity`, `facility_normalized`, `facility_field_parse`, `source_artifact`, `facility_claim`, `extraction_assertion`, `evidence_span`, `evidence_relation`, `facility_quality_signal`, `web_evidence`, `claim_validation`, `postal_office_normalized`, `pin_postal_reference`, `analysis_origin`, `district_identity_crosswalk`, `nfhs_indicator_observation`, `district_survey_context`, `geography_dimension`, `capability_dimension`.
- Gold: `facility_documentary_support`, `regional_documentary_evidence_summary`, `analysis_origin_facility_distance`, `district_context_profile`, `planning_priority_candidate`, `verification_priority`, `facility_evidence_document`, `scenario_change_feed`.

### 7.2 Schema drift

Fail the pipeline when:

- Required source columns disappear.
- A type changes incompatibly.
- Stable ID assumptions no longer hold.
- Exact source counts change without a new source-bundle version.
- Structural-quarantine, parse-failure, coordinate-unavailable, or crosswalk-unmatched rates change above approved drift thresholds.

Permit additive columns only after recording the new schema version.

### 7.3 Entity resolution

Test:

- Exact duplicate names at different addresses.
- Multiple names at one address.
- Multi-campus hospitals.
- Shared source pages.
- Chains and branches.
- Abbreviations and spelling variants.
- The verified 11 exact duplicate UUID rows.
- Non-UUID spillover rows that must never create facility entities.

No automatic merge may destroy the original record relationship.

### 7.4 Facility integrity and parsing

Test:

- Every source row ends in exactly one disposition: accepted, partially parsed, quarantined, or exact duplicate.
- Disposition counts sum to 10,088.
- The 88 non-UUID rows are quarantined before entity, extraction, geography, and scoring stages.
- The 11 repeated UUID rows collapse to 9,989 canonical entities and retain all source-row lineage.
- Shifted rows fail semantic column-domain validation even though the physical schema matches.
- JSON-like parse failure retains the raw value and `unparseable` status.
- A malformed field can create a field-level partial parse without fabricating an empty array.
- Quarantining a row cannot improve documentary confidence or create negative clinical evidence.

### 7.5 Postal geography

Test:

- PIN is represented as a strict six-character string in silver.
- One canonical `pin_postal_reference` row is produced per PIN.
- One `analysis_origin` row is retained per PIN: 19,586 total, 19,550 mappable, and 36 unavailable with a reason.
- Reordering office rows produces the same reference output and hash.
- Exact duplicate office rows are classified separately from legitimate office multiplicity.
- `0`, `0.0`, `NA`, blank, nonnumeric, nonfinite, and out-of-range coordinates are unavailable.
- Coordinate disposition uses the frozen envelope longitude `68..98` east and latitude `6.5..39` north; the four exclusive categories sum to 165,627.
- Coordinate aggregation records method, valid-coordinate count, and dispersion.
- Multiple state or district labels produce an ambiguous mapping unless a versioned reviewed rule resolves them.
- A postal reference is never labeled as a PIN centroid or population origin.

### 7.6 NFHS context

Test:

- All 706 rows retain raw state and district names plus normalized keys.
- Parenthesized values parse numerically with `low_sample_25_49`.
- `*` values parse as unavailable with `suppressed_lt_25`.
- Suppressed and missing values never become zero.
- Unknown decorations remain unparseable and block use by the selected indicator policy.
- NFHS observations never enter facility claims or documentary-support factors.
- Survey sample counts are not exposed as district population.

### 7.7 Cross-source joins

Test:

- Facility-to-office joins occur through the one-row-per-PIN reference and cannot increase facility cardinality.
- Facility-to-NFHS joins use canonical `state + district`, never district alone.
- Case and outer-whitespace normalization may match.
- Alias or historical-boundary matches retain source names, rule version, and review status.
- Undocumented fuzzy matches are forbidden.
- Every NFHS row is matched, unmatched, ambiguous, or crosswalked.
- Repeated office rows cannot duplicate facilities, evidence, distance edges, documentary summaries, or `N_region_entities`.
- Strict current baseline counts are reproducible: 9,766 valid facility PINs, 9,568 PIN-directory matches, 9,055 unambiguous district mappings, and 5,862 exact NFHS joins.

## 8. Evidence Engine Tests

Core required capability cases:

- G0 freezes the capability identifiers `maternal_emergency_documentation`, `emergency_surgery_documentation`, and `advanced_imaging_documentation`, the policy schema, DRI, reviewer, and approver. G1 freezes executable rules after fixture review.
- Each selected capability must include direct, claim-only, contradicted, stale, and insufficient-evidence records where available.
- Maternal emergency fixtures include OB-GYN plus C-section evidence, missing prerequisites, and NFHS context that remains separate.
- Emergency surgery fixtures include emergency medicine plus general surgery evidence and missing operational-readiness signals.
- Advanced imaging fixtures include CT plus MRI evidence, spelling variants, and stale or directory-only sources.

Post-G7 expansion capability cases:

- Emergency services.
- ICU.
- NICU.
- Maternity.
- Trauma.
- Oncology.
- Surgery.
- Diagnostic imaging.

Required language patterns:

- Direct positive statement.
- Negation.
- Historical capability.
- Planned future capability.
- Marketing claim.
- Multiple facilities in one page.
- General medical statement unrelated to the facility.
- Capacity with a quantity.
- Capability inferred only from the facility name.
- Historical or undated claim incorrectly converted to present tense.
- Multiple fields copied from one webpage.

Failure conditions:

- Evidence text is not found in the preserved source.
- Evidence belongs to another organization.
- Inference is emitted as explicit fact.
- A duplicate sentence becomes independent corroboration.
- A repeated assertion from one source family becomes independent corroboration.
- Unsupported clinical prerequisites are invented.

Release metrics:

- Pooled claim precision >=95%, recall >=85%, citation-span accuracy >=95%, and unsupported-claim rate <=2%.
- Each flagship capability independently achieves precision >=90%, recall >=80%, citation-span accuracy >=90%, zero cross-facility attribution failures, and no more than one unsupported emitted claim.
- A pooled pass cannot hide a capability-level failure.
- Claim-level TP, FP, and FN denominators and exact failure counts are included in the release evidence package.

## 9. Trust and Self-Correction Tests

### 9.1 Score arithmetic

- Factor ranges.
- Weight application.
- Clamp behavior.
- Band boundaries.
- Not-scoreable behavior.
- Independent contradiction-state behavior.
- Policy caps or abstention caused by unresolved contradiction.
- Configuration versioning.

### 9.2 Validator fixtures

- Claimed ICU with no additional support.
- Advanced surgery claim with configured prerequisite gaps.
- Trauma specialty inferred only from the name.
- Contradictory doctor counts.
- Contradictory bed capacity.
- Official page and third-party page conflict.
- External result names another facility.
- Source is inaccessible or stale.

### 9.3 Human review

- Confirm with source.
- Correct normalized capability.
- Mark unresolved.
- Defer.
- Attach evidence.
- Reverse an earlier decision.
- Expire an override if policy enables expiry.

The original machine assessment must remain queryable.

### 9.4 Verification Priority Queue

- Reproduce the configured weighted formula from frozen inputs.
- Each factor is normalized to `0..1`, and the final priority is clamped to `0..1`.
- Increasing classification-flip potential, affected origins or regions, active scenario references, staleness, or unresolved-contradiction severity cannot lower priority.
- Queue ordering is deterministic for equal inputs through a documented tie-breaker.
- Before a population denominator exists, the impact factor uses affected origin or region count and labels that proxy explicitly.
- When an authorized population denominator is enabled, the versioned policy replaces the proxy without changing historical queue snapshots.

## 10. Geographic and Documentary Summary Tests

- Valid and invalid PINs.
- Missing coordinates.
- Zero, `NA`, malformed, and out-of-range office coordinates.
- Repeated-office PINs and ambiguous district labels.
- Boundary coordinates.
- Facility near a district border.
- Duplicate facility within a radius.
- Multiple facilities sharing coordinates.
- Straight-line distance correctness.
- Radius presets 10 km, 25 km, and 50 km change documentary summaries deterministically.
- `analysis_origin_facility_distance` contains no edge above the maximum preset.
- Query-time filtering matches a direct distance oracle for every preset.
- The default origin universe retains exactly 19,586 PIN origins, including 19,550 mappable and 36 unavailable origins.
- At least one mappable origin with zero nearby facilities is present in `geo_oracle_core`, remains visible in results, and returns insufficient corpus evidence.
- Unknown geography is excluded and counted.
- Ambiguous geography is excluded and counted.
- `N_region_entities=0` returns no observed records and insufficient corpus evidence.
- Every assessability component uses its declared denominator and excluded count.
- Low nearby documentary support is displayed only when assessability is above threshold.
- Strong nearby documentary support reports distinct observed records and never implies capacity.
- NFHS context is displayed separately and cannot change a facility support result.
- Removing the NFHS snapshot or changing a district crosswalk leaves facility support, observed-record assessability, origin-facility distances, and regional documentary classifications byte-for-byte identical.
- Only `survey_context_availability`, district-context payloads, and planning-priority context ordering may change when NFHS is removed or remapped.
- A medical-desert candidate is blocked with the current catalog because population, completeness, operational readiness, and capacity inputs are absent.
- A planning-priority candidate displays the documentary axis, context axis, and external-validation requirement separately.

If H3 is used:

- Resolution consistency.
- Parent-child cell conservation.
- Stable conversion across Python and SQL implementations.

## 11. Retrieval Tests

Structured SQL remains the baseline.

If AI Search is retained, compare:

- SQL exact filters.
- AI Search full-text.
- AI Search hybrid.
- Reranking, if enabled.

Query classes:

- Exact capability.
- Synonym.
- Negated capability.
- Misspelling.
- Facility name.
- Geography-restricted query.
- No matching evidence.

Any retrieved evidence must preserve:

- Facility ID.
- Capability ID.
- Evidence span ID.
- Source snapshot.
- Search index update time.

## 12. Tavily Tests

### 12.1 Unit and mock tests

- Search request construction.
- Domain restriction.
- India country boost.
- Search depth and credit policy.
- Maximum results.
- Exact result parsing.
- Extract parsing.
- URL validation.
- Timeout.
- 401.
- 429 with `retry-after`.
- 5xx retry.
- Malformed response.
- Empty response.
- Prompt-injection text.

### 12.2 Live canary

Before each demo deployment:

- Confirm app egress to `api.tavily.com`.
- Run one low-cost basic search.
- Verify the result is cached.
- Verify the key is not present in logs or traces.

If the canary fails:

- Set `TAVILY_MODE=cached`.
- Disable live verification actions.
- Confirm the UI shows retrieval dates.
- Confirm an HTTP transport spy records zero Tavily network attempts.
- Validate cache manifest fields: query, request ID, source URL, publisher, content hash, retrieval time, expiry time, importing actor/job, approver, and usage.
- Confirm expired evidence remains visible as stale and cannot newly upgrade a support band.
- Run the full demo in cached mode.

## 13. Lakebase Tests

- Connection after scale-to-zero.
- OAuth/token refresh or adapter reconnect behavior.
- Scenario create and retrieve.
- Optimistic concurrency conflict.
- Duplicate idempotency key.
- Audit event creation.
- Override reversal.
- Reviewer isolation.
- Persistence after App redeploy.
- Partial failure between Lakebase write and Delta recalculation request.
- Atomic review decision, audit event, and outbox event.
- Outbox event sequence and idempotency.
- Bound recalculation Job trigger.
- Scheduled backup drain of missed events.
- `stage_run` creation, retry, cancellation, and replay.
- Single-writer ordering with one concurrent Job run.
- Materialization checkpoint and derived Delta version.
- Immediate read-your-write in the facility panel.
- Pending, applied, and failed aggregate states.
- Dead-letter or `failed_final` diagnostics.
- Event N fails while N+1 in the same stream is pending.
- N+1 becomes `blocked_dependency`.
- An event in a different stream continues.
- Repair/replay unblocks the stream without duplication.
- Audited administrator supersession advances the checkpoint and preserves the skipped event history.

A committed review decision must remain durable and replayable if recalculation fails. Delta is tested as a derived read model, not the authoritative review store.

## 14. MLflow Tests

Every evaluated planner result should contain:

- Root request trace.
- SQL or retrieval span.
- Facility scoring batch reference or sampled fixture spans.
- Regional documentary-summary span or materialized result reference.
- Scenario or review persistence span for writes.
- Tavily span when used.
- Error and retry metadata.

Assertions:

- Trace ID is returned in internal response metadata.
- Result IDs correlate to trace IDs.
- No Tavily key, OAuth token, or secret appears.
- User notes are not included in model spans unless explicitly required.
- Trace overhead is below 10% in the measured workflow.
- A 10,000-record batch produces one root trace and stage-level spans, not one span per record.
- Per-record spans are limited to evaluation fixtures, sampled failures, and explicit debugging.
- Async trace logging does not lose required root/stage traces during normal shutdown.

## 15. API and Frontend Tests

### 15.1 Contract

- OpenAPI schema snapshot.
- Generated TypeScript client compiles.
- Stable error codes.
- Pagination and filters.
- Idempotency headers.
- Version conflict response.
- Actor identity and role response fixtures.
- Materialization version and state fields.
- Canonical documentary fields use `documentary_support_index`, `observed_record_assessability`, `postal_reference_point`, `analysis_origin`, and `survey_context_availability`.
- Scenario responses include a deterministic current-vs-saved change summary with changed field, prior version, current version, reason, and affected result IDs.
- JSON and CSV exports validate against frozen schemas and include assumptions, citations, uncertainty, source-bundle ID, policy version, and saved-snapshot version.
- The human-readable decision brief is generated only after the core app is stable and contains the same conclusions, assumptions, citations, uncertainty, and version identifiers as the machine-readable exports.

### 15.2 Frontend

- Loading preserves last stable map.
- Empty result differs from insufficient data.
- Insufficient corpus evidence is not colored as missing care.
- Strong nearby documentary support is not labeled as capacity, availability, or operational readiness.
- NFHS survey context is visually and semantically separate from facility documentary evidence.
- Postal reference points display method and ambiguity and are never labeled as PIN centroids.
- Evidence drawer renders long source text safely.
- Keyboard user can complete the workflow.
- Table selection synchronizes with map selection.
- Mobile controls do not overlap.
- Reduced motion disables crisis animation.
- Facility review shows committed Lakebase state immediately.
- Map shows `update pending` when the review version is newer than the materialized aggregate.
- Single-team demo mode hides collaboration controls and does not claim multi-user isolation.
- React branch validates the generated OpenAPI client, map rail, desktop viewport, and mobile viewport.
- Streamlit branch validates the planner adapter, narrow viewport, facility panel/expander, and table-first keyboard workflow.
- City selection is absent or disabled until the G1 city-normalization gate passes; after activation, only accepted versioned city keys are selectable and switching capability preserves the city.
- Medical Desert Planner is the product name, default route, and primary navigation item.
- Facility Trust Desk remains embedded in facility drill-down.
- Data Readiness Desk remains a supporting queue/review workflow rather than a peer product homepage.
- Referral Copilot is absent from default navigation through G7.

### 15.3 E2E workflows

Planner:

`select capability -> select geography -> inspect documentary summary -> inspect separate survey context -> open facility -> inspect evidence -> save scenario -> reopen`

Review:

`open queue -> inspect item -> attach/confirm/correct -> publish decision -> verify current regional result changes -> verify saved snapshot remains`

Failure:

`disable optional service -> run planner -> show explicit degraded state -> complete deterministic workflow`

Source-specific:

- Load all three snapshots and verify exact row and disposition accounting.
- Open a facility with a malformed JSON-like field; the UI shows preserved raw evidence and insufficiency rather than empty negative evidence.
- Select a repeated-office PIN; every canonical facility appears once.
- Select a PIN with zero, `NA`, or unavailable coordinates; no false marker or distance edge appears.
- Open a district with a parenthesized NFHS value; raw value, numeric value, `low_sample_25_49`, survey period, and sample metadata are traceable.
- Open a district with an asterisk NFHS value; the metric is unavailable and cannot enter a priority calculation.
- An unresolved district crosswalk displays unavailable context and unmatched counts rather than a guessed match.
- Reprocessing the same source bundle produces identical quarantine sets, canonical PIN references, crosswalk results, documentary summaries, and aggregate hashes.
- Load `darbhanga_demo_core` and reproduce 15 observed facility records, 0 maternal-policy matches, 3 emergency-surgery matches, 2 advanced-imaging matches, and NFHS context values `24.9`, `69.9`, and `60.8` under the frozen source-bundle and policy versions.
- Save a scenario, change one review decision or policy version, and verify the current-vs-saved change summary without mutating the saved snapshot.
- Export the same scenario to JSON and CSV and verify equivalent facility IDs, result classifications, assumptions, citations, and version identifiers.
- Generate the human-readable decision brief and verify semantic equivalence with the JSON export, no hidden chain-of-thought, and no unsupported conclusion.

## 16. Security Tests

- SQL injection against all filters and IDs.
- XSS in facility name, source text, reviewer note, and Tavily passage.
- SSRF through source URLs.
- Non-HTTP URL schemes.
- Private IP and metadata service targets.
- Prompt injection in external pages.
- Oversized payloads.
- Full identity/RBAC: unauthorized scenario access.
- Full identity/RBAC: unauthorized review action.
- Full identity/RBAC: Planner attempting Reviewer action.
- Full identity/RBAC: Reviewer attempting Administrator action.
- Both profiles: unmapped or untrusted actor identity.
- Single-team demo: alternate identity rejected and collaboration controls absent.
- App service-principal access incorrectly treated as product authorization.
- Secret scanning for repository, logs, and traces.
- Dependency vulnerability scan.

Release requires zero critical and high findings.

## 17. Performance Tests

Measure cold and warm:

| Operation | Target |
| --- | --- |
| Capability/geography metadata | p95 <=500 ms warm |
| Map documentary-evidence query | p95 <=2 s warm |
| Region drill-down | p95 <=2 s warm |
| Facility evidence | p95 <=2 s warm, <=4 s with search |
| Scenario write | p95 <=750 ms warm |
| Review command acknowledgement | p95 <=1.5 s |
| Review materialization | p95 <=60 s warm |
| Agent workflow without Tavily | p95 <=10 s |
| Live Tavily workflow | p95 <=15 s |

Load shape:

- 10 concurrent interactive users.
- Repeated capability and geography changes.
- Concurrent scenario writes.
- Cold warehouse and Lakebase recovery.

## 18. Failure Injection

Inject:

- SQL warehouse cold start or temporary error.
- Missing Delta view.
- Stale AI Search index.
- Model endpoint timeout.
- Tavily timeout or quota exhaustion.
- Lakebase scale-to-zero reconnect.
- Malformed extraction output.
- Invalid review event.
- Bound Job trigger failure.
- Outbox event stuck pending.
- Materialization merge failure.
- App restart after Lakebase commit but before Job trigger.
- Missing geometry.
- App restart during a write.

Expected behavior:

- No fabricated result.
- Explicit failed component.
- Retry only where safe.
- Saved work preserved.
- Deterministic fallback where defined.
- Trace contains the failure and recovery.

## 19. Gate Checklist

### G0 Platform and contract

- [ ] Presentation branch decision is recorded.
- [ ] `uv sync --frozen` passes with committed `uv.lock`.
- [ ] Selected deployment artifact is created from the declared manifest and deployed from `.dist/<adapter>-app`.
- [ ] React branch: `.dist/react-app` contains the Node manifests and frontend; root build is reproducible, FastAPI starts through the production Python entrypoint, and the React shell completes one typed request.
- [ ] React branch: root `npm ci` and `npm run build` pass with committed `package-lock.json`.
- [ ] Streamlit branch: `.dist/streamlit-app` contains no `package.json`, `package-lock.json`, `frontend/`, or Node build artifacts.
- [ ] Streamlit branch: the exact Streamlit-only artifact deploys, starts through the production entrypoint, and completes the equivalent application-service and persistence flow without attempting a Node install or build.
- [ ] Databricks resources bound.
- [ ] All three physical source contracts and schema fingerprints are frozen.
- [ ] Exact counts `10,088`, `165,627`, and `706` are verified.
- [ ] Source-bundle manifest is versioned.
- [ ] Facility integrity accounting reproduces 10,000 UUID-shaped rows, 9,989 canonical UUIDs, 11 exact duplicate rows, and 88 quarantined rows.
- [ ] Facility field accounting reproduces all frozen numerators and one-decimal coverage percentages.
- [ ] Postal accounting reproduces 19,586 PINs, two exact duplicate rows, all four coordinate dispositions, 19,550 PINs with a valid coordinate, and the ambiguity profile.
- [ ] NFHS accounting reproduces 706 unique normalized keys and the string-indicator qualifier profile.
- [ ] NFHS is formally blocked from population-denominator and facility-support roles.
- [ ] SQL read through the App service principal passes.
- [ ] Lakebase command, audit, and outbox transaction passes.
- [ ] Bound recalculation Job stub and `stage_run` pass.
- [ ] Correlated MLflow root/stage trace passes.
- [ ] Trusted actor extraction or documented single-team mode passes.
- [ ] Product-role strategy is documented.
- [ ] Authorization test profile is selected and its conditional tests pass.
- [ ] Initial capability identifiers, policy schema, DRI, named reviewer, and gate approver are approved; executable rules remain a G1 deliverable.
- [ ] React continuation or Streamlit fallback decision is recorded.
- [ ] Tavily mode decided.

### G1 Data foundation

- [ ] Bronze source conservation and complete disposition accounting pass.
- [ ] Facility source rows resolve to accepted, partially parsed, quarantined, or exact duplicate states.
- [ ] Quarantined facility rows reach no entity, claim, geography, or regional output.
- [ ] Stable canonical facility IDs and exact duplicate collapse pass.
- [ ] JSON-like parser contracts preserve raw values and failure states.
- [ ] One-row-per-PIN postal-reference derivation passes.
- [ ] One analysis origin is retained per PIN: 19,586 total, 19,550 mappable, and 36 unavailable with reasons.
- [ ] Repeated post-office rows cannot increase facility cardinality.
- [ ] Invalid and ambiguous geography is excluded and counted.
- [ ] NFHS numeric and qualifier parsing passes.
- [ ] All 706 NFHS rows are matched, unmatched, ambiguous, or crosswalked with a reason.
- [ ] District geometry is versioned and tested or explicitly disabled.
- [ ] Annotation guide approved.
- [ ] Initial capability taxonomy is versioned.
- [ ] Executable documentary, prerequisite, contradiction, and freshness rules pass fixture review and named approval.
- [ ] City selection is enabled only if its versioned normalization-quality threshold passes; otherwise it remains disabled without blocking other geography workflows.
- [ ] Observed-record-assessability counts, denominators, and formula are versioned.
- [ ] Radius presets, facility-independent analysis-origin strategy, postal-reference method, district crosswalk, and distance-table contract are versioned.
- [ ] A zero-nearby-facility origin remains visible and returns insufficient corpus evidence.
- [ ] Removing or remapping NFHS changes only survey-context outputs.

### G2 Evidence

- [ ] Precision >=95%.
- [ ] Recall >=85%.
- [ ] Citation accuracy >=95%.
- [ ] Unsupported claims <=2%.
- [ ] Cross-facility attribution failures = 0 in golden set.
- [ ] Every flagship capability also passes its independent precision, recall, citation, attribution, and unsupported-claim floors.

### G3 Trust

- [ ] Documentary-support arithmetic and bands pass.
- [ ] Contradiction state remains separate and policy caps or abstention are reproducible.
- [ ] Monotonicity passes.
- [ ] Contradiction properties pass.
- [ ] Ambiguous abstention >=95%.
- [ ] Ranking agreement >=85%.
- [ ] Each flagship capability has at least 12 adjudicated pairs and achieves at least 10/12 agreement; no pooled pass can hide a capability-level ranking failure.

### G4 Planner

- [ ] Primary workflow E2E passes.
- [ ] Medical Desert Planner is the default route and product identity.
- [ ] Facility Trust Desk remains an embedded drill-down.
- [ ] Map/table accessibility passes.
- [ ] Warm interaction SLOs pass.
- [ ] Citation or insufficiency coverage = 100%.
- [ ] React branch: generated client and desktop/mobile E2E pass.
- [ ] Streamlit branch: application-service contract and desktop/narrow-viewport E2E pass.

### G5 Persistence and review

- [ ] Scenario round-trip = 100%.
- [ ] Data Readiness Desk remains a supporting planner/review workflow rather than a co-equal product.
- [ ] Concurrency conflict handling passes.
- [ ] Audit history passes.
- [ ] Review is immediately visible in the facility panel.
- [ ] Outbox materializes Delta changes idempotently and in order.
- [ ] Version mismatch shows `update pending`.
- [ ] Failed materialization replays without duplicate logical decisions.
- [ ] Saved snapshot remains immutable.

### G6 Hardening

- [ ] Optional-service fallbacks pass.
- [ ] Security has zero high/critical findings.
- [ ] Trace correlation >=99%.
- [ ] Failure injection passes.

### G7 Core demo release

- [ ] App restarted and warmed.
- [ ] Quota and endpoint checks pass.
- [ ] Demo snapshot available.
- [ ] Required 10/10 rehearsals pass; target 20/20.
- [ ] Median <=52 s and maximum <=60 s.
- [ ] Referral Copilot is disabled by default and absent from default navigation.

### G8 Optional crisis mode

- [ ] G7 remains green.
- [ ] Source, timestamp, refresh status, and live/uploaded/demo label are visible.
- [ ] Crisis failure does not affect the core planner.

### G9 Referral extension

- [ ] G7 remains green; G8 is not required.
- [ ] G0-G7 remain green with Referral Copilot enabled and disabled.
- [ ] Referral Copilot remains separately namespaced, disabled by default, and never replaces the Planner as the default route or product identity.
- [ ] Evidence-grounded shortlist passes.
- [ ] Distance and availability language passes.
- [ ] Forced referral failures do not affect Planner, Facility Trust Desk, Data Readiness Desk, scenarios, or core navigation.

## 20. Release Evidence Package

The final repository should include:

- Test reports.
- Data contract and profiling report.
- Golden-set metrics.
- MLflow experiment and representative trace IDs.
- Security scan summary.
- Accessibility report.
- Demo rehearsal log.
- Deployment runbook.
- Known limitations.
- Screenshot or recording of the live Databricks App.

## 21. Stop Condition

Testing is complete when all required G0-G7 core checks are green, no known critical or high defects remain, the one-minute workflow passes 10 consecutive rehearsals at 60 seconds or less, and the app can produce a fully cited or explicitly insufficient result after a cold start without developer intervention. Crisis mode and Referral Copilot remain optional.
