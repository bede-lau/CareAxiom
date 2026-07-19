DELETE FROM {{project_catalog}}.gold.verification_priority
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.gold.verification_priority
WITH affected AS (
  SELECT
    support.source_bundle_id,
    support.facility_id,
    support.capability_id,
    count(DISTINCT edge.analysis_origin_id) AS affected_origin_count,
    max(CASE WHEN support.support_band IN ('claim_only_or_weak', 'partially_supported') THEN 1.0 ELSE 0.25 END) AS flip_potential,
    max(CASE WHEN facility.freshness_status = 'stale' THEN 1.0 WHEN facility.freshness_status = 'unknown' THEN 0.7 ELSE 0.0 END) AS staleness,
    max(CASE WHEN support.contradiction_state = 'confirmed' THEN 1.0 WHEN support.contradiction_state = 'unresolved' THEN 0.7 ELSE 0.0 END) AS contradiction,
    max(CASE WHEN facility.location_conflict_status <> 'none' THEN 1.0 ELSE 0.0 END) AS location_conflict
  FROM {{project_catalog}}.gold.facility_documentary_support support
  JOIN {{project_catalog}}.silver.facility_normalized facility
    ON support.source_bundle_id = facility.source_bundle_id
   AND support.facility_id = facility.facility_id
  LEFT JOIN {{project_catalog}}.gold.analysis_origin_facility_distance edge
    ON support.source_bundle_id = edge.source_bundle_id
   AND support.facility_id = edge.facility_id
  WHERE support.source_bundle_id = '{{source_bundle_id}}'
  GROUP BY support.source_bundle_id, support.facility_id, support.capability_id
),
normalized AS (
  SELECT
    *,
    least(1.0, affected_origin_count / 100.0) AS affected_factor,
    0.0 AS active_scenario_factor,
    greatest(contradiction, location_conflict) AS contradiction_or_location
  FROM affected
)
SELECT
  sha2(concat(source_bundle_id, ':', facility_id, ':', capability_id, ':verification-v1'), 256) AS verification_item_id,
  source_bundle_id,
  facility_id,
  cast(NULL AS STRING) AS claim_id,
  capability_id,
  CASE
    WHEN location_conflict = 1.0 THEN 'Facility coordinates or city conflict with PIN administrative evidence; PIN labels are not treated as geographic truth.'
    WHEN contradiction > 0 THEN 'Unresolved documentary contradiction may change the regional result.'
    WHEN staleness > 0 THEN 'Evidence freshness is unknown or stale.'
    ELSE 'Weak documentary support may change classification after review.'
  END AS reason,
  flip_potential AS classification_flip_potential,
  affected_factor AS affected_origin_or_region_factor,
  active_scenario_factor AS active_scenario_reference_factor,
  staleness AS evidence_staleness,
  contradiction_or_location AS contradiction_severity,
  least(1.0, greatest(0.0,
    0.40 * flip_potential
    + 0.25 * affected_factor
    + 0.20 * active_scenario_factor
    + 0.10 * staleness
    + 0.05 * contradiction_or_location
  )) AS priority_score,
  'affected_analysis_origin_count_without_population_denominator' AS impact_proxy_label,
  'open' AS status,
  concat(lpad(cast(1000000 - cast(least(1.0, greatest(0.0,
    0.40 * flip_potential
    + 0.25 * affected_factor
    + 0.20 * active_scenario_factor
    + 0.10 * staleness
    + 0.05 * contradiction_or_location
  )) * 1000000 AS INT) AS STRING), 7, '0'), ':', facility_id, ':', capability_id) AS deterministic_tiebreaker,
  current_timestamp() AS calculated_at
FROM normalized
WHERE flip_potential > 0 OR staleness > 0 OR contradiction_or_location > 0;

DELETE FROM {{project_catalog}}.gold.planning_priority_candidate
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.gold.planning_priority_candidate
SELECT
  sha2(concat(summary.summary_id, ':planning-priority-v1'), 256) AS candidate_id,
  summary.source_bundle_id,
  summary.analysis_origin_id,
  summary.capability_id,
  summary.radius_km,
  summary.regional_classification AS documentary_classification,
  summary.observed_record_assessability,
  'unavailable_or_separate' AS survey_context_availability,
  cast(NULL AS DOUBLE) AS context_axis_score,
  true AS external_validation_required,
  false AS medical_desert_label_enabled,
  sha2(concat(summary.summary_hash, ':planning-priority-v1'), 256) AS candidate_hash,
  current_timestamp() AS calculated_at
FROM {{project_catalog}}.gold.regional_documentary_evidence_summary summary
WHERE summary.source_bundle_id = '{{source_bundle_id}}'
  AND summary.regional_classification = 'low_nearby_documentary_support'
  AND summary.observed_record_assessability >= 0.65;

SELECT assert_true(
  COUNT_IF(medical_desert_label_enabled) = 0,
  'Medical-desert candidate label is disabled without population and operational inputs'
)
FROM {{project_catalog}}.gold.planning_priority_candidate
WHERE source_bundle_id = '{{source_bundle_id}}';
