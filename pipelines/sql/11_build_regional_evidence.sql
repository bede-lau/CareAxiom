DELETE FROM {{project_catalog}}.gold.analysis_origin_facility_distance
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.gold.analysis_origin_facility_distance
WITH candidate_edges AS (
  SELECT
    origin.source_bundle_id,
    origin.analysis_origin_id,
    facility.facility_id,
    6371.0088 * 2 * asin(sqrt(
      pow(sin(radians(facility.latitude - origin.latitude) / 2), 2)
      + cos(radians(origin.latitude)) * cos(radians(facility.latitude))
      * pow(sin(radians(facility.longitude - origin.longitude) / 2), 2)
    )) AS distance_km
  FROM {{project_catalog}}.silver.analysis_origin origin
  JOIN {{project_catalog}}.silver.facility_normalized facility
    ON origin.source_bundle_id = facility.source_bundle_id
   AND facility.regional_aggregation_eligible
   AND facility.latitude BETWEEN origin.latitude - 0.75 AND origin.latitude + 0.75
   AND facility.longitude BETWEEN origin.longitude - 0.75 AND origin.longitude + 0.75
  WHERE origin.source_bundle_id = '{{source_bundle_id}}'
    AND origin.origin_status = 'mappable'
)
SELECT
  source_bundle_id,
  analysis_origin_id,
  facility_id,
  distance_km,
  50 AS maximum_radius_km,
  '{{geography_version}}' AS geography_version,
  sha2(concat(source_bundle_id, ':', analysis_origin_id, ':', facility_id, ':', cast(round(distance_km, 6) AS STRING), ':{{geography_version}}'), 256) AS edge_hash,
  current_timestamp() AS calculated_at
FROM candidate_edges
WHERE distance_km <= 50;

DELETE FROM {{project_catalog}}.gold.regional_documentary_evidence_summary
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.gold.regional_documentary_evidence_summary
WITH capabilities AS (
  SELECT explode(array(
    'maternal_emergency_documentation',
    'emergency_surgery_documentation',
    'advanced_imaging_documentation'
  )) AS capability_id
),
radii AS (
  SELECT explode(array(10, 25, 50)) AS radius_km
),
origin_grid AS (
  SELECT origin.*, capability.capability_id, radii.radius_km
  FROM {{project_catalog}}.silver.analysis_origin origin
  CROSS JOIN capabilities capability
  CROSS JOIN radii
  WHERE origin.source_bundle_id = '{{source_bundle_id}}'
),
regional AS (
  SELECT
    grid.source_bundle_id,
    grid.analysis_origin_id,
    grid.capability_id,
    grid.radius_km,
    max(grid.origin_status) AS origin_status,
    count(DISTINCT edge.facility_id) AS n_region_entities,
    count(DISTINCT support.facility_id) AS n_capability_assessed_entities,
    count(DISTINCT CASE WHEN support.support_band = 'strongly_supported' THEN support.facility_id END) AS strong_support_count,
    count(DISTINCT CASE WHEN support.support_band = 'partially_supported' THEN support.facility_id END) AS partial_support_count,
    count(DISTINCT CASE WHEN support.support_band = 'claim_only_or_weak' THEN support.facility_id END) AS weak_support_count,
    count(DISTINCT CASE WHEN support.contradiction_state <> 'none' THEN support.facility_id END) AS contradiction_count,
    sort_array(collect_set(edge.facility_id)) AS contributing_facility_ids
  FROM origin_grid grid
  LEFT JOIN {{project_catalog}}.gold.analysis_origin_facility_distance edge
    ON grid.source_bundle_id = edge.source_bundle_id
   AND grid.analysis_origin_id = edge.analysis_origin_id
   AND edge.distance_km <= grid.radius_km
  LEFT JOIN {{project_catalog}}.gold.facility_documentary_support support
    ON edge.source_bundle_id = support.source_bundle_id
   AND edge.facility_id = support.facility_id
   AND grid.capability_id = support.capability_id
  GROUP BY grid.source_bundle_id, grid.analysis_origin_id, grid.capability_id, grid.radius_km
),
global_counts AS (
  SELECT
    (SELECT COUNT(*) FROM {{project_catalog}}.bronze.facility_source_snapshot WHERE source_bundle_id = '{{source_bundle_id}}') AS n_source_rows,
    (SELECT COUNT(*) FROM {{project_catalog}}.silver.facility_row_integrity WHERE source_bundle_id = '{{source_bundle_id}}' AND disposition <> 'quarantined') AS n_structurally_eligible_rows,
    (SELECT COUNT(*) FROM {{project_catalog}}.silver.facility_entity WHERE source_bundle_id = '{{source_bundle_id}}') AS n_canonical_facility_entities
),
scored AS (
  SELECT
    regional.*,
    global_counts.*,
    CASE
      WHEN regional.origin_status = 'unavailable' THEN cast(NULL AS DOUBLE)
      WHEN regional.n_region_entities = 0 THEN 0.0
      ELSE least(1.0, greatest(0.0,
        0.15 * (global_counts.n_structurally_eligible_rows / global_counts.n_source_rows)
        + 0.25
        + 0.20
        + 0.20 * (regional.n_capability_assessed_entities / regional.n_region_entities)
        + 0.10
        + 0.10 * 0.3535
        - 0.15 * (regional.contradiction_count / regional.n_region_entities)
      ))
    END AS observed_record_assessability
  FROM regional
  CROSS JOIN global_counts
)
SELECT
  sha2(concat(source_bundle_id, ':', analysis_origin_id, ':', capability_id, ':', radius_km, ':{{policy_version}}:{{geography_version}}'), 256) AS summary_id,
  source_bundle_id,
  analysis_origin_id,
  capability_id,
  radius_km,
  CASE
    WHEN origin_status = 'unavailable' THEN 'unavailable_analysis'
    WHEN n_region_entities = 0 THEN 'insufficient_corpus_evidence'
    WHEN observed_record_assessability < 0.65 THEN 'insufficient_corpus_evidence'
    WHEN contradiction_count > 0 THEN 'mixed_signal_verification_required'
    WHEN strong_support_count + partial_support_count > 0 THEN 'strong_nearby_documentary_support'
    ELSE 'low_nearby_documentary_support'
  END AS regional_classification,
  observed_record_assessability,
  n_source_rows,
  n_structurally_eligible_rows,
  n_canonical_facility_entities,
  n_region_entities,
  n_capability_assessed_entities,
  strong_support_count,
  partial_support_count,
  weak_support_count,
  contradiction_count,
  n_region_entities - n_capability_assessed_entities AS excluded_count,
  coalesce(contributing_facility_ids, array()) AS contributing_facility_ids,
  CASE
    WHEN origin_status = 'unavailable' THEN array('analysis_origin_unavailable')
    WHEN n_region_entities = 0 THEN array('no_observed_records_within_radius')
    WHEN observed_record_assessability < 0.65 THEN array('assessability_below_policy_threshold')
    ELSE array()
  END AS exclusion_reasons,
  '{{policy_version}}' AS policy_version,
  '{{geography_version}}' AS geography_version,
  sha2(concat_ws('|',
    analysis_origin_id,
    capability_id,
    cast(radius_km AS STRING),
    cast(n_region_entities AS STRING),
    cast(n_capability_assessed_entities AS STRING),
    concat_ws(',', coalesce(contributing_facility_ids, array())),
    '{{policy_version}}',
    '{{geography_version}}'
  ), 256) AS summary_hash,
  current_timestamp() AS calculated_at
FROM scored;

DELETE FROM {{project_catalog}}.gold.district_context_profile
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.gold.district_context_profile
SELECT
  district_context_id AS district_profile_id,
  source_bundle_id,
  normalized_state,
  normalized_district,
  survey_context_availability,
  context_payload,
  source_version,
  sha2(concat(normalized_state, ':', normalized_district, ':', context_payload, ':', source_version), 256) AS profile_hash,
  current_timestamp() AS calculated_at
FROM {{project_catalog}}.silver.district_survey_context
WHERE source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(COUNT_IF(distance_km > 50) = 0, 'Distance edge exceeds maximum radius')
FROM {{project_catalog}}.gold.analysis_origin_facility_distance
WHERE source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(
  COUNT_IF(
    n_region_entities = 0
    AND regional_classification NOT IN ('insufficient_corpus_evidence', 'unavailable_analysis')
  ) = 0,
  'Zero-record origins must remain insufficient corpus evidence or explicitly unavailable'
)
FROM {{project_catalog}}.gold.regional_documentary_evidence_summary
WHERE source_bundle_id = '{{source_bundle_id}}';
