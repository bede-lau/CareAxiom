# Authenticated Data Profile: Virtue Foundation DAIS 2026

Status: Read-only profiling complete
Profile date: 2026-07-19
Workspace host: authenticated Databricks workspace (intentionally omitted from the public repository)
Catalog: `databricks_virtue_foundation_dataset_dais_2026`
Schema: `virtue_foundation_dataset`
Companion PRD: `.omx/plans/prd-medical-desert-planner.md`
Companion verification plan: `.omx/plans/test-spec-medical-desert-planner.md`

## 1. Scope and Method

The catalog was inspected through an authenticated Databricks CLI profile and the Databricks SQL Statement Execution API using the `Serverless Starter Warehouse`.

Only read operations were issued:

- Catalog, schema, and table metadata reads.
- `SELECT`, aggregate, and limited sample queries.
- Information-schema inspection.

No source table, catalog, schema, permission, warehouse, or dataset value was modified.

## 2. Source Inventory

The share contains exactly three data tables with three different analytical grains.

| Table | Grain | Rows | Columns | Primary analytical role |
| --- | --- | ---: | ---: | --- |
| `facilities` | Extracted facility source row | 10,088 | 51 | Facility identity, documentary claims, source URLs, and point coordinates |
| `india_post_pincode_directory` | India Post office | 165,627 | 11 | Postal-office coordinates and administrative labels associated with PINs |
| `nfhs_5_district_health_indicators` | NFHS-5 state/district factsheet row | 706 | 109 | District survey context and sample metadata |

The three tables are not interchangeable:

- A facility row is documentary evidence about a named organization.
- A postal row is a post-office observation, not a PIN centroid or boundary.
- An NFHS row is a district survey profile, not a population count or facility-demand quantity.

## 3. Facilities Table

Full name:

`databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities`

### 3.1 Physical schema

- 49 string columns.
- 2 double columns: `latitude`, `longitude`.
- JSON-like arrays are stored as strings rather than structured arrays.

Important field groups:

| Group | Fields |
| --- | --- |
| Identity | `unique_id`, `name`, `organization_type`, `facilityTypeId`, `operatorTypeId`, `affiliationTypeIds` |
| Contact and web | `phone_numbers`, `officialPhone`, `email`, `websites`, `officialWebsite`, `facebookLink` |
| Address | `address_line1`, `address_line2`, `address_line3`, `address_city`, `address_stateOrRegion`, `address_zipOrPostcode`, `address_country`, `address_countryCode`, `countries` |
| Facility facts | `description`, `area`, `numberDoctors`, `capacity`, `yearEstablished` |
| Clinical documentary fields | `specialties`, `procedure`, `equipment`, `capability` |
| Source and freshness | `source_types`, `source_ids`, `source_content_id`, `content_table_id`, `source`, `source_urls`, `recency_of_page_update` |
| Geography | `coordinates`, `latitude`, `longitude`, `cluster_id` |
| Activity signals | social-presence, post, follower, like, and engagement fields |

### 3.2 Structural integrity

| Finding | Count |
| --- | ---: |
| Source rows | 10,088 |
| UUID-shaped rows | 10,000 |
| Non-UUID malformed/spillover rows | 88 |
| Distinct IDs across all rows | 10,077 |
| Distinct UUID-shaped IDs | 9,989 |
| Repeated UUIDs | 11 |
| Rows beyond the first for repeated UUIDs | 11 |
| Exact duplicate repeated IDs | 11 |
| Conflicting repeated IDs | 0 |

The 88 non-UUID rows contain text fragments or values shifted into incompatible columns. They have no valid coordinates or PIN values and must be preserved in bronze but quarantined from facility identity, evidence extraction, geography, and scoring.

The 11 repeated valid IDs are exact row duplicates. Bronze must preserve them; the canonical facility layer should collapse them deterministically while retaining source-row lineage.

### 3.3 Field coverage among the 10,000 UUID-shaped rows

| Field or condition | Rows | Coverage |
| --- | ---: | ---: |
| Description present | 10,000 | 100.0% |
| Non-empty parsed capability array | 9,944 | 99.4% |
| Non-empty parsed procedure array | 9,216 | 92.2% |
| Non-empty parsed equipment array | 7,680 | 76.8% |
| Numeric doctor count | 3,630 | 36.3% |
| Numeric capacity | 2,516 | 25.2% |
| Valid establishment year | 4,777 | 47.8% |
| Parseable page-update date | 3,535 | 35.4% |
| Coordinates within the broad India envelope | 9,964 | 99.6% |
| Strict six-digit PIN string | 9,766 | 97.7% |

These live measurements closely match the field-coverage claims in the hackathon brief, but they also show that freshness is unknown for most records.

For the snapshot contract, the broad coordinate envelope is longitude `68..98` east and latitude `6.5..39` north. These are validation bounds, not a legal or cartographic definition of India.

### 3.4 JSON-like field parsing

Across all 10,088 physical rows:

| Field | Array-parseable rows |
| --- | ---: |
| `specialties` | 9,970 |
| `procedure` | 9,940 |
| `equipment` | 9,860 |
| `capability` | 9,963 |
| `source_urls` | 9,970 |

Parsing failure must not be normalized to an empty array. Silver contracts require:

- Preserved raw string.
- Parsed value, if successful.
- Parser version.
- Parse status.
- Error or quality flags.

### 3.5 Repetition and vocabulary

The valid facility rows average:

| Field | Average mentions | Average distinct values | Maximum mentions |
| --- | ---: | ---: | ---: |
| Specialties | 28.0 | 11.9 | 50 |
| Procedures | 16.8 | 15.9 | 50 |
| Equipment | 6.1 | 5.6 | 50 |
| Capabilities | 23.3 | 22.5 | 50 |

Specialties behave like a noisy controlled ontology with repeated values. Procedures, equipment, and capabilities contain high-variance phrases and spelling variants.

Top specialties by distinct facility count include:

| Specialty | Facilities |
| --- | ---: |
| `internalMedicine` | 6,836 |
| `familyMedicine` | 5,175 |
| `gynecologyAndObstetrics` | 4,489 |
| `dentistry` | 4,190 |
| `orthopedicSurgery` | 3,519 |
| `pediatrics` | 3,429 |
| `generalSurgery` | 3,191 |
| `cardiology` | 3,003 |
| `radiology` | 2,993 |
| `ophthalmology` | 2,823 |
| `emergencyMedicine` | 2,079 |
| `criticalCareMedicine` | 1,673 |

High-frequency free-text capability phrases include 24/7 opening claims, emergency-care claims, accreditation, inpatient/outpatient services, and facility-type descriptions. These phrases require normalization and must not be treated as one controlled capability dimension without evidence-specific rules.

### 3.6 Candidate demo policy ingredients

The following counts are evidence-ingredient counts, not confirmed operational services:

| Documentary ingredient or policy | Valid facility rows |
| --- | ---: |
| OB-GYN specialty | 4,497 |
| Neonatology specialty | 1,255 |
| Emergency medicine specialty | 2,085 |
| General surgery specialty | 3,198 |
| Critical care specialty | 1,677 |
| Cardiology specialty | 3,011 |
| Radiology specialty | 2,999 |
| C-section phrase | 432 |
| CT claim | 1,270 |
| MRI claim | 894 |
| Blood-bank phrase | 526 |
| OB-GYN plus C-section phrase | 416 |
| Emergency medicine plus general surgery | 1,438 |
| CT plus MRI | 694 |

The specialty counts in this section use the proposed policy-normalization rules and can therefore differ slightly from the exact normalized-token counts in Section 3.5. G1 must version the synonym and normalization mapping that produces each policy ingredient.

Recommended initial demo policies:

1. `maternal_emergency_documentation`
   - OB-GYN specialty plus a C-section claim.
   - NFHS maternal indicators may be displayed separately as district survey context.
2. `emergency_surgery_documentation`
   - Emergency medicine plus general surgery documentary support.
3. `advanced_imaging_documentation`
   - Both CT and MRI documentary claims.

These are versioned documentary policies. They do not prove current staffing, readiness, capacity, or availability.

### 3.7 Source characteristics

Source-family values among valid rows:

| Source type | Facilities |
| --- | ---: |
| `overture` | 9,155 |
| `dynamic` | 6,932 |
| `constant` | 3,386 |
| `mongo_facility` | 1,124 |
| `mongo_ngo` | 228 |

Common source URL hosts are dominated by Facebook and third-party directories, including Justdial, Practo, Mappls, Medindia, and other aggregators. Multiple URLs from the same publisher family must not count as independent corroboration.

Reported fields:

| Field | Present rows |
| --- | ---: |
| `officialWebsite` | 8,393 |
| `websites` | 10,000 |
| `email` | 8,545 |
| `officialPhone` | 9,503 |

Presence does not guarantee correctness. Official-site discovery and source-family classification are high-impact Tavily use cases.

## 4. India Post PIN Directory

Full name:

`databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory`

### 4.1 Physical schema

- 10 string columns.
- One long column: `pincode`.
- Latitude and longitude are strings.
- Grain is one post office, not one PIN.

Columns:

`circlename`, `regionname`, `divisionname`, `officename`, `pincode`, `officetype`, `delivery`, `district`, `statename`, `latitude`, `longitude`.

### 4.2 Quality profile

| Finding | Count |
| --- | ---: |
| Source rows | 165,627 |
| Exact distinct rows | 165,625 |
| Exact duplicate rows | 2 |
| Distinct PINs | 19,586 |
| Coordinate rows in broad India bounds | 151,015 |
| Unparseable or missing coordinate rows | 12,015 |
| Zero-coordinate rows | 13 |
| Numeric non-zero rows outside broad India bounds | 2,584 |
| PINs with at least one valid coordinate | 19,550 |
| PINs spanning multiple state labels | 290 |
| PINs spanning multiple district labels | 1,478 |
| Maximum office rows for one PIN | 153 |
| Average office rows per PIN | 8.46 |

The four coordinate dispositions are mutually exclusive and sum to 165,627 rows. The broad coordinate envelope is longitude `68..98` east and latitude `6.5..39` north.

The derived PIN layer must retain:

- `office_count`.
- Valid-coordinate count.
- Coordinate aggregation method.
- Coordinate dispersion.
- State and district candidate sets.
- Consensus or ambiguity status.
- Original office-row lineage.

A median or medoid of valid post-office coordinates may be used only as a labeled `postal_reference_point`. It must not be called a PIN centroid.

## 5. NFHS-5 District Indicators

Full name:

`databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.nfhs_5_district_health_indicators`

### 5.1 Physical schema

- 109 columns.
- 706 rows.
- 36 normalized state or union-territory values.
- 706 unique normalized `state + district` keys.
- No duplicate normalized district keys.
- 704 district names contain outer whitespace and require trimming.
- One state value contains outer whitespace.
- 49 indicator columns are stored as strings in addition to the two string key columns.
- Remaining indicators and survey-count fields are doubles.

### 5.2 Survey metadata

| Measure | Value |
| --- | ---: |
| Minimum households surveyed | 213 |
| Maximum households surveyed | 990 |
| Average households surveyed | 900.5 |

`households_surveyed`, `women_15_49_interviewed`, and `men_15_54_interviewed` are sample metadata. They are not district population denominators.

### 5.3 Qualifier semantics

NFHS-5 factsheets use:

- Parentheses for estimates based on 25-49 unweighted cases.
- `*` for a percentage suppressed because it is based on fewer than 25 unweighted cases.

The parser must retain the raw value and produce:

- `numeric_value`.
- `qualifier = standard | low_sample_25_49 | suppressed_lt_25`.
- `parse_status`.
- Indicator definition and unit.
- Survey period and source version.

Suppressed values must remain unavailable. They must never become zero.

Examples of string-indicator suppression in this table:

| Indicator | Suppressed district rows |
| --- | ---: |
| Non-breastfeeding children 6-23 months receiving adequate diet | 643 |
| Children 6-8 months receiving complementary food and breastmilk | 642 |
| Diarrhoea treatment indicators | 492 each |
| Home-born children taken to a facility | 422 |
| Exclusive breastfeeding under six months | 261 |
| Fever or ARI taken to a facility/provider | 224 |
| Private-facility C-section rate | 150 |
| Pregnant women with anaemia | 134 |
| Fully vaccinated from vaccination-card information | 22 |

### 5.4 Permissible use

NFHS may support a separate district survey-context panel and an optional planning-priority sorting axis.

NFHS must not:

- Corroborate a facility capability.
- Enter a facility documentary-support score.
- Be treated as a district population count.
- Be converted into affected-person counts without a separate population denominator.
- By itself unlock a `medical-desert candidate` label.

## 6. Cross-Source Join Profile

Strict facility PIN joins use only six-digit PIN strings.

| Join stage | Facility rows |
| --- | ---: |
| UUID-shaped facility rows | 10,000 |
| Strict valid PIN | 9,766 |
| PIN found in India Post directory | 9,568 |
| PIN has one state and one district label | 9,055 |
| Exact normalized state/district match to NFHS | 5,862 |
| Valid derived postal reference point | 9,567 |

Only 58.6% of UUID-shaped facility rows currently reach NFHS through a strict, unambiguous, exact-name join.

Major mismatch causes include:

- Renamed districts, such as Pune, Belagavi, Bengaluru Urban, Mysuru, and Prayagraj.
- Newer district subdivisions absent from the 2019-21 NFHS district frame.
- Alternative state and district spellings.
- `NA` administrative labels.
- PINs legitimately or inconsistently associated with multiple districts.

Required contract:

- Join NFHS by normalized `state + district`, never district alone.
- Use a versioned, reviewable district alias and temporal crosswalk.
- Preserve source names and match reason.
- Do not use undocumented fuzzy matches.
- Do not let one-to-many office rows multiply facility counts or regional evidence.

## 7. Product Implications

### 7.1 Official mission

`Medical Desert Planner` remains the official mission and product name.

With the current catalog, the MVP can defensibly produce:

- Facility documentary-support results.
- Regional documentary evidence summaries.
- Low-nearby-documentary-support findings.
- Insufficient-corpus-evidence findings.
- District NFHS survey context.
- Planning-priority candidates that explicitly require external validation.

The current catalog cannot establish:

- A definitive medical desert.
- A population-weighted access deficit.
- Current operational capability.
- Current availability or capacity.
- Travel-time access.

### 7.2 Map strategy

Core map:

- Facility points.
- One `analysis_origin` per PIN, independent of facility presence: 19,586 origins are retained, 19,550 have a mappable postal reference, and 36 remain unavailable with an explicit reason.
- Optional versioned H3 or external tessellation origins may replace or augment the PIN-origin universe only after G1 comparison tests.
- Facility-derived H3 cells may be rendered as an evidence-density overlay, but they cannot define the analysis-origin universe.
- Postal reference points retain ambiguity and dispersion flags and are never treated as population origins.
- Synchronized accessible table.

District choropleth:

- Requires an external, versioned district-boundary asset and a reviewed temporal/name crosswalk.
- Must be feature-gated until geometry provenance and licensing are recorded.

### 7.3 Initial demo

Recommended one-minute path:

1. Select `maternal_emergency_documentation`.
2. Open a prepared district such as Darbhanga, Bihar.
3. Show low nearby documentary support and the exact contributing facility evidence.
4. Show NFHS maternal survey indicators as a separate context panel.
5. Open one questionable facility in Facility Trust Desk.
6. Submit or apply a review decision.
7. Show the changed documentary summary or assessability state.
8. State that the result is a planning-priority candidate, not proof of a medical desert.

Darbhanga is useful for a prepared demo because the strict current join produced:

- 15 observed facility records.
- 0 records meeting the initial OB-GYN plus C-section documentary policy.
- 3 emergency-medicine plus general-surgery records.
- 2 CT plus MRI records.
- NFHS four-plus ANC estimate: 24.9%.
- NFHS institutional-birth estimate: 69.9%.
- NFHS women age 15-49 with anaemia estimate: 60.8%.

These values are scenario inputs, not causal or operational conclusions.

## 8. Required Canonical Data Contracts

### Bronze

- `source_bundle_manifest`
- `facility_source_snapshot`
- `india_post_office_snapshot`
- `nfhs5_district_snapshot`

### Silver

- `facility_row_integrity`
- `facility_entity`
- `facility_normalized`
- `facility_field_parse`
- `source_artifact`
- `facility_claim`
- `extraction_assertion`
- `evidence_span`
- `evidence_relation`
- `facility_quality_signal`
- `web_evidence`
- `claim_validation`
- `postal_office_normalized`
- `pin_postal_reference`
- `analysis_origin`
- `district_identity_crosswalk`
- `nfhs_indicator_observation`
- `district_survey_context`
- `geography_dimension`
- `capability_dimension`

### Gold

- `facility_documentary_support`
- `regional_documentary_evidence_summary`
- `analysis_origin_facility_distance`
- `district_context_profile`
- `planning_priority_candidate`
- `verification_priority`
- `facility_evidence_document`
- `scenario_change_feed`

Canonical output fields include:

- `facility_documentary_support.documentary_support_index`
- `regional_documentary_evidence_summary.observed_record_assessability`
- `district_context_profile.survey_context_availability`

## 9. Gate Consequences

G0 must freeze:

- All three physical schemas and exact snapshot counts.
- The source bundle manifest.
- The 88-row structural quarantine contract.
- Exact duplicate behavior.
- JSON-like field parsing states.
- Post-office grain and postal-reference terminology.
- The independent `analysis_origin` universe and its unavailable-origin disposition.
- NFHS qualifier semantics and non-denominator role.
- Capability names, policy schema, policy DRI, named domain reviewer, and gate approver; executable policy rules remain a G1 deliverable.

G1 must prove:

- Every source row has an accounted disposition.
- Quarantined rows cannot reach extraction or aggregates.
- Exact duplicate collapse is deterministic.
- PIN office multiplicity cannot multiply facilities.
- Invalid and ambiguous geography is excluded and counted.
- All 706 NFHS rows are matched, unmatched, ambiguous, or crosswalked with a reason.
- Suppressed NFHS values remain unavailable.
- Origins with zero nearby observed facilities remain present and return insufficient corpus evidence.
- Removing NFHS input changes only survey-context availability and never changes facility support, observed-record assessability, or the regional documentary classification.
- Executable documentary, prerequisite, contradiction, and freshness rules pass fixture review and are versioned.
- District geometry strategy is resolved.

## 10. Remaining Manual Decisions

- Create the project catalog and bronze/silver/gold/evaluation schemas.
- Decide whether to import a versioned district-boundary asset or ship the core with H3 and point layers only.
- Approve the initial three documentary policies.
- Name the domain reviewer and review owner.
- Define and review district alias/crosswalk rules.
- Test Tavily egress from the Databricks App runtime.
- Confirm the Foundation Model API endpoint and quota.
- Create and bind Lakebase, the Databricks App, MLflow experiment, secret resource, and recalculation Job.

## 11. Reference

NFHS-5 national reporting explains that parenthesized figures are based on 25-49 unweighted cases and asterisks mark figures suppressed because they are based on fewer than 25 unweighted cases:

- https://dhsprogram.com/pubs/pdf/FR375/FR375.pdf
