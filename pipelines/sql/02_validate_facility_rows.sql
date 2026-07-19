DELETE FROM {{project_catalog}}.silver.facility_row_integrity
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.facility_row_integrity
WITH classified AS (
  SELECT
    *,
    unique_id RLIKE '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$' AS uuid_shape_valid,
    row_number() OVER (PARTITION BY unique_id ORDER BY source_duplicate_ordinal, source_row_id) AS id_ordinal,
    min(raw_hash) OVER (PARTITION BY unique_id) AS minimum_id_raw_hash,
    max(raw_hash) OVER (PARTITION BY unique_id) AS maximum_id_raw_hash
  FROM {{project_catalog}}.bronze.facility_source_snapshot
  WHERE source_bundle_id = '{{source_bundle_id}}'
)
SELECT
  source_bundle_id,
  source_row_id,
  raw_hash,
  unique_id AS unique_id_raw,
  uuid_shape_valid,
  CASE
    WHEN uuid_shape_valid AND minimum_id_raw_hash = maximum_id_raw_hash THEN id_ordinal
    ELSE NULL
  END AS duplicate_ordinal,
  uuid_shape_valid
    AND (latitude IS NULL OR (latitude BETWEEN -90 AND 90))
    AND (longitude IS NULL OR (longitude BETWEEN -180 AND 180)) AS semantic_domain_valid,
  CASE
    WHEN NOT uuid_shape_valid THEN 'quarantined'
    WHEN minimum_id_raw_hash <> maximum_id_raw_hash THEN 'quarantined'
    WHEN id_ordinal > 1 THEN 'exact_duplicate'
    WHEN
      try_cast(number_doctors_raw AS DOUBLE) IS NULL AND number_doctors_raw IS NOT NULL
      OR try_cast(capacity_raw AS DOUBLE) IS NULL AND capacity_raw IS NOT NULL
    THEN 'partially_parsed'
    ELSE 'accepted'
  END AS disposition,
  CASE
    WHEN NOT uuid_shape_valid THEN 'non_uuid_structural_spillover'
    WHEN minimum_id_raw_hash <> maximum_id_raw_hash THEN 'conflicting_rows_share_uuid'
    WHEN id_ordinal > 1 THEN 'exact_duplicate_uuid_row'
    ELSE NULL
  END AS quarantine_reason,
  CASE WHEN uuid_shape_valid THEN lower(unique_id) ELSE NULL END AS canonical_facility_id,
  current_timestamp() AS classified_at
FROM classified;

SELECT assert_true(COUNT(*) = 10088, 'Facility dispositions do not conserve source rows')
FROM {{project_catalog}}.silver.facility_row_integrity
WHERE source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(
  COUNT_IF(
    quarantine_reason = 'non_uuid_structural_spillover'
    AND disposition <> 'quarantined'
  ) = 0,
  'Structurally invalid UUID rows must be quarantined'
)
FROM {{project_catalog}}.silver.facility_row_integrity
WHERE source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(
  COUNT(*) = 0,
  'Repeated UUIDs with conflicting raw hashes must be quarantined, not collapsed'
)
FROM (
  SELECT canonical_facility_id
  FROM {{project_catalog}}.silver.facility_row_integrity
  WHERE source_bundle_id = '{{source_bundle_id}}'
    AND canonical_facility_id IS NOT NULL
  GROUP BY canonical_facility_id
  HAVING count(DISTINCT raw_hash) > 1
     AND count_if(disposition <> 'quarantined') > 0
) conflicting_uuid;

SELECT assert_true(
  COUNT(*) = 0,
  'Exact duplicate rows must share one raw hash per UUID'
)
FROM (
  SELECT canonical_facility_id
  FROM {{project_catalog}}.silver.facility_row_integrity
  WHERE source_bundle_id = '{{source_bundle_id}}'
    AND disposition = 'exact_duplicate'
  GROUP BY canonical_facility_id
  HAVING count(DISTINCT raw_hash) > 1
) invalid_exact_duplicate;
