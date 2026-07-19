-- Each query returns zero rows on success unless explicitly labeled as a metric.

-- Source conservation.
SELECT 'facility_source_count' AS validation_name, COUNT(*) AS observed, 10088 AS expected
FROM {{project_catalog}}.bronze.facility_source_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}'
HAVING observed <> expected;

SELECT 'postal_source_count' AS validation_name, COUNT(*) AS observed, 165627 AS expected
FROM {{project_catalog}}.bronze.india_post_office_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}'
HAVING observed <> expected;

SELECT 'nfhs_source_count' AS validation_name, COUNT(*) AS observed, 706 AS expected
FROM {{project_catalog}}.bronze.nfhs5_district_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}'
HAVING observed <> expected;

-- Facility disposition and entity integrity.
SELECT disposition, COUNT(*) AS row_count
FROM {{project_catalog}}.silver.facility_row_integrity
WHERE source_bundle_id = '{{source_bundle_id}}'
GROUP BY disposition;

SELECT 'facility_disposition_total' AS validation_name, COUNT(*) AS observed, 10088 AS expected
FROM {{project_catalog}}.silver.facility_row_integrity
WHERE source_bundle_id = '{{source_bundle_id}}'
HAVING observed <> expected;

SELECT 'facility_quarantine_count' AS validation_name, COUNT(*) AS observed, 88 AS expected
FROM {{project_catalog}}.silver.facility_row_integrity
WHERE source_bundle_id = '{{source_bundle_id}}' AND disposition = 'quarantined'
HAVING observed <> expected;

SELECT 'facility_exact_duplicate_count' AS validation_name, COUNT(*) AS observed, 11 AS expected
FROM {{project_catalog}}.silver.facility_row_integrity
WHERE source_bundle_id = '{{source_bundle_id}}' AND disposition = 'exact_duplicate'
HAVING observed <> expected;

SELECT canonical_facility_id, COUNT(DISTINCT raw_hash) AS distinct_raw_hashes
FROM {{project_catalog}}.silver.facility_row_integrity
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND canonical_facility_id IS NOT NULL
GROUP BY canonical_facility_id
HAVING distinct_raw_hashes > 1
   AND COUNT_IF(disposition <> 'quarantined') > 0;

SELECT 'canonical_facility_count' AS validation_name, COUNT(*) AS observed, 9989 AS expected
FROM {{project_catalog}}.silver.facility_entity
WHERE source_bundle_id = '{{source_bundle_id}}'
HAVING observed <> expected;

SELECT facility_id, COUNT(*) AS duplicate_count
FROM {{project_catalog}}.silver.facility_entity
WHERE source_bundle_id = '{{source_bundle_id}}'
GROUP BY facility_id
HAVING duplicate_count > 1;

SELECT integrity.source_row_id
FROM {{project_catalog}}.silver.facility_row_integrity integrity
JOIN {{project_catalog}}.silver.facility_claim claim
  ON integrity.source_bundle_id = claim.source_bundle_id
 AND integrity.canonical_facility_id = claim.facility_id
WHERE integrity.source_bundle_id = '{{source_bundle_id}}'
  AND integrity.disposition = 'quarantined';

-- Parse failures remain distinguishable from empty arrays.
SELECT facility_id, field_name, raw_value
FROM {{project_catalog}}.silver.facility_field_parse
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND parse_status = 'unparseable'
  AND parsed_values IS NOT NULL;

-- Postal coordinate categories and independent origins.
SELECT coordinate_status, COUNT(*) AS row_count
FROM {{project_catalog}}.silver.postal_office_normalized
WHERE source_bundle_id = '{{source_bundle_id}}'
GROUP BY coordinate_status;

SELECT 'postal_normalized_count' AS validation_name, COUNT(*) AS observed, 165627 AS expected
FROM {{project_catalog}}.silver.postal_office_normalized
WHERE source_bundle_id = '{{source_bundle_id}}'
HAVING observed <> expected;

SELECT 'analysis_origin_count' AS validation_name, COUNT(*) AS observed, 19586 AS expected
FROM {{project_catalog}}.silver.analysis_origin
WHERE source_bundle_id = '{{source_bundle_id}}'
HAVING observed <> expected;

SELECT 'mappable_origin_count' AS validation_name, COUNT(*) AS observed, 19550 AS expected
FROM {{project_catalog}}.silver.analysis_origin
WHERE source_bundle_id = '{{source_bundle_id}}' AND origin_status = 'mappable'
HAVING observed <> expected;

SELECT 'unavailable_origin_count' AS validation_name, COUNT(*) AS observed, 36 AS expected
FROM {{project_catalog}}.silver.analysis_origin
WHERE source_bundle_id = '{{source_bundle_id}}' AND origin_status = 'unavailable'
HAVING observed <> expected;

SELECT pincode, COUNT(*) AS duplicate_count
FROM {{project_catalog}}.silver.pin_postal_reference
WHERE source_bundle_id = '{{source_bundle_id}}'
GROUP BY pincode
HAVING duplicate_count > 1;

-- PIN labels are evidence, not truth: material conflicts remain visible and excluded.
SELECT facility_id, pincode, pin_reference_distance_km, location_conflict_status
FROM {{project_catalog}}.silver.facility_normalized
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND location_conflict_status <> 'none'
  AND regional_aggregation_eligible = true;

SELECT facility_id, signal_type, details
FROM {{project_catalog}}.silver.facility_quality_signal
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND signal_type = 'pin_coordinate_city_conflict';

-- No edge may exceed the maximum radius and no office multiplicity may duplicate an edge.
SELECT *
FROM {{project_catalog}}.gold.analysis_origin_facility_distance
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND distance_km > maximum_radius_km;

SELECT analysis_origin_id, facility_id, COUNT(*) AS duplicate_count
FROM {{project_catalog}}.gold.analysis_origin_facility_distance
WHERE source_bundle_id = '{{source_bundle_id}}'
GROUP BY analysis_origin_id, facility_id
HAVING duplicate_count > 1;

-- NFHS accounting and isolation.
SELECT 'nfhs_crosswalk_accounting' AS validation_name, COUNT(*) AS observed, 706 AS expected
FROM {{project_catalog}}.silver.district_identity_crosswalk
WHERE source_bundle_id = '{{source_bundle_id}}' AND source_system = 'nfhs5'
HAVING observed <> expected;

SELECT *
FROM {{project_catalog}}.silver.nfhs_indicator_observation
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND qualifier = 'suppressed_lt_25'
  AND numeric_value IS NOT NULL;

SELECT *
FROM {{project_catalog}}.silver.nfhs_indicator_observation
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND parse_status IN ('missing', 'unparseable')
  AND numeric_value = 0;

-- Facility support has no survey fields and must be reproducible from facility evidence only.
SELECT support.result_id
FROM {{project_catalog}}.gold.facility_documentary_support support
LEFT ANTI JOIN (
  SELECT DISTINCT claim.facility_id, claim.capability_id
  FROM {{project_catalog}}.silver.facility_claim claim
  JOIN {{project_catalog}}.silver.claim_validation validation
    ON claim.claim_id = validation.claim_id
  WHERE claim.source_bundle_id = '{{source_bundle_id}}'
    AND validation.validation_status IN ('passed', 'warning')
) evidence
ON support.facility_id = evidence.facility_id
AND support.capability_id = evidence.capability_id
WHERE support.source_bundle_id = '{{source_bundle_id}}'
  AND support.documentary_support_index IS NOT NULL;

-- Zero-nearby origins remain present and cannot be labeled low support.
SELECT *
FROM {{project_catalog}}.gold.regional_documentary_evidence_summary
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND n_region_entities = 0
  AND regional_classification NOT IN ('insufficient_corpus_evidence', 'unavailable_analysis');

-- Planning candidates cannot enable the medical-desert label with the current contract.
SELECT *
FROM {{project_catalog}}.gold.planning_priority_candidate
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND medical_desert_label_enabled = true;

-- Deterministic queue formula.
SELECT verification_item_id, priority_score, expected_score
FROM (
  SELECT
    verification_item_id,
    priority_score,
    LEAST(1.0, GREATEST(0.0,
      0.40 * classification_flip_potential
      + 0.25 * affected_origin_or_region_factor
      + 0.20 * active_scenario_reference_factor
      + 0.10 * evidence_staleness
      + 0.05 * contradiction_severity
    )) AS expected_score
  FROM {{project_catalog}}.gold.verification_priority
  WHERE source_bundle_id = '{{source_bundle_id}}'
)
WHERE ABS(priority_score - expected_score) > 0.000001;

-- Operational materialization remains idempotent.
SELECT event_id, COUNT(*) AS duplicate_count
FROM {{project_catalog}}.gold.operational_event_materialization
WHERE source_bundle_id = '{{source_bundle_id}}'
GROUP BY event_id
HAVING duplicate_count > 1;

SELECT review_id, COUNT(*) AS duplicate_count
FROM {{project_catalog}}.gold.facility_review_overlay
WHERE source_bundle_id = '{{source_bundle_id}}'
GROUP BY review_id
HAVING duplicate_count > 1;
