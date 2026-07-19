DELETE FROM {{project_catalog}}.silver.postal_office_normalized
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.postal_office_normalized
WITH parsed AS (
  SELECT
    *,
    try_cast(trim(latitude_raw) AS DOUBLE) AS latitude_value,
    try_cast(trim(longitude_raw) AS DOUBLE) AS longitude_value
  FROM {{project_catalog}}.bronze.india_post_office_snapshot
  WHERE source_bundle_id = '{{source_bundle_id}}'
)
SELECT
  source_bundle_id,
  source_row_id,
  CASE WHEN pincode RLIKE '^[0-9]{6}$' THEN pincode ELSE NULL END AS pincode,
  officename AS office_name,
  statename AS state_raw,
  nullif(trim(regexp_replace(lower(statename), '[^a-z0-9]+', ' ')), '') AS state_normalized,
  district AS district_raw,
  nullif(trim(regexp_replace(lower(district), '[^a-z0-9]+', ' ')), '') AS district_normalized,
  CASE
    WHEN latitude_value BETWEEN 6.5 AND 39
     AND longitude_value BETWEEN 68 AND 98
     AND NOT (latitude_value = 0 OR longitude_value = 0) THEN latitude_value
    ELSE NULL
  END AS latitude,
  CASE
    WHEN latitude_value BETWEEN 6.5 AND 39
     AND longitude_value BETWEEN 68 AND 98
     AND NOT (latitude_value = 0 OR longitude_value = 0) THEN longitude_value
    ELSE NULL
  END AS longitude,
  CASE
    WHEN latitude_value IS NULL OR longitude_value IS NULL THEN 'unparseable_or_missing'
    WHEN latitude_value = 0 OR longitude_value = 0 THEN 'zero_coordinate'
    WHEN latitude_value BETWEEN 6.5 AND 39 AND longitude_value BETWEEN 68 AND 98 THEN 'valid_broad_envelope'
    ELSE 'numeric_outside_broad_envelope'
  END AS coordinate_status,
  source_duplicate_ordinal > 1 AS exact_duplicate,
  current_timestamp() AS normalized_at
FROM parsed;

DELETE FROM {{project_catalog}}.silver.pin_postal_reference
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.pin_postal_reference
WITH pins AS (
  SELECT DISTINCT pincode
  FROM {{project_catalog}}.bronze.india_post_office_snapshot
  WHERE source_bundle_id = '{{source_bundle_id}}' AND pincode RLIKE '^[0-9]{6}$'
),
aggregated AS (
  SELECT
    pincode,
    percentile_approx(latitude, 0.5, 10000) AS latitude_median,
    percentile_approx(longitude, 0.5, 10000) AS longitude_median,
    count(*) AS office_count,
    count(latitude) AS valid_coordinate_count,
    max(latitude) - min(latitude) + max(longitude) - min(longitude) AS coordinate_dispersion_degrees,
    sort_array(array_distinct(filter(collect_list(state_normalized), value -> value IS NOT NULL))) AS state_candidates,
    sort_array(array_distinct(filter(collect_list(district_normalized), value -> value IS NOT NULL))) AS district_candidates
  FROM {{project_catalog}}.silver.postal_office_normalized
  WHERE source_bundle_id = '{{source_bundle_id}}' AND NOT exact_duplicate
  GROUP BY pincode
)
SELECT
  '{{source_bundle_id}}' AS source_bundle_id,
  pins.pincode,
  aggregated.latitude_median AS postal_reference_latitude,
  aggregated.longitude_median AS postal_reference_longitude,
  CASE WHEN aggregated.valid_coordinate_count > 0 THEN 'available' ELSE 'unavailable' END AS reference_status,
  'coordinate_median' AS reference_method,
  coalesce(aggregated.valid_coordinate_count, 0) AS valid_coordinate_count,
  coalesce(aggregated.office_count, 0) AS office_count,
  aggregated.coordinate_dispersion_degrees,
  coalesce(aggregated.state_candidates, array()) AS state_candidates,
  coalesce(aggregated.district_candidates, array()) AS district_candidates,
  CASE
    WHEN size(aggregated.state_candidates) = 1 AND size(aggregated.district_candidates) = 1 THEN 'unambiguous_label_evidence'
    WHEN size(aggregated.state_candidates) = 0 OR size(aggregated.district_candidates) = 0 THEN 'label_unavailable'
    ELSE 'ambiguous_label_evidence'
  END AS geography_status,
  'evidence_not_geographic_truth' AS administrative_label_semantics,
  '{{geography_version}}' AS geography_version,
  sha2(concat_ws('|',
    pins.pincode,
    coalesce(cast(aggregated.latitude_median AS STRING), 'unavailable'),
    coalesce(cast(aggregated.longitude_median AS STRING), 'unavailable'),
    concat_ws(',', aggregated.state_candidates),
    concat_ws(',', aggregated.district_candidates),
    '{{geography_version}}'
  ), 256) AS reference_hash,
  current_timestamp() AS created_at
FROM pins
LEFT JOIN aggregated ON pins.pincode = aggregated.pincode;

DELETE FROM {{project_catalog}}.silver.analysis_origin
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.analysis_origin
SELECT
  source_bundle_id,
  concat('pin:', pincode) AS analysis_origin_id,
  'postal_reference_point' AS origin_type,
  pincode,
  postal_reference_latitude AS latitude,
  postal_reference_longitude AS longitude,
  CASE WHEN reference_status = 'available' THEN 'mappable' ELSE 'unavailable' END AS origin_status,
  CASE WHEN reference_status = 'unavailable' THEN 'no_valid_postal_coordinate' ELSE NULL END AS unavailable_reason,
  geography_status,
  reference_hash,
  geography_version,
  current_timestamp() AS created_at
FROM {{project_catalog}}.silver.pin_postal_reference
WHERE source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(COUNT(*) = 19586, 'Analysis origin universe must retain all 19,586 PINs')
FROM {{project_catalog}}.silver.analysis_origin
WHERE source_bundle_id = '{{source_bundle_id}}';
