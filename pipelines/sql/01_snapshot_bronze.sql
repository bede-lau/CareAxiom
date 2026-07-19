DELETE FROM {{project_catalog}}.bronze.facility_source_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.bronze.facility_source_snapshot
WITH raw AS (
  SELECT
    *,
    to_json(struct(*)) AS raw_payload,
    sha2(to_json(struct(*)), 256) AS raw_hash
  FROM {{source_catalog}}.{{source_schema}}.facilities
),
numbered AS (
  SELECT
    *,
    row_number() OVER (PARTITION BY raw_hash ORDER BY coalesce(unique_id, ''), coalesce(name, '')) AS duplicate_ordinal
  FROM raw
)
SELECT
  '{{source_bundle_id}}' AS source_bundle_id,
  sha2(concat(raw_hash, ':', lpad(cast(duplicate_ordinal AS STRING), 6, '0')), 256) AS source_row_id,
  duplicate_ordinal AS source_duplicate_ordinal,
  raw_hash,
  raw_payload,
  unique_id,
  name,
  description,
  specialties AS specialties_raw,
  procedure AS procedure_raw,
  equipment AS equipment_raw,
  capability AS capability_raw,
  source_urls AS source_urls_raw,
  source_types AS source_types_raw,
  source AS source_raw,
  address_city,
  address_stateOrRegion AS address_state_or_region,
  address_zipOrPostcode AS address_zip_or_postcode,
  latitude,
  longitude,
  numberDoctors AS number_doctors_raw,
  capacity AS capacity_raw,
  yearEstablished AS year_established_raw,
  recency_of_page_update AS recency_of_page_update_raw,
  current_timestamp() AS ingested_at
FROM numbered;

DELETE FROM {{project_catalog}}.bronze.india_post_office_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.bronze.india_post_office_snapshot
WITH raw AS (
  SELECT
    *,
    to_json(struct(*)) AS raw_payload,
    sha2(to_json(struct(*)), 256) AS raw_hash
  FROM {{source_catalog}}.{{source_schema}}.india_post_pincode_directory
),
numbered AS (
  SELECT
    *,
    row_number() OVER (PARTITION BY raw_hash ORDER BY cast(pincode AS STRING), coalesce(officename, '')) AS duplicate_ordinal
  FROM raw
)
SELECT
  '{{source_bundle_id}}' AS source_bundle_id,
  sha2(concat(raw_hash, ':', lpad(cast(duplicate_ordinal AS STRING), 6, '0')), 256) AS source_row_id,
  duplicate_ordinal AS source_duplicate_ordinal,
  raw_hash,
  raw_payload,
  circlename,
  regionname,
  divisionname,
  officename,
  lpad(cast(pincode AS STRING), 6, '0') AS pincode,
  officetype,
  delivery,
  district,
  statename,
  latitude AS latitude_raw,
  longitude AS longitude_raw,
  current_timestamp() AS ingested_at
FROM numbered;

DELETE FROM {{project_catalog}}.bronze.nfhs5_district_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.bronze.nfhs5_district_snapshot
SELECT
  '{{source_bundle_id}}' AS source_bundle_id,
  sha2(concat(trim(state_ut), ':', trim(district_name)), 256) AS source_row_id,
  sha2(to_json(struct(*)), 256) AS raw_hash,
  to_json(struct(*)) AS raw_payload,
  state_ut AS state_raw,
  district_name AS district_raw,
  households_surveyed,
  women_15_49_interviewed,
  men_15_54_interviewed,
  current_timestamp() AS ingested_at
FROM {{source_catalog}}.{{source_schema}}.nfhs_5_district_health_indicators;

SELECT assert_true(COUNT(*) = 10088, 'Facility bronze conservation failed')
FROM {{project_catalog}}.bronze.facility_source_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(COUNT(*) = 165627, 'Postal bronze conservation failed')
FROM {{project_catalog}}.bronze.india_post_office_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}';

SELECT assert_true(COUNT(*) = 706, 'NFHS bronze conservation failed')
FROM {{project_catalog}}.bronze.nfhs5_district_snapshot
WHERE source_bundle_id = '{{source_bundle_id}}';
