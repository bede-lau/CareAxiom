DELETE FROM {{project_catalog}}.gold.facility_documentary_support
WHERE source_bundle_id = '{{source_bundle_id}}';

INSERT INTO {{project_catalog}}.gold.facility_documentary_support
WITH validated_claims AS (
  SELECT
    claim.source_bundle_id,
    claim.facility_id,
    claim.capability_id,
    claim.claim_type,
    claim.polarity,
    claim.source_artifact_id,
    artifact.source_family,
    span.evidence_span_id,
    facility.freshness_status
  FROM {{project_catalog}}.silver.facility_claim claim
  JOIN {{project_catalog}}.silver.claim_validation validation
    ON claim.claim_id = validation.claim_id
   AND validation.validation_status IN ('passed', 'warning')
   AND NOT validation.abstain
  JOIN {{project_catalog}}.silver.source_artifact artifact ON claim.source_artifact_id = artifact.source_artifact_id
  JOIN {{project_catalog}}.silver.evidence_span span ON claim.claim_id = span.claim_id
  JOIN {{project_catalog}}.silver.facility_normalized facility
    ON claim.source_bundle_id = facility.source_bundle_id
   AND claim.facility_id = facility.facility_id
  WHERE claim.source_bundle_id = '{{source_bundle_id}}'
    AND claim.claim_status = 'validated'
),
aggregated AS (
  SELECT
    source_bundle_id,
    facility_id,
    capability_id,
    collect_set(claim_type) AS claim_types,
    collect_set(polarity) AS claim_polarities,
    collect_set(source_family) AS source_families,
    sort_array(collect_set(evidence_span_id)) AS evidence_span_ids,
    max(CASE WHEN freshness_status = 'known' THEN 10.0 WHEN freshness_status = 'stale' THEN 2.0 ELSE 0.0 END) AS freshness_factor
  FROM validated_claims
  GROUP BY source_bundle_id, facility_id, capability_id
),
factored AS (
  SELECT
    *,
    30.0 AS direct_evidence_specificity,
    least(20.0, greatest(0.0, (size(source_families) - 1) * 10.0)) AS independent_source_corroboration,
    10.0 AS source_quality,
    15.0 AS entity_attribution_quality,
    freshness_factor AS freshness,
    CASE
      WHEN capability_id = 'maternal_emergency_documentation'
       AND array_contains(claim_types, 'ob_gyn_specialty')
       AND array_contains(claim_types, 'c_section') THEN 10.0
      WHEN capability_id = 'emergency_surgery_documentation'
       AND array_contains(claim_types, 'emergency_medicine')
       AND array_contains(claim_types, 'general_surgery') THEN 10.0
      WHEN capability_id = 'advanced_imaging_documentation'
       AND array_contains(claim_types, 'ct')
       AND array_contains(claim_types, 'mri') THEN 10.0
      ELSE 0.0
    END AS prerequisite_support
  FROM aggregated
)
SELECT
  sha2(concat(source_bundle_id, ':', facility_id, ':', capability_id, ':{{policy_version}}'), 256) AS result_id,
  source_bundle_id,
  facility_id,
  capability_id,
  CASE
    WHEN prerequisite_support = 0 THEN
      least(49.0, direct_evidence_specificity + independent_source_corroboration + source_quality + entity_attribution_quality + freshness)
    ELSE
      least(100.0, direct_evidence_specificity + independent_source_corroboration + source_quality + entity_attribution_quality + freshness + prerequisite_support)
  END AS documentary_support_index,
  CASE
    WHEN prerequisite_support = 0 THEN 'claim_only_or_weak'
    WHEN direct_evidence_specificity + independent_source_corroboration + source_quality + entity_attribution_quality + freshness + prerequisite_support >= 75 THEN 'strongly_supported'
    WHEN direct_evidence_specificity + independent_source_corroboration + source_quality + entity_attribution_quality + freshness + prerequisite_support >= 50 THEN 'partially_supported'
    ELSE 'claim_only_or_weak'
  END AS support_band,
  CASE
    WHEN array_contains(claim_polarities, 'positive')
     AND array_contains(claim_polarities, 'negative') THEN 'unresolved'
    WHEN array_contains(claim_polarities, 'negative') THEN 'confirmed'
    WHEN array_contains(claim_polarities, 'uncertain') THEN 'unresolved'
    ELSE 'none'
  END AS contradiction_state,
  direct_evidence_specificity,
  independent_source_corroboration,
  source_quality,
  entity_attribution_quality,
  freshness,
  prerequisite_support,
  evidence_span_ids,
  CASE WHEN prerequisite_support = 0 THEN array('missing_configured_prerequisite') ELSE array() END AS exclusion_reasons,
  '{{policy_version}}' AS policy_version,
  sha2(concat_ws('|',
    source_bundle_id,
    facility_id,
    capability_id,
    cast(direct_evidence_specificity AS STRING),
    cast(independent_source_corroboration AS STRING),
    cast(source_quality AS STRING),
    cast(entity_attribution_quality AS STRING),
    cast(freshness AS STRING),
    cast(prerequisite_support AS STRING),
    concat_ws(',', evidence_span_ids),
    '{{policy_version}}'
  ), 256) AS result_hash,
  current_timestamp() AS calculated_at
FROM factored;

SELECT assert_true(
  COUNT_IF(documentary_support_index < 0 OR documentary_support_index > 100) = 0,
  'Documentary support index outside 0..100'
)
FROM {{project_catalog}}.gold.facility_documentary_support
WHERE source_bundle_id = '{{source_bundle_id}}';
