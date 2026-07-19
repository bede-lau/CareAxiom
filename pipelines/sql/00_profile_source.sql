DELETE FROM {{project_catalog}}.bronze.source_bundle_manifest
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.bronze.source_bundle_manifest
WITH source_contracts AS (
  SELECT 'facilities' AS source_table, 'extracted facility source row' AS source_grain, 10088 AS expected_rows, 51 AS expected_columns
  UNION ALL
  SELECT 'india_post_pincode_directory', 'India Post office', 165627, 11
  UNION ALL
  SELECT 'nfhs_5_district_health_indicators', 'NFHS-5 state and district factsheet row', 706, 109
),
observed AS (
  SELECT
    contract.*,
    CASE contract.source_table
      WHEN 'facilities' THEN (SELECT COUNT(*) FROM {{source_catalog}}.{{source_schema}}.facilities)
      WHEN 'india_post_pincode_directory' THEN (SELECT COUNT(*) FROM {{source_catalog}}.{{source_schema}}.india_post_pincode_directory)
      WHEN 'nfhs_5_district_health_indicators' THEN (SELECT COUNT(*) FROM {{source_catalog}}.{{source_schema}}.nfhs_5_district_health_indicators)
    END AS observed_rows
  FROM source_contracts contract
),
schemas AS (
  SELECT
    table_name,
    COUNT(*) AS observed_columns,
    sha2(
      concat_ws(
        '|',
        sort_array(collect_list(concat(column_name, ':', full_data_type, ':', ordinal_position)))
      ),
      256
    ) AS schema_fingerprint
  FROM {{source_catalog}}.information_schema.columns
  WHERE table_schema = '{{source_schema}}'
    AND table_name IN ('facilities', 'india_post_pincode_directory', 'nfhs_5_district_health_indicators')
  GROUP BY table_name
)
SELECT
  '{{source_bundle_id}}',
  '{{source_catalog}}',
  '{{source_schema}}',
  observed.source_table,
  observed.source_grain,
  observed.expected_rows,
  observed.observed_rows,
  observed.expected_columns,
  schemas.observed_columns,
  schemas.schema_fingerprint,
  current_timestamp(),
  CASE
    WHEN observed.expected_rows = observed.observed_rows
     AND observed.expected_columns = schemas.observed_columns THEN 'matched'
    ELSE 'drift_detected'
  END,
  '1.0.0'
FROM observed
JOIN schemas ON observed.source_table = schemas.table_name;

SELECT assert_true(
  COUNT_IF(profile_status <> 'matched') = 0,
  'Source contract drift detected; create a new source bundle before continuing.'
)
FROM {{project_catalog}}.bronze.source_bundle_manifest
WHERE source_bundle_id = '{{source_bundle_id}}';
