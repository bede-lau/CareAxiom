DELETE FROM {{project_catalog}}.silver.nfhs_indicator_observation
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.silver.nfhs_indicator_observation
WITH source_map AS (
  SELECT
    source_bundle_id,
    source_row_id,
    state_raw,
    district_raw,
    from_json(raw_payload, 'MAP<STRING,STRING>') AS fields
  FROM {{project_catalog}}.bronze.nfhs5_district_snapshot
  WHERE source_bundle_id = '{{source_bundle_id}}'
),
long_form AS (
  SELECT
    source_bundle_id,
    source_row_id,
    state_raw,
    district_raw,
    indicator_id,
    raw_value
  FROM source_map
  LATERAL VIEW explode(fields) exploded AS indicator_id, raw_value
  WHERE indicator_id NOT IN (
    'district_name',
    'state_ut',
    'households_surveyed',
    'women_15_49_interviewed',
    'men_15_54_interviewed'
  )
)
SELECT
  sha2(concat(source_row_id, ':', indicator_id), 256) AS observation_id,
  source_bundle_id,
  source_row_id,
  state_raw,
  district_raw,
  trim(regexp_replace(lower(state_raw), '[^a-z0-9]+', ' ')) AS normalized_state,
  trim(regexp_replace(lower(district_raw), '[^a-z0-9]+', ' ')) AS normalized_district,
  indicator_id,
  raw_value,
  CASE
    WHEN trim(raw_value) = '*' THEN NULL
    WHEN trim(raw_value) RLIKE '^\\([-+]?[0-9]+(\\.[0-9]+)?\\)$'
      THEN try_cast(regexp_extract(trim(raw_value), '[-+]?[0-9]+(\\.[0-9]+)?', 0) AS DOUBLE)
    WHEN trim(raw_value) RLIKE '^[-+]?[0-9]+(\\.[0-9]+)?$'
      THEN try_cast(trim(raw_value) AS DOUBLE)
    ELSE NULL
  END AS numeric_value,
  CASE
    WHEN trim(raw_value) = '*' THEN 'suppressed_lt_25'
    WHEN trim(raw_value) RLIKE '^\\([-+]?[0-9]+(\\.[0-9]+)?\\)$' THEN 'low_sample_25_49'
    WHEN trim(raw_value) RLIKE '^[-+]?[0-9]+(\\.[0-9]+)?$' THEN 'standard'
    ELSE 'unparseable'
  END AS qualifier,
  CASE
    WHEN raw_value IS NULL OR trim(raw_value) = '' THEN 'missing'
    WHEN trim(raw_value) = '*' THEN 'suppressed'
    WHEN trim(raw_value) RLIKE '^\\([-+]?[0-9]+(\\.[0-9]+)?\\)$' THEN 'parsed'
    WHEN trim(raw_value) RLIKE '^[-+]?[0-9]+(\\.[0-9]+)?$' THEN 'parsed'
    ELSE 'unparseable'
  END AS parse_status,
  CASE WHEN indicator_id LIKE '%_pct' THEN 'percent' ELSE 'reported_value' END AS unit,
  'NFHS-5 2019-2021' AS survey_period,
  'nfhs5-district-dais-2026' AS source_version,
  current_timestamp() AS parsed_at
FROM long_form;

SELECT assert_true(
  COUNT_IF(qualifier = 'suppressed_lt_25' AND numeric_value IS NOT NULL) = 0,
  'Suppressed NFHS values must remain unavailable'
)
FROM {{project_catalog}}.silver.nfhs_indicator_observation
WHERE source_bundle_id = '{{source_bundle_id}}';
