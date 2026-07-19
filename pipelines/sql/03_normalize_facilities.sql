DELETE FROM {{project_catalog}}.silver.facility_entity
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.facility_entity
WITH eligible AS (
  SELECT
    source.source_bundle_id,
    integrity.canonical_facility_id AS facility_id,
    source.source_row_id,
    source.name,
    integrity.duplicate_ordinal,
    row_number() OVER (
      PARTITION BY integrity.canonical_facility_id
      ORDER BY integrity.duplicate_ordinal, source.source_row_id
    ) AS canonical_ordinal,
    count(*) OVER (PARTITION BY integrity.canonical_facility_id) AS source_row_count
  FROM {{project_catalog}}.bronze.facility_source_snapshot source
  JOIN {{project_catalog}}.silver.facility_row_integrity integrity
    ON source.source_bundle_id = integrity.source_bundle_id
   AND source.source_row_id = integrity.source_row_id
  WHERE source.source_bundle_id = '{{source_bundle_id}}'
    AND integrity.disposition <> 'quarantined'
)
SELECT
  source_bundle_id,
  facility_id,
  source_row_id AS canonical_source_row_id,
  source_row_count,
  source_row_count - 1 AS exact_duplicate_count,
  name AS canonical_name,
  'verified_uuid_exact_duplicate_collapse' AS entity_resolution_method,
  'uuid-collapse-v1' AS entity_resolution_version,
  current_timestamp() AS created_at
FROM eligible
WHERE canonical_ordinal = 1;

DELETE FROM {{project_catalog}}.silver.facility_field_parse
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.facility_field_parse
WITH canonical AS (
  SELECT source.*
  FROM {{project_catalog}}.bronze.facility_source_snapshot source
  JOIN {{project_catalog}}.silver.facility_entity entity
    ON source.source_bundle_id = entity.source_bundle_id
   AND source.source_row_id = entity.canonical_source_row_id
  WHERE source.source_bundle_id = '{{source_bundle_id}}'
),
fields AS (
  SELECT source_bundle_id, lower(unique_id) AS facility_id, source_row_id, 'specialties' AS field_name, specialties_raw AS raw_value FROM canonical
  UNION ALL
  SELECT source_bundle_id, lower(unique_id), source_row_id, 'procedure', procedure_raw FROM canonical
  UNION ALL
  SELECT source_bundle_id, lower(unique_id), source_row_id, 'equipment', equipment_raw FROM canonical
  UNION ALL
  SELECT source_bundle_id, lower(unique_id), source_row_id, 'capability', capability_raw FROM canonical
  UNION ALL
  SELECT source_bundle_id, lower(unique_id), source_row_id, 'source_urls', source_urls_raw FROM canonical
)
SELECT
  source_bundle_id,
  facility_id,
  source_row_id,
  field_name,
  raw_value,
  from_json(raw_value, 'ARRAY<STRING>') AS parsed_values,
  CASE
    WHEN raw_value IS NULL OR lower(trim(raw_value)) IN ('', 'null') THEN 'missing'
    WHEN from_json(raw_value, 'ARRAY<STRING>') IS NULL THEN 'unparseable'
    WHEN size(from_json(raw_value, 'ARRAY<STRING>')) = 0 THEN 'parsed_empty'
    ELSE 'parsed'
  END AS parse_status,
  'json-array-v1' AS parser_version,
  CASE
    WHEN raw_value IS NOT NULL AND from_json(raw_value, 'ARRAY<STRING>') IS NULL
      THEN array('raw_preserved', 'manual_review_candidate')
    ELSE array()
  END AS quality_flags,
  current_timestamp() AS parsed_at
FROM fields;

DELETE FROM {{project_catalog}}.silver.facility_normalized
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.facility_normalized
SELECT
  source.source_bundle_id,
  entity.facility_id,
  source.name AS canonical_name,
  trim(regexp_replace(lower(source.name), '[^a-z0-9]+', ' ')) AS normalized_name,
  source.description,
  source.address_city AS city_raw,
  nullif(trim(regexp_replace(lower(source.address_city), '[^a-z0-9]+', ' ')), '') AS city_normalized,
  source.address_state_or_region AS state_raw,
  nullif(trim(regexp_replace(lower(source.address_state_or_region), '[^a-z0-9]+', ' ')), '') AS state_normalized,
  CASE
    WHEN trim(source.address_zip_or_postcode) RLIKE '^[0-9]{6}$'
      THEN trim(source.address_zip_or_postcode)
    ELSE NULL
  END AS pincode,
  source.latitude,
  source.longitude,
  CASE
    WHEN source.latitude BETWEEN 6.5 AND 39
     AND source.longitude BETWEEN 68 AND 98 THEN 'valid_broad_envelope'
    WHEN source.latitude IS NULL OR source.longitude IS NULL THEN 'missing'
    ELSE 'outside_broad_envelope'
  END AS coordinate_status,
  try_cast(source.number_doctors_raw AS DOUBLE) AS number_doctors,
  CASE
    WHEN source.number_doctors_raw IS NULL THEN 'missing'
    WHEN try_cast(source.number_doctors_raw AS DOUBLE) IS NULL THEN 'unparseable'
    ELSE 'numeric'
  END AS number_doctors_status,
  try_cast(source.capacity_raw AS DOUBLE) AS capacity,
  CASE
    WHEN source.capacity_raw IS NULL THEN 'missing'
    WHEN try_cast(source.capacity_raw AS DOUBLE) IS NULL THEN 'unparseable'
    ELSE 'numeric'
  END AS capacity_status,
  CASE
    WHEN try_cast(source.year_established_raw AS INT) BETWEEN 1600 AND year(current_date())
      THEN try_cast(source.year_established_raw AS INT)
    ELSE NULL
  END AS year_established,
  CASE
    WHEN source.year_established_raw IS NULL THEN 'missing'
    WHEN try_cast(source.year_established_raw AS INT) BETWEEN 1600 AND year(current_date()) THEN 'valid'
    ELSE 'invalid'
  END AS year_established_status,
  try_cast(source.recency_of_page_update_raw AS DATE) AS page_update_date,
  CASE
    WHEN try_cast(source.recency_of_page_update_raw AS DATE) IS NULL THEN 'unknown'
    WHEN try_cast(source.recency_of_page_update_raw AS DATE) < add_months(current_date(), -36) THEN 'stale'
    ELSE 'known'
  END AS freshness_status,
  cast(NULL AS DOUBLE) AS pin_reference_distance_km,
  'pending_pin_reference' AS location_conflict_status,
  false AS regional_aggregation_eligible,
  current_timestamp() AS normalized_at
FROM {{project_catalog}}.silver.facility_entity entity
JOIN {{project_catalog}}.bronze.facility_source_snapshot source
  ON entity.source_bundle_id = source.source_bundle_id
 AND entity.canonical_source_row_id = source.source_row_id
WHERE entity.source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(
  COUNT(*) = (
    SELECT count(DISTINCT canonical_facility_id)
    FROM {{project_catalog}}.silver.facility_row_integrity
    WHERE source_bundle_id = '{{source_bundle_id}}'
      AND disposition <> 'quarantined'
  ),
  'Canonical facility count must equal the distinct eligible UUID count'
)
FROM {{project_catalog}}.silver.facility_entity
WHERE source_bundle_id = '{{source_bundle_id}}';
