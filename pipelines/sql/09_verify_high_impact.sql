DELETE FROM {{project_catalog}}.evaluation.external_verification_candidate
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.evaluation.external_verification_candidate
WITH claim_risk AS (
  SELECT
    claim.source_bundle_id,
    claim.facility_id,
    claim.claim_id,
    claim.capability_id,
    max(CASE WHEN validation.severity = 'high' THEN 1.0 WHEN validation.severity = 'warning' THEN 0.5 ELSE 0.0 END) AS validation_risk,
    max(CASE WHEN facility.freshness_status IN ('unknown', 'stale') THEN 1.0 ELSE 0.0 END) AS freshness_risk,
    max(CASE WHEN facility.location_conflict_status <> 'none' THEN 1.0 ELSE 0.0 END) AS location_risk
  FROM {{project_catalog}}.silver.facility_claim claim
  JOIN {{project_catalog}}.silver.claim_validation validation ON claim.claim_id = validation.claim_id
  JOIN {{project_catalog}}.silver.facility_normalized facility
    ON claim.source_bundle_id = facility.source_bundle_id
   AND claim.facility_id = facility.facility_id
  WHERE claim.source_bundle_id = '{{source_bundle_id}}'
  GROUP BY claim.source_bundle_id, claim.facility_id, claim.claim_id, claim.capability_id
)
SELECT
  sha2(concat(claim_id, ':external-verification-v1'), 256) AS candidate_id,
  source_bundle_id,
  facility_id,
  claim_id,
  capability_id,
  least(1.0, 0.5 * validation_risk + 0.3 * freshness_risk + 0.2 * location_risk) AS candidate_priority,
  CASE
    WHEN location_risk = 1.0 THEN 'location_conflict'
    WHEN validation_risk > 0 THEN 'validator_finding'
    ELSE 'freshness_unknown'
  END AS verification_reason,
  'cached_or_manual' AS verification_mode,
  2 AS maximum_external_calls,
  'queued' AS status,
  current_timestamp() AS created_at
FROM claim_risk
WHERE validation_risk > 0 OR freshness_risk > 0 OR location_risk > 0;
