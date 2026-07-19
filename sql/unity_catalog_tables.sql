-- Project-owned objects only. This file never creates or modifies source-catalog objects.
CREATE SCHEMA IF NOT EXISTS {{project_catalog}}.bronze
COMMENT 'Immutable source-bundle conservation for Medical Desert Planner';

CREATE SCHEMA IF NOT EXISTS {{project_catalog}}.silver
COMMENT 'Normalized, traceable, non-aggregated analytical contracts';

CREATE SCHEMA IF NOT EXISTS {{project_catalog}}.gold
COMMENT 'Published documentary evidence and planner read models';

CREATE SCHEMA IF NOT EXISTS {{project_catalog}}.evaluation
COMMENT 'Pipeline run state, validation results, and release evidence';

CREATE TABLE IF NOT EXISTS {{project_catalog}}.bronze.source_bundle_manifest (
  source_bundle_id STRING NOT NULL,
  source_catalog STRING NOT NULL,
  source_schema STRING NOT NULL,
  source_table STRING NOT NULL,
  source_grain STRING NOT NULL,
  expected_row_count BIGINT NOT NULL,
  observed_row_count BIGINT,
  expected_column_count INT NOT NULL,
  observed_column_count INT,
  schema_fingerprint STRING,
  profiled_at TIMESTAMP,
  profile_status STRING,
  contract_version STRING NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.bronze.facility_source_snapshot (
  source_bundle_id STRING NOT NULL,
  source_row_id STRING NOT NULL,
  source_duplicate_ordinal INT NOT NULL,
  raw_hash STRING NOT NULL,
  raw_payload STRING NOT NULL,
  unique_id STRING,
  name STRING,
  description STRING,
  specialties_raw STRING,
  procedure_raw STRING,
  equipment_raw STRING,
  capability_raw STRING,
  source_urls_raw STRING,
  source_types_raw STRING,
  source_raw STRING,
  address_city STRING,
  address_state_or_region STRING,
  address_zip_or_postcode STRING,
  latitude DOUBLE,
  longitude DOUBLE,
  number_doctors_raw STRING,
  capacity_raw STRING,
  year_established_raw STRING,
  recency_of_page_update_raw STRING,
  ingested_at TIMESTAMP NOT NULL
) USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {{project_catalog}}.bronze.india_post_office_snapshot (
  source_bundle_id STRING NOT NULL,
  source_row_id STRING NOT NULL,
  source_duplicate_ordinal INT NOT NULL,
  raw_hash STRING NOT NULL,
  raw_payload STRING NOT NULL,
  circlename STRING,
  regionname STRING,
  divisionname STRING,
  officename STRING,
  pincode STRING,
  officetype STRING,
  delivery STRING,
  district STRING,
  statename STRING,
  latitude_raw STRING,
  longitude_raw STRING,
  ingested_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.bronze.nfhs5_district_snapshot (
  source_bundle_id STRING NOT NULL,
  source_row_id STRING NOT NULL,
  raw_hash STRING NOT NULL,
  raw_payload STRING NOT NULL,
  state_raw STRING,
  district_raw STRING,
  households_surveyed DOUBLE,
  women_15_49_interviewed DOUBLE,
  men_15_54_interviewed DOUBLE,
  ingested_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.facility_row_integrity (
  source_bundle_id STRING NOT NULL,
  source_row_id STRING NOT NULL,
  raw_hash STRING NOT NULL,
  unique_id_raw STRING,
  uuid_shape_valid BOOLEAN NOT NULL,
  duplicate_ordinal INT,
  semantic_domain_valid BOOLEAN NOT NULL,
  disposition STRING NOT NULL,
  quarantine_reason STRING,
  canonical_facility_id STRING,
  classified_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.facility_entity (
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  canonical_source_row_id STRING NOT NULL,
  source_row_count INT NOT NULL,
  exact_duplicate_count INT NOT NULL,
  canonical_name STRING,
  entity_resolution_method STRING NOT NULL,
  entity_resolution_version STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.facility_normalized (
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  canonical_name STRING,
  normalized_name STRING,
  description STRING,
  city_raw STRING,
  city_normalized STRING,
  state_raw STRING,
  state_normalized STRING,
  pincode STRING,
  latitude DOUBLE,
  longitude DOUBLE,
  coordinate_status STRING NOT NULL,
  number_doctors DOUBLE,
  number_doctors_status STRING NOT NULL,
  capacity DOUBLE,
  capacity_status STRING NOT NULL,
  year_established INT,
  year_established_status STRING NOT NULL,
  page_update_date DATE,
  freshness_status STRING NOT NULL,
  pin_reference_distance_km DOUBLE,
  location_conflict_status STRING NOT NULL,
  regional_aggregation_eligible BOOLEAN NOT NULL,
  normalized_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.facility_field_parse (
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  source_row_id STRING NOT NULL,
  field_name STRING NOT NULL,
  raw_value STRING,
  parsed_values ARRAY<STRING>,
  parse_status STRING NOT NULL,
  parser_version STRING NOT NULL,
  quality_flags ARRAY<STRING>,
  parsed_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.source_artifact (
  source_artifact_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  facility_id STRING,
  source_row_id STRING,
  source_field STRING NOT NULL,
  source_family STRING,
  publisher STRING,
  source_url STRING,
  raw_content STRING,
  content_hash STRING NOT NULL,
  publication_time TIMESTAMP,
  valid_time TIMESTAMP,
  retrieval_time TIMESTAMP,
  artifact_status STRING NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.facility_claim (
  claim_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  capability_id STRING NOT NULL,
  claim_type STRING NOT NULL,
  polarity STRING NOT NULL,
  explicitness STRING NOT NULL,
  claim_text STRING NOT NULL,
  source_artifact_id STRING NOT NULL,
  extraction_method STRING NOT NULL,
  extraction_version STRING NOT NULL,
  claim_status STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.extraction_assertion (
  assertion_id STRING NOT NULL,
  claim_id STRING NOT NULL,
  assertion_type STRING NOT NULL,
  assertion_value STRING,
  confidence DOUBLE,
  model_name STRING,
  prompt_version STRING,
  rule_version STRING,
  trace_id STRING,
  span_id STRING,
  status STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.evidence_span (
  evidence_span_id STRING NOT NULL,
  claim_id STRING NOT NULL,
  source_artifact_id STRING NOT NULL,
  source_field STRING NOT NULL,
  evidence_text STRING NOT NULL,
  start_offset INT,
  end_offset INT,
  span_hash STRING NOT NULL,
  citation_status STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.evidence_relation (
  evidence_relation_id STRING NOT NULL,
  left_evidence_span_id STRING NOT NULL,
  right_evidence_span_id STRING NOT NULL,
  relation_type STRING NOT NULL,
  source_family_independent BOOLEAN NOT NULL,
  rule_version STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.facility_quality_signal (
  quality_signal_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  signal_type STRING NOT NULL,
  signal_value DOUBLE,
  signal_status STRING NOT NULL,
  details STRING,
  rule_version STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.web_evidence (
  web_evidence_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  capability_id STRING,
  query_text STRING NOT NULL,
  source_url STRING NOT NULL,
  publisher STRING,
  source_family STRING,
  content_text STRING,
  content_hash STRING,
  retrieval_time TIMESTAMP NOT NULL,
  expiry_time TIMESTAMP,
  verification_status STRING NOT NULL,
  request_id STRING,
  importing_actor STRING,
  approver STRING,
  usage_note STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.claim_validation (
  validation_id STRING NOT NULL,
  claim_id STRING NOT NULL,
  validator_name STRING NOT NULL,
  validator_version STRING NOT NULL,
  validation_status STRING NOT NULL,
  severity STRING NOT NULL,
  finding_code STRING,
  finding_details STRING,
  support_cap DOUBLE,
  abstain BOOLEAN NOT NULL,
  validated_at TIMESTAMP NOT NULL,
  trace_id STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.postal_office_normalized (
  source_bundle_id STRING NOT NULL,
  source_row_id STRING NOT NULL,
  pincode STRING,
  office_name STRING,
  state_raw STRING,
  state_normalized STRING,
  district_raw STRING,
  district_normalized STRING,
  latitude DOUBLE,
  longitude DOUBLE,
  coordinate_status STRING NOT NULL,
  exact_duplicate BOOLEAN NOT NULL,
  normalized_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.pin_postal_reference (
  source_bundle_id STRING NOT NULL,
  pincode STRING NOT NULL,
  postal_reference_latitude DOUBLE,
  postal_reference_longitude DOUBLE,
  reference_status STRING NOT NULL,
  reference_method STRING NOT NULL,
  valid_coordinate_count INT NOT NULL,
  office_count INT NOT NULL,
  coordinate_dispersion_degrees DOUBLE,
  state_candidates ARRAY<STRING>,
  district_candidates ARRAY<STRING>,
  geography_status STRING NOT NULL,
  administrative_label_semantics STRING NOT NULL,
  geography_version STRING NOT NULL,
  reference_hash STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.analysis_origin (
  source_bundle_id STRING NOT NULL,
  analysis_origin_id STRING NOT NULL,
  origin_type STRING NOT NULL,
  pincode STRING NOT NULL,
  latitude DOUBLE,
  longitude DOUBLE,
  origin_status STRING NOT NULL,
  unavailable_reason STRING,
  geography_status STRING NOT NULL,
  reference_hash STRING NOT NULL,
  geography_version STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.district_identity_crosswalk (
  crosswalk_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  source_system STRING NOT NULL,
  source_state STRING NOT NULL,
  source_district STRING NOT NULL,
  normalized_state STRING NOT NULL,
  normalized_district STRING NOT NULL,
  canonical_state STRING,
  canonical_district STRING,
  match_status STRING NOT NULL,
  match_reason STRING NOT NULL,
  review_status STRING NOT NULL,
  crosswalk_version STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.nfhs_indicator_observation (
  observation_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  source_row_id STRING NOT NULL,
  state_raw STRING NOT NULL,
  district_raw STRING NOT NULL,
  normalized_state STRING NOT NULL,
  normalized_district STRING NOT NULL,
  indicator_id STRING NOT NULL,
  raw_value STRING,
  numeric_value DOUBLE,
  qualifier STRING NOT NULL,
  parse_status STRING NOT NULL,
  unit STRING,
  survey_period STRING NOT NULL,
  source_version STRING NOT NULL,
  parsed_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.district_survey_context (
  source_bundle_id STRING NOT NULL,
  district_context_id STRING NOT NULL,
  normalized_state STRING NOT NULL,
  normalized_district STRING NOT NULL,
  crosswalk_id STRING,
  survey_context_availability STRING NOT NULL,
  matched_observation_count INT NOT NULL,
  unavailable_observation_count INT NOT NULL,
  context_payload STRING NOT NULL,
  source_version STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.geography_dimension (
  geography_id STRING NOT NULL,
  geography_type STRING NOT NULL,
  geography_key STRING NOT NULL,
  display_name STRING NOT NULL,
  parent_geography_id STRING,
  latitude DOUBLE,
  longitude DOUBLE,
  geometry_status STRING NOT NULL,
  geography_version STRING NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.silver.capability_dimension (
  capability_id STRING NOT NULL,
  display_name STRING NOT NULL,
  policy_definition STRING NOT NULL,
  prerequisite_definition STRING NOT NULL,
  policy_version STRING NOT NULL,
  approval_status STRING NOT NULL,
  enabled BOOLEAN NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.facility_documentary_support (
  result_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  capability_id STRING NOT NULL,
  documentary_support_index DOUBLE,
  support_band STRING NOT NULL,
  contradiction_state STRING NOT NULL,
  direct_evidence_specificity DOUBLE NOT NULL,
  independent_source_corroboration DOUBLE NOT NULL,
  source_quality DOUBLE NOT NULL,
  entity_attribution_quality DOUBLE NOT NULL,
  freshness DOUBLE NOT NULL,
  prerequisite_support DOUBLE NOT NULL,
  evidence_span_ids ARRAY<STRING> NOT NULL,
  exclusion_reasons ARRAY<STRING> NOT NULL,
  policy_version STRING NOT NULL,
  result_hash STRING NOT NULL,
  calculated_at TIMESTAMP NOT NULL
) USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.analysis_origin_facility_distance (
  source_bundle_id STRING NOT NULL,
  analysis_origin_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  distance_km DOUBLE NOT NULL,
  maximum_radius_km INT NOT NULL,
  geography_version STRING NOT NULL,
  edge_hash STRING NOT NULL,
  calculated_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.regional_documentary_evidence_summary (
  summary_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  analysis_origin_id STRING NOT NULL,
  capability_id STRING NOT NULL,
  radius_km INT NOT NULL,
  regional_classification STRING NOT NULL,
  observed_record_assessability DOUBLE,
  n_source_rows BIGINT NOT NULL,
  n_structurally_eligible_rows BIGINT NOT NULL,
  n_canonical_facility_entities BIGINT NOT NULL,
  n_region_entities BIGINT NOT NULL,
  n_capability_assessed_entities BIGINT NOT NULL,
  strong_support_count BIGINT NOT NULL,
  partial_support_count BIGINT NOT NULL,
  weak_support_count BIGINT NOT NULL,
  contradiction_count BIGINT NOT NULL,
  excluded_count BIGINT NOT NULL,
  contributing_facility_ids ARRAY<STRING> NOT NULL,
  exclusion_reasons ARRAY<STRING> NOT NULL,
  policy_version STRING NOT NULL,
  geography_version STRING NOT NULL,
  summary_hash STRING NOT NULL,
  calculated_at TIMESTAMP NOT NULL
) USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.district_context_profile (
  district_profile_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  normalized_state STRING NOT NULL,
  normalized_district STRING NOT NULL,
  survey_context_availability STRING NOT NULL,
  context_payload STRING NOT NULL,
  source_version STRING NOT NULL,
  profile_hash STRING NOT NULL,
  calculated_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.planning_priority_candidate (
  candidate_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  analysis_origin_id STRING NOT NULL,
  capability_id STRING NOT NULL,
  radius_km INT NOT NULL,
  documentary_classification STRING NOT NULL,
  observed_record_assessability DOUBLE,
  survey_context_availability STRING NOT NULL,
  context_axis_score DOUBLE,
  external_validation_required BOOLEAN NOT NULL,
  medical_desert_label_enabled BOOLEAN NOT NULL,
  candidate_hash STRING NOT NULL,
  calculated_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.verification_priority (
  verification_item_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  facility_id STRING,
  claim_id STRING,
  capability_id STRING,
  reason STRING NOT NULL,
  classification_flip_potential DOUBLE NOT NULL,
  affected_origin_or_region_factor DOUBLE NOT NULL,
  active_scenario_reference_factor DOUBLE NOT NULL,
  evidence_staleness DOUBLE NOT NULL,
  contradiction_severity DOUBLE NOT NULL,
  priority_score DOUBLE NOT NULL,
  impact_proxy_label STRING NOT NULL,
  status STRING NOT NULL,
  deterministic_tiebreaker STRING NOT NULL,
  calculated_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.facility_evidence_document (
  document_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  capability_id STRING,
  document_text STRING NOT NULL,
  evidence_span_ids ARRAY<STRING> NOT NULL,
  source_artifact_ids ARRAY<STRING> NOT NULL,
  geography_keys ARRAY<STRING> NOT NULL,
  freshness_time TIMESTAMP,
  document_hash STRING NOT NULL,
  updated_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.scenario_change_feed (
  change_id STRING NOT NULL,
  scenario_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  saved_snapshot_version STRING NOT NULL,
  current_materialization_version STRING NOT NULL,
  changed_field STRING NOT NULL,
  prior_value STRING,
  current_value STRING,
  reason STRING NOT NULL,
  affected_result_ids ARRAY<STRING> NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.facility_review_overlay (
  review_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  capability_id STRING NOT NULL,
  verdict STRING,
  contradiction_state STRING,
  reason STRING NOT NULL,
  evidence_ids_json STRING NOT NULL,
  actor_id STRING NOT NULL,
  review_version BIGINT NOT NULL,
  review_status STRING NOT NULL,
  reviewed_at TIMESTAMP NOT NULL
) USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {{project_catalog}}.gold.operational_event_materialization (
  event_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  stream_id STRING NOT NULL,
  sequence_number BIGINT NOT NULL,
  event_type STRING NOT NULL,
  payload_json STRING NOT NULL,
  materialized_at TIMESTAMP NOT NULL
) USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {{project_catalog}}.evaluation.stage_run (
  stage_run_id STRING NOT NULL,
  stage_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  input_version STRING,
  output_version STRING,
  attempt INT NOT NULL,
  status STRING NOT NULL,
  row_counts MAP<STRING, BIGINT>,
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  error_code STRING,
  error_message STRING,
  trace_id STRING,
  idempotency_key STRING NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.evaluation.validation_result (
  validation_run_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  validation_name STRING NOT NULL,
  severity STRING NOT NULL,
  expected_value STRING,
  observed_value STRING,
  status STRING NOT NULL,
  details STRING,
  validated_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{project_catalog}}.evaluation.external_verification_candidate (
  candidate_id STRING NOT NULL,
  source_bundle_id STRING NOT NULL,
  facility_id STRING NOT NULL,
  claim_id STRING NOT NULL,
  capability_id STRING NOT NULL,
  candidate_priority DOUBLE NOT NULL,
  verification_reason STRING NOT NULL,
  verification_mode STRING NOT NULL,
  maximum_external_calls INT NOT NULL,
  status STRING NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

-- Read-only source views. They expose the shared source but grant no write path.
CREATE OR REPLACE VIEW {{project_catalog}}.bronze.v_source_facilities_readonly AS
SELECT * FROM {{source_catalog}}.{{source_schema}}.facilities;

CREATE OR REPLACE VIEW {{project_catalog}}.bronze.v_source_india_post_readonly AS
SELECT * FROM {{source_catalog}}.{{source_schema}}.india_post_pincode_directory;

CREATE OR REPLACE VIEW {{project_catalog}}.bronze.v_source_nfhs5_readonly AS
SELECT * FROM {{source_catalog}}.{{source_schema}}.nfhs_5_district_health_indicators;

CREATE OR REPLACE VIEW {{project_catalog}}.gold.v_app_regional_documentary_evidence AS
SELECT
  s.*,
  o.pincode,
  o.latitude AS postal_reference_latitude,
  o.longitude AS postal_reference_longitude,
  o.origin_status
FROM {{project_catalog}}.gold.regional_documentary_evidence_summary s
JOIN {{project_catalog}}.silver.analysis_origin o
  ON s.source_bundle_id = o.source_bundle_id
 AND s.analysis_origin_id = o.analysis_origin_id;

CREATE OR REPLACE VIEW {{project_catalog}}.gold.v_app_facility_documentary_support AS
SELECT
  support.*,
  facility.canonical_name,
  facility.state_normalized,
  facility.city_normalized,
  facility.pincode,
  facility.latitude,
  facility.longitude
FROM {{project_catalog}}.gold.facility_documentary_support support
JOIN {{project_catalog}}.silver.facility_normalized facility
  ON support.source_bundle_id = facility.source_bundle_id
 AND support.facility_id = facility.facility_id;

CREATE OR REPLACE VIEW {{project_catalog}}.gold.v_app_verification_queue AS
SELECT *
FROM {{project_catalog}}.gold.verification_priority
WHERE status IN ('open', 'deferred', 'unresolved');
