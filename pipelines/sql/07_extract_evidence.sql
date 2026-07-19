DELETE FROM {{project_catalog}}.silver.claim_validation
WHERE claim_id IN (
  SELECT claim_id
  FROM {{project_catalog}}.silver.facility_claim
  WHERE source_bundle_id = '{{source_bundle_id}}'
);

DELETE FROM {{project_catalog}}.silver.evidence_span
WHERE claim_id IN (
  SELECT claim_id
  FROM {{project_catalog}}.silver.facility_claim
  WHERE source_bundle_id = '{{source_bundle_id}}'
);

DELETE FROM {{project_catalog}}.silver.extraction_assertion
WHERE claim_id IN (
  SELECT claim_id
  FROM {{project_catalog}}.silver.facility_claim
  WHERE source_bundle_id = '{{source_bundle_id}}'
);

DELETE FROM {{project_catalog}}.silver.source_artifact
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.source_artifact
WITH field_sources AS (
  SELECT
    parse.source_bundle_id,
    parse.facility_id,
    parse.source_row_id,
    parse.field_name,
    parse.raw_value,
    source.source_types_raw,
    source.source_urls_raw
  FROM {{project_catalog}}.silver.facility_field_parse parse
  JOIN {{project_catalog}}.bronze.facility_source_snapshot source
    ON parse.source_bundle_id = source.source_bundle_id
   AND parse.source_row_id = source.source_row_id
  WHERE parse.source_bundle_id = '{{source_bundle_id}}'
    AND parse.field_name IN ('specialties', 'procedure', 'equipment', 'capability')
)
SELECT
  sha2(concat(source_bundle_id, ':', source_row_id, ':', field_name), 256) AS source_artifact_id,
  source_bundle_id,
  facility_id,
  source_row_id,
  field_name AS source_field,
  coalesce(element_at(from_json(source_types_raw, 'ARRAY<STRING>'), 1), 'dataset') AS source_family,
  coalesce(element_at(from_json(source_types_raw, 'ARRAY<STRING>'), 1), 'dataset') AS publisher,
  element_at(from_json(source_urls_raw, 'ARRAY<STRING>'), 1) AS source_url,
  raw_value AS raw_content,
  sha2(coalesce(raw_value, ''), 256) AS content_hash,
  cast(NULL AS TIMESTAMP) AS publication_time,
  cast(NULL AS TIMESTAMP) AS valid_time,
  current_timestamp() AS retrieval_time,
  CASE WHEN raw_value IS NULL THEN 'missing' ELSE 'preserved' END AS artifact_status
FROM field_sources;

DELETE FROM {{project_catalog}}.silver.facility_claim
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.facility_claim
WITH evidence_fields AS (
  SELECT
    artifact.*,
    lower(coalesce(artifact.raw_content, '')) AS searchable_text
  FROM {{project_catalog}}.silver.source_artifact artifact
  WHERE artifact.source_bundle_id = '{{source_bundle_id}}'
),
candidate_claims AS (
  SELECT *, 'maternal_emergency_documentation' AS capability_id, 'ob_gyn_specialty' AS claim_type
  FROM evidence_fields
  WHERE source_field = 'specialties'
    AND searchable_text RLIKE 'gynecologyandobstetrics|obstetric|gynaecolog'
  UNION ALL
  SELECT *, 'maternal_emergency_documentation', 'c_section'
  FROM evidence_fields
  WHERE searchable_text RLIKE 'c[- ]?section|caesarean|cesarean'
  UNION ALL
  SELECT *, 'emergency_surgery_documentation', 'emergency_medicine'
  FROM evidence_fields
  WHERE source_field = 'specialties' AND searchable_text RLIKE 'emergencymedicine|emergency medicine'
  UNION ALL
  SELECT *, 'emergency_surgery_documentation', 'general_surgery'
  FROM evidence_fields
  WHERE source_field = 'specialties' AND searchable_text RLIKE 'generalsurgery|general surgery'
  UNION ALL
  SELECT *, 'advanced_imaging_documentation', 'ct'
  FROM evidence_fields
  WHERE searchable_text RLIKE '(^|[^a-z])(ct|computed tomography)([^a-z]|$)'
  UNION ALL
  SELECT *, 'advanced_imaging_documentation', 'mri'
  FROM evidence_fields
  WHERE searchable_text RLIKE '(^|[^a-z])(mri|magnetic resonance)([^a-z]|$)'
)
SELECT
  sha2(concat(source_artifact_id, ':', capability_id, ':', claim_type), 256) AS claim_id,
  source_bundle_id,
  facility_id,
  capability_id,
  claim_type,
  'positive' AS polarity,
  'explicit_source_field' AS explicitness,
  raw_content AS claim_text,
  source_artifact_id,
  'deterministic_field_pattern' AS extraction_method,
  'documentary-extraction-v1' AS extraction_version,
  'pending_validation' AS claim_status,
  current_timestamp() AS created_at
FROM candidate_claims;

INSERT INTO {{project_catalog}}.silver.evidence_span
SELECT
  sha2(concat(claim.claim_id, ':span:0'), 256) AS evidence_span_id,
  claim.claim_id,
  claim.source_artifact_id,
  artifact.source_field,
  artifact.raw_content AS evidence_text,
  0 AS start_offset,
  length(artifact.raw_content) AS end_offset,
  sha2(artifact.raw_content, 256) AS span_hash,
  'exact_preserved_field' AS citation_status,
  current_timestamp() AS created_at
FROM {{project_catalog}}.silver.facility_claim claim
JOIN {{project_catalog}}.silver.source_artifact artifact
  ON claim.source_artifact_id = artifact.source_artifact_id
WHERE claim.source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.extraction_assertion
SELECT
  sha2(concat(claim_id, ':explicitness'), 256) AS assertion_id,
  claim_id,
  'entity_attribution' AS assertion_type,
  'same_source_row_as_facility' AS assertion_value,
  1.0 AS confidence,
  cast(NULL AS STRING) AS model_name,
  cast(NULL AS STRING) AS prompt_version,
  'documentary-extraction-v1' AS rule_version,
  cast(NULL AS STRING) AS trace_id,
  cast(NULL AS STRING) AS span_id,
  'asserted' AS status,
  current_timestamp() AS created_at
FROM {{project_catalog}}.silver.facility_claim
WHERE source_bundle_id = '{{source_bundle_id}}';

DELETE FROM {{project_catalog}}.gold.facility_evidence_document
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.gold.facility_evidence_document
SELECT
  sha2(concat(claim.source_bundle_id, ':', claim.facility_id, ':', claim.capability_id), 256) AS document_id,
  claim.source_bundle_id,
  claim.facility_id,
  claim.capability_id,
  concat_ws('\n', sort_array(collect_set(span.evidence_text))) AS document_text,
  sort_array(collect_set(span.evidence_span_id)) AS evidence_span_ids,
  sort_array(collect_set(claim.source_artifact_id)) AS source_artifact_ids,
  array_distinct(array(
    concat('state:', coalesce(facility.state_normalized, 'unknown')),
    concat('pin:', coalesce(facility.pincode, 'unknown'))
  )) AS geography_keys,
  max(artifact.retrieval_time) AS freshness_time,
  sha2(concat_ws('|', sort_array(collect_set(span.span_hash))), 256) AS document_hash,
  current_timestamp() AS updated_at
FROM {{project_catalog}}.silver.facility_claim claim
JOIN {{project_catalog}}.silver.evidence_span span ON claim.claim_id = span.claim_id
JOIN {{project_catalog}}.silver.source_artifact artifact ON claim.source_artifact_id = artifact.source_artifact_id
JOIN {{project_catalog}}.silver.facility_normalized facility
  ON claim.source_bundle_id = facility.source_bundle_id
 AND claim.facility_id = facility.facility_id
WHERE claim.source_bundle_id = '{{source_bundle_id}}'
GROUP BY claim.source_bundle_id, claim.facility_id, claim.capability_id, facility.state_normalized, facility.pincode;
