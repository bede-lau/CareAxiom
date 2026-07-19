DELETE FROM {{project_catalog}}.silver.district_identity_crosswalk
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.district_identity_crosswalk
WITH nfhs AS (
  SELECT DISTINCT
    source_bundle_id,
    state_raw,
    district_raw,
    trim(regexp_replace(lower(state_raw), '[^a-z0-9]+', ' ')) AS normalized_state,
    trim(regexp_replace(lower(district_raw), '[^a-z0-9]+', ' ')) AS normalized_district
  FROM {{project_catalog}}.bronze.nfhs5_district_snapshot
  WHERE source_bundle_id = '{{source_bundle_id}}'
),
postal_districts AS (
  SELECT DISTINCT
    source_bundle_id,
    element_at(state_candidates, 1) AS normalized_state,
    element_at(district_candidates, 1) AS normalized_district
  FROM {{project_catalog}}.silver.pin_postal_reference
  WHERE source_bundle_id = '{{source_bundle_id}}'
    AND geography_status = 'unambiguous_label_evidence'
),
postal AS (
  SELECT
    source_bundle_id,
    pincode,
    element_at(state_candidates, 1) AS state_raw,
    element_at(district_candidates, 1) AS district_raw,
    geography_status
  FROM {{project_catalog}}.silver.pin_postal_reference
  WHERE source_bundle_id = '{{source_bundle_id}}'
)
SELECT
  sha2(concat('nfhs5:', nfhs.normalized_state, ':', nfhs.normalized_district, ':{{geography_version}}'), 256) AS crosswalk_id,
  nfhs.source_bundle_id,
  'nfhs5' AS source_system,
  nfhs.state_raw AS source_state,
  nfhs.district_raw AS source_district,
  nfhs.normalized_state,
  nfhs.normalized_district,
  CASE WHEN postal_districts.normalized_district IS NOT NULL THEN nfhs.normalized_state ELSE NULL END AS canonical_state,
  CASE WHEN postal_districts.normalized_district IS NOT NULL THEN nfhs.normalized_district ELSE NULL END AS canonical_district,
  CASE
    WHEN postal_districts.normalized_district IS NOT NULL THEN 'matched_exact_normalized'
    ELSE 'unmatched'
  END AS match_status,
  CASE
    WHEN postal_districts.normalized_district IS NOT NULL THEN 'exact_normalized_postal_label_evidence'
    ELSE 'no_exact_postal_label_evidence_reviewed_alias_required'
  END AS match_reason,
  CASE
    WHEN postal_districts.normalized_district IS NOT NULL THEN 'auto_exact'
    ELSE 'review_required'
  END AS review_status,
  '{{geography_version}}' AS crosswalk_version,
  current_timestamp() AS created_at
FROM nfhs
LEFT JOIN postal_districts
  ON nfhs.source_bundle_id = postal_districts.source_bundle_id
 AND nfhs.normalized_state = postal_districts.normalized_state
 AND nfhs.normalized_district = postal_districts.normalized_district
UNION ALL
SELECT
  sha2(concat('postal:', pincode, ':{{geography_version}}'), 256),
  source_bundle_id,
  'india_post',
  coalesce(state_raw, ''),
  coalesce(district_raw, ''),
  coalesce(state_raw, ''),
  coalesce(district_raw, ''),
  CASE WHEN geography_status = 'unambiguous_label_evidence' THEN state_raw ELSE NULL END,
  CASE WHEN geography_status = 'unambiguous_label_evidence' THEN district_raw ELSE NULL END,
  CASE
    WHEN geography_status = 'unambiguous_label_evidence' THEN 'matched_label_evidence'
    WHEN geography_status = 'ambiguous_label_evidence' THEN 'ambiguous'
    ELSE 'unmatched'
  END,
  CASE
    WHEN geography_status = 'unambiguous_label_evidence' THEN 'single_postal_label_candidate'
    WHEN geography_status = 'ambiguous_label_evidence' THEN 'multiple_postal_label_candidates'
    ELSE 'postal_label_unavailable'
  END,
  CASE WHEN geography_status = 'unambiguous_label_evidence' THEN 'unreviewed_evidence' ELSE 'review_required' END,
  '{{geography_version}}',
  current_timestamp()
FROM postal;

MERGE INTO {{project_catalog}}.silver.facility_normalized target
USING (
  WITH known_districts AS (
    SELECT DISTINCT
      source_bundle_id,
      element_at(state_candidates, 1) AS normalized_state,
      element_at(district_candidates, 1) AS normalized_district
    FROM {{project_catalog}}.silver.pin_postal_reference
    WHERE source_bundle_id = '{{source_bundle_id}}'
      AND geography_status = 'unambiguous_label_evidence'
  )
  SELECT
    facility.source_bundle_id,
    facility.facility_id,
    reference.geography_status,
    CASE
      WHEN facility.city_normalized IS NOT NULL
       AND known_city_district.normalized_district IS NOT NULL
       AND NOT array_contains(reference.district_candidates, facility.city_normalized)
      THEN true
      ELSE false
    END AS city_label_conflict,
    CASE
      WHEN facility.coordinate_status = 'valid_broad_envelope'
       AND reference.reference_status = 'available'
      THEN 6371.0088 * 2 * asin(sqrt(
        pow(sin(radians(reference.postal_reference_latitude - facility.latitude) / 2), 2)
        + cos(radians(facility.latitude)) * cos(radians(reference.postal_reference_latitude))
        * pow(sin(radians(reference.postal_reference_longitude - facility.longitude) / 2), 2)
      ))
      ELSE NULL
    END AS distance_km
  FROM {{project_catalog}}.silver.facility_normalized facility
  LEFT JOIN {{project_catalog}}.silver.pin_postal_reference reference
    ON facility.source_bundle_id = reference.source_bundle_id
   AND facility.pincode = reference.pincode
  LEFT JOIN known_districts known_city_district
    ON facility.source_bundle_id = known_city_district.source_bundle_id
   AND facility.state_normalized = known_city_district.normalized_state
   AND facility.city_normalized = known_city_district.normalized_district
  WHERE facility.source_bundle_id = '{{source_bundle_id}}'
) source
ON target.source_bundle_id = source.source_bundle_id
AND target.facility_id = source.facility_id
WHEN MATCHED THEN UPDATE SET
  target.pin_reference_distance_km = source.distance_km,
  target.location_conflict_status = CASE
    WHEN target.pincode IS NULL THEN 'invalid_or_missing_pin'
    WHEN source.geography_status IS NULL THEN 'pin_not_in_directory'
    WHEN source.geography_status <> 'unambiguous_label_evidence' THEN 'ambiguous_pin_administrative_evidence'
    WHEN source.city_label_conflict THEN 'city_pin_district_label_conflict'
    WHEN source.distance_km > 75 THEN 'coordinate_pin_reference_conflict'
    WHEN target.coordinate_status <> 'valid_broad_envelope' THEN 'facility_coordinate_unavailable'
    ELSE 'none'
  END,
  target.regional_aggregation_eligible = CASE
    WHEN target.pincode IS NOT NULL
     AND source.geography_status = 'unambiguous_label_evidence'
     AND NOT source.city_label_conflict
     AND target.coordinate_status = 'valid_broad_envelope'
     AND source.distance_km <= 75 THEN true
    ELSE false
  END;

DELETE FROM {{project_catalog}}.silver.facility_quality_signal
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND signal_type IN (
    'location_conflict',
    'pin_coordinate_city_conflict',
    'pin_coordinate_conflict',
    'postal_geography_review_required'
  );

INSERT INTO {{project_catalog}}.silver.facility_quality_signal
SELECT
  sha2(concat(source_bundle_id, ':', facility_id, ':location_conflict:{{geography_version}}'), 256),
  source_bundle_id,
  facility_id,
  CASE
    WHEN location_conflict_status = 'city_pin_district_label_conflict'
      THEN 'pin_coordinate_city_conflict'
    WHEN location_conflict_status = 'coordinate_pin_reference_conflict'
      THEN 'pin_coordinate_conflict'
    ELSE 'postal_geography_review_required'
  END,
  CASE
    WHEN location_conflict_status = 'coordinate_pin_reference_conflict'
      THEN least(1.0, coalesce(pin_reference_distance_km, 75.0) / 500.0)
    ELSE 1.0
  END,
  'needs_review',
  to_json(named_struct(
    'status', location_conflict_status,
    'pincode', pincode,
    'city_raw', city_raw,
    'city_normalized', city_normalized,
    'state_raw', state_raw,
    'pin_reference_distance_km', pin_reference_distance_km,
    'postal_label_semantics', 'evidence_not_geographic_truth',
    'aggregate_eligible', regional_aggregation_eligible
  )),
  '{{geography_version}}',
  current_timestamp()
FROM {{project_catalog}}.silver.facility_normalized
WHERE source_bundle_id = '{{source_bundle_id}}'
  AND location_conflict_status <> 'none';

DELETE FROM {{project_catalog}}.silver.district_survey_context
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.district_survey_context
SELECT
  observation.source_bundle_id,
  sha2(concat(observation.normalized_state, ':', observation.normalized_district), 256) AS district_context_id,
  observation.normalized_state,
  observation.normalized_district,
  crosswalk.crosswalk_id,
  CASE
    WHEN crosswalk.match_status = 'matched_exact_normalized' THEN 'matched'
    ELSE 'unavailable'
  END AS survey_context_availability,
  count_if(observation.parse_status = 'parsed') AS matched_observation_count,
  count_if(observation.parse_status <> 'parsed') AS unavailable_observation_count,
  to_json(
    map_from_entries(
      collect_list(
        named_struct(
          'key', observation.indicator_id,
          'value', to_json(named_struct(
            'raw_value', observation.raw_value,
            'numeric_value', observation.numeric_value,
            'qualifier', observation.qualifier,
            'parse_status', observation.parse_status
          ))
        )
      )
    )
  ) AS context_payload,
  max(observation.source_version) AS source_version,
  current_timestamp() AS created_at
FROM {{project_catalog}}.silver.nfhs_indicator_observation observation
LEFT JOIN {{project_catalog}}.silver.district_identity_crosswalk crosswalk
  ON observation.source_bundle_id = crosswalk.source_bundle_id
 AND crosswalk.source_system = 'nfhs5'
 AND observation.normalized_state = crosswalk.normalized_state
 AND observation.normalized_district = crosswalk.normalized_district
WHERE observation.source_bundle_id = '{{source_bundle_id}}'
GROUP BY
  observation.source_bundle_id,
  observation.normalized_state,
  observation.normalized_district,
  crosswalk.crosswalk_id,
  crosswalk.match_status;
