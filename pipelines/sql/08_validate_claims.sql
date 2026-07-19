DELETE FROM {{project_catalog}}.silver.claim_validation
WHERE claim_id IN (
  SELECT claim_id
  FROM {{project_catalog}}.silver.facility_claim
  WHERE source_bundle_id = '{{source_bundle_id}}'
);

INSERT INTO {{project_catalog}}.silver.claim_validation
WITH claim_context AS (
  SELECT
    claim.*,
    artifact.source_family,
    artifact.source_field,
    artifact.raw_content,
    facility.location_conflict_status,
    parse.parse_status
  FROM {{project_catalog}}.silver.facility_claim claim
  JOIN {{project_catalog}}.silver.source_artifact artifact
    ON claim.source_artifact_id = artifact.source_artifact_id
  JOIN {{project_catalog}}.silver.facility_normalized facility
    ON claim.source_bundle_id = facility.source_bundle_id
   AND claim.facility_id = facility.facility_id
  LEFT JOIN {{project_catalog}}.silver.facility_field_parse parse
    ON claim.source_bundle_id = parse.source_bundle_id
   AND claim.facility_id = parse.facility_id
   AND artifact.source_field = parse.field_name
  WHERE claim.source_bundle_id = '{{source_bundle_id}}'
)
SELECT
  sha2(concat(claim_id, ':deterministic-validator-v1'), 256) AS validation_id,
  claim_id,
  'deterministic_claim_validator' AS validator_name,
  'validator-v1' AS validator_version,
  CASE
    WHEN parse_status = 'unparseable' THEN 'failed'
    WHEN raw_content IS NULL OR trim(raw_content) = '' THEN 'failed'
    ELSE 'passed'
  END AS validation_status,
  CASE
    WHEN parse_status = 'unparseable' OR raw_content IS NULL OR trim(raw_content) = '' THEN 'high'
    WHEN location_conflict_status <> 'none' THEN 'warning'
    ELSE 'info'
  END AS severity,
  CASE
    WHEN parse_status = 'unparseable' THEN 'malformed_source_field'
    WHEN raw_content IS NULL OR trim(raw_content) = '' THEN 'missing_evidence_text'
    WHEN location_conflict_status <> 'none' THEN 'location_conflict_separate_from_claim'
    ELSE NULL
  END AS finding_code,
  CASE
    WHEN location_conflict_status <> 'none'
      THEN 'Capability evidence is retained, but this facility is excluded from regional geography until location review.'
    ELSE NULL
  END AS finding_details,
  CASE WHEN parse_status = 'unparseable' THEN 0.0 ELSE 100.0 END AS support_cap,
  parse_status = 'unparseable' OR raw_content IS NULL OR trim(raw_content) = '' AS abstain,
  current_timestamp() AS validated_at,
  cast(NULL AS STRING) AS trace_id
FROM claim_context;

UPDATE {{project_catalog}}.silver.facility_claim claim
SET claim_status = CASE
  WHEN EXISTS (
    SELECT 1
    FROM {{project_catalog}}.silver.claim_validation validation
    WHERE validation.claim_id = claim.claim_id
      AND validation.validation_status = 'failed'
  ) THEN 'rejected'
  ELSE 'validated'
END
WHERE source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(
  COUNT_IF(claim_status = 'pending_validation') = 0,
  'All claims must be validated before publication'
)
FROM {{project_catalog}}.silver.facility_claim
WHERE source_bundle_id = '{{source_bundle_id}}';
