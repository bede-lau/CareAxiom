import {
  capabilities,
  demoHealth,
  facilities,
  geographies,
  initialScenarios,
  regions,
  surveyContext,
  verificationItems,
} from "../demoData";
import type {
  Capability,
  CapabilityId,
  DocumentaryQuery,
  DocumentaryState,
  ExternalVerificationResult,
  Facility,
  GeographyOption,
  HealthResponse,
  RegionResult,
  Scenario,
  SurveyContext,
  VerificationItem,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const STORAGE_KEY = "careaxiom-scenarios-v1";
const DEMO_FALLBACK_ENABLED = import.meta.env.VITE_DEMO_FALLBACK === "true";

type JsonObject = Record<string, unknown>;

interface BackendGeography {
  geography_id: string;
  geography_type: GeographyOption["type"];
  name: string;
  state: string | null;
  district: string | null;
  pin: string | null;
  selectable: boolean;
  unavailable_reason: string | null;
  metadata: JsonObject;
}

interface BackendScoreFactors {
  direct_evidence_specificity: number;
  independent_source_corroboration: number;
  source_quality: number;
  entity_attribution_quality: number;
  freshness: number;
  prerequisite_support: number;
}

interface BackendAssessment {
  facility_id: string;
  capability_id: CapabilityId;
  documentary_support_index: number | null;
  support_band: string;
  contradiction_state: "none" | "unresolved" | "confirmed";
  evidence_sufficiency: string;
  decision_readiness: string;
  score_factors: BackendScoreFactors | null;
  missing_prerequisites: string[];
  contradictions: string[];
  evidence_ids: string[];
  rule_version: string;
  machine_assessed_at: string;
  human_reviewed_verdict: string | null;
  human_review_reason: string | null;
  review_version: number;
}

interface BackendEvidence {
  evidence_id: string;
  facility_id: string;
  capability_id: CapabilityId;
  source_field: string;
  exact_text: string;
  source_url: string | null;
  publisher: string;
  source_family: string;
  retrieval_time: string | null;
  extraction_method: string;
  extraction_version: string;
  entity_attribution_confidence: number;
  polarity: "positive" | "negative" | "uncertain";
}

interface BackendFacilitySummary {
  facility_id: string;
  name: string;
  city: string | null;
  district: string | null;
  state: string;
  pin: string | null;
  latitude: number | null;
  longitude: number | null;
  assessment: BackendAssessment;
  contribution_reason: string;
}

interface BackendSurveyContext {
  district_id: string;
  district: string;
  state: string;
  survey_context_availability: string;
  indicators: Array<{
    label: string;
    raw_value: string;
    numeric_value: number | null;
    qualifier: "standard" | "low_sample_25_49" | "suppressed_lt_25" | "unparseable";
    unit: string;
    survey_period: string;
  }>;
  limitations: string[];
}

interface BackendDocumentaryResult {
  result_id: string;
  capability_id: CapabilityId;
  geography: BackendGeography;
  radius_km: number;
  classification: string;
  classification_label: string;
  observed_record_assessability: {
    observed_record_assessability: number;
    n_region_entities: number;
    source_bundle_version: string;
  };
  distinct_observed_facilities: number;
  qualifying_facilities: number;
  contradiction_count: number;
  excluded_counts: Record<string, number>;
  facilities: BackendFacilitySummary[];
  survey_context: BackendSurveyContext | null;
  planning_priority_candidate: boolean;
  external_validation_required: boolean;
  source_bundle_id: string;
  policy_version: string;
  materialization_state: "pending" | "applied" | "failed" | "blocked_dependency";
  trace_id: string;
}

interface BackendFacilityDetail {
  facility_id: string;
  name: string;
  description: string;
  city: string | null;
  district: string | null;
  state: string;
  pin: string | null;
  latitude: number | null;
  longitude: number | null;
  observed_fields: JsonObject;
  assessments: BackendAssessment[];
  review_history: JsonObject[];
}

interface BackendVerificationItem {
  item_id: string;
  facility_id: string;
  capability_id: CapabilityId;
  question: string;
  why_it_matters: string;
  affected_region_ids: string[];
  affected_scenario_ids: string[];
  priority: number;
  recommended_action: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

interface BackendExternalVerificationResult {
  verification_item_id: string;
  mode: "cached" | "live";
  query: string;
  results: Array<{
    url: string;
    title: string | null;
    excerpt: string | null;
    score: number | null;
  }>;
  limitation: string;
  trace_id: string;
}

interface BackendScenario {
  scenario_id: string;
  name: string;
  capability_id: CapabilityId;
  geography_id: string;
  radius_km: number;
  selected_region_ids: string[];
  shortlisted_facility_ids: string[];
  notes: string;
  decision_rationale: string;
  machine_score_version: string;
  human_review_version: number;
  dataset_snapshot_id: string;
  evidence_snapshot_id: string;
  saved_result: BackendDocumentaryResult;
  version: number;
  created_at: string;
  updated_at: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly recovery: string,
    readonly traceId?: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body.message ?? `Request failed with status ${response.status}`,
      response.status,
      body.code ?? "API_REQUEST_FAILED",
      body.recovery ?? "Retry or continue with the last stable result.",
      body.request_id,
    );
  }
  return response.json() as Promise<T>;
}

async function withServiceFallback<T>(live: () => Promise<T>, fallback: T): Promise<T> {
  if (!DEMO_FALLBACK_ENABLED) return live();
  try {
    return await live();
  } catch (error) {
    if (error instanceof ApiError && error.status < 500) throw error;
    if (!(error instanceof ApiError) && !(error instanceof TypeError)) throw error;
    await new Promise((resolve) => window.setTimeout(resolve, 120));
    return fallback;
  }
}

function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function mapGeography(value: BackendGeography): GeographyOption {
  return {
    id: value.geography_id,
    type: value.geography_type,
    name: value.name,
    state: value.state ?? undefined,
    district: value.district ?? undefined,
    pin: value.pin ?? undefined,
    selectable: value.selectable,
    unavailableReason: value.unavailable_reason ?? undefined,
  };
}

function mapDocumentaryState(classification: string, externalValidation: boolean): DocumentaryState {
  if (classification === "strong_nearby_documentary_support") return "strong";
  if (classification === "mixed_signal_verification_required") return "mixed";
  if (classification === "insufficient_corpus_evidence") return "insufficient";
  if (classification === "unavailable_analysis") return "unavailable";
  return externalValidation ? "validation" : "low";
}

function mapDocumentaryResult(value: BackendDocumentaryResult): RegionResult {
  const fallbackPosition = regions[0];
  const metadata = value.geography.metadata ?? {};
  return {
    id: value.geography.geography_id,
    name: value.geography.pin
      ? `${value.geography.name} ${value.geography.pin}`
      : value.geography.name,
    district: value.geography.district ?? value.geography.name,
    state: value.geography.state ?? "",
    pin: value.geography.pin ?? "",
    x: typeof metadata.map_x === "number" ? metadata.map_x : fallbackPosition.x,
    y: typeof metadata.map_y === "number" ? metadata.map_y : fallbackPosition.y,
    stateCode: typeof metadata.state_code === "string" ? metadata.state_code : "IN",
    documentaryState: mapDocumentaryState(value.classification, value.external_validation_required),
    documentaryLabel: value.classification_label,
    supportedFacilities: value.qualifying_facilities,
    observedFacilities: value.distinct_observed_facilities,
    assessability: value.observed_record_assessability.observed_record_assessability,
    priority: value.planning_priority_candidate ? 0.92 : Math.max(0.2, 1 - value.observed_record_assessability.observed_record_assessability),
    postalMethod: typeof metadata.postal_reference_method === "string"
      ? metadata.postal_reference_method
      : "Backend geography reference",
    postalAmbiguity: typeof metadata.ambiguity === "string"
      ? metadata.ambiguity
      : `${value.excluded_counts.geography_conflict ?? 0} geography conflicts excluded`,
    dispersionKm: typeof metadata.dispersion_km === "number" ? metadata.dispersion_km : 0,
    materializationState: value.materialization_state,
    traceId: value.trace_id,
    facilityOptions: value.facilities.map((facility) => ({
      id: facility.facility_id,
      name: facility.name,
      contributionReason: facility.contribution_reason,
    })),
  };
}

function mapSurvey(value: BackendSurveyContext): SurveyContext {
  return {
    district: value.district,
    state: value.state,
    period: value.indicators[0]?.survey_period
      ? `NFHS-5, ${value.indicators[0].survey_period}`
      : "NFHS-5",
    availability:
      value.survey_context_availability === "matched"
        ? "matched"
        : value.survey_context_availability === "crosswalked"
          ? "crosswalked"
          : "unavailable",
    metrics: value.indicators.map((indicator) => ({
      label: indicator.label,
      value: indicator.numeric_value === null ? "Unavailable" : `${indicator.numeric_value}${indicator.unit === "percent" ? "%" : ""}`,
      rawValue: indicator.raw_value,
      qualifier: indicator.qualifier,
    })),
    householdsSurveyed: null,
    note: value.limitations.join(" "),
  };
}

function assessmentFactors(value: BackendScoreFactors | null) {
  if (!value) return [];
  return [
    { label: "Evidence specificity", value: value.direct_evidence_specificity, max: 30 },
    { label: "Independent corroboration", value: value.independent_source_corroboration, max: 20 },
    { label: "Source quality", value: value.source_quality, max: 15 },
    { label: "Entity attribution", value: value.entity_attribution_quality, max: 15 },
    { label: "Freshness", value: value.freshness, max: 10 },
    { label: "Prerequisites", value: value.prerequisite_support, max: 10 },
  ];
}

function geographyConflict(detail: BackendFacilityDetail) {
  const signals = Array.isArray(detail.observed_fields.quality_signals)
    ? (detail.observed_fields.quality_signals as JsonObject[])
    : [];
  const conflict = signals.find((signal) => signal.code === "pin_coordinate_city_conflict");
  if (!conflict) return undefined;
  return {
    city: detail.city ?? "Unknown",
    longitude: detail.longitude ?? 0,
    pinDistrict: detail.district ?? "Unknown",
    disposition: typeof conflict.detail === "string"
      ? `${conflict.detail} Excluded from confident planning results pending geography review.`
      : "Excluded from confident planning results pending geography review.",
  };
}

function mapFacility(
  detail: BackendFacilityDetail,
  evidence: BackendEvidence[],
  capabilityId: CapabilityId,
): Facility {
  const assessment =
    detail.assessments.find((item) => item.capability_id === capabilityId) ??
    detail.assessments[0];
  if (!assessment) {
    throw new Error(`Facility ${detail.facility_id} has no capability assessments.`);
  }
  return {
    id: detail.facility_id,
    name: detail.name,
    location: [detail.city, detail.district, detail.state].filter(Boolean).join(", "),
    capabilityId: assessment.capability_id,
    machineVerdict: titleCase(assessment.support_band),
    humanVerdict: assessment.human_reviewed_verdict
      ? titleCase(assessment.human_reviewed_verdict)
      : undefined,
    supportIndex: assessment.documentary_support_index,
    supportBand: titleCase(assessment.support_band),
    contradictionState: assessment.contradiction_state,
    freshness: `Machine assessed ${new Date(assessment.machine_assessed_at).toLocaleDateString()}`,
    attributionConfidence: evidence[0]?.entity_attribution_confidence ?? 0,
    missingPrerequisites: [...assessment.missing_prerequisites, ...assessment.contradictions],
    locationConflict: geographyConflict(detail),
    factors: assessmentFactors(assessment.score_factors),
    evidence: evidence.map((item) => ({
      id: item.evidence_id,
      polarity:
        item.polarity === "positive"
          ? "supporting"
          : item.polarity === "negative"
            ? "contradicting"
            : "unknown",
      text: item.exact_text,
      sourceField: item.source_field,
      publisher: item.publisher,
      sourceFamily: item.source_family,
      url: item.source_url,
      retrievedAt: item.retrieval_time ?? "Unavailable",
      extractionVersion: `${item.extraction_method} ${item.extraction_version}`,
    })),
    history: detail.review_history.map((item) => ({
      actor: String(item.actor_id ?? item.actor ?? "Reviewer"),
      action: String(item.action ?? item.status ?? "Review event"),
      time: String(item.created_at ?? item.timestamp ?? "Time unavailable"),
      reason: String(item.reason ?? "No reason recorded."),
    })),
  };
}

const knownFacilityNames = new Map(
  facilities.map((facility) => [facility.id, facility.name]),
);

function mapVerification(value: BackendVerificationItem): VerificationItem {
  const mappedStatus: VerificationItem["status"] =
    value.status === "open" || value.status === "in_review" || value.status === "deferred" || value.status === "unresolved"
      ? value.status
      : "resolved";
  const issue = value.question;
  return {
    id: value.item_id,
    facilityId: value.facility_id,
    facilityName: knownFacilityNames.get(value.facility_id) ?? value.facility_id,
    issue,
    whyItMatters: value.why_it_matters,
    capability: titleCase(value.capability_id),
    region: value.affected_region_ids.join(", ") || "No region attached",
    priority: value.priority,
    affectedRegions: value.affected_region_ids.length,
    scenarioReferences: value.affected_scenario_ids.length,
    ageDays: Math.max(0, Math.floor((Date.now() - Date.parse(value.created_at)) / 86_400_000)),
    status: mappedStatus,
    traceId: `verification:${value.item_id}`,
    flag: issue.toLowerCase().includes("location") ? "location_conflict" : "evidence_gap",
    backendVersion: value.version,
  };
}

function mapScenario(value: BackendScenario): Scenario {
  return {
    id: value.scenario_id,
    name: value.name,
    capabilityId: value.capability_id,
    geography: value.geography_id,
    radiusKm: value.radius_km,
    selectedRegionIds: value.selected_region_ids,
    facilityIds: value.shortlisted_facility_ids,
    notes: value.notes || value.decision_rationale,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
    version: value.version,
    sourceBundleId: value.dataset_snapshot_id,
    policyVersion: value.machine_score_version,
    evidenceSnapshotId: value.evidence_snapshot_id,
    traceId: value.saved_result.trace_id,
    changeSummary: [],
  };
}

function loadLocalScenarios(): Scenario[] {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return initialScenarios;
  try {
    return JSON.parse(stored) as Scenario[];
  } catch {
    return initialScenarios;
  }
}

export const apiClient = {
  getHealth: () =>
    withServiceFallback(
      async () => {
        const value = await request<{
          status: "healthy" | "degraded";
          components: Record<string, { status: string; detail: string }>;
          dataset_snapshot_version: string;
          timestamp: string;
        }>("/health");
        return {
          state: value.status,
          traceId: `health:${value.timestamp}`,
          snapshotVersion: value.dataset_snapshot_version,
          components: Object.entries(value.components).map(([name, component]) => ({
            name: titleCase(name),
            state:
              component.status === "healthy"
                ? "healthy"
                : component.status === "unavailable"
                  ? "unavailable"
                  : "degraded",
            detail: component.detail,
          })),
        } satisfies HealthResponse;
      },
      demoHealth,
    ),
  getCapabilities: () =>
    withServiceFallback(
      async () => {
        const values = await request<Array<{
          capability_id: CapabilityId;
          label: string;
          description: string;
        }>>("/capabilities");
        return values.map((value) => ({
          id: value.capability_id,
          label: value.label,
          shortLabel: value.label.replace(" documentation", ""),
          description: value.description,
        })) satisfies Capability[];
      },
      capabilities,
    ),
  getGeographies: () =>
    withServiceFallback(
      async () => (await request<BackendGeography[]>("/geographies")).map(mapGeography),
      geographies,
    ),
  queryDocumentaryEvidence: (query: DocumentaryQuery) =>
    withServiceFallback(
      async () => {
        const value = await request<BackendDocumentaryResult>("/documentary-evidence/query", {
          method: "POST",
          body: JSON.stringify({
            capability_id: query.capabilityId,
            geography_id: query.geography,
            radius_km: query.radiusKm,
            include_facilities: true,
          }),
        });
        return [mapDocumentaryResult(value)];
      },
      regions
        .filter((region) => query.geography === "district:br:darbhanga" || region.id === query.geography)
        .map((region) => {
          if (region.id !== "darbhanga-846004") return region;
          const supported =
            query.capabilityId === "maternal_emergency_documentation"
              ? 0
              : query.capabilityId === "emergency_surgery_documentation"
                ? 3
                : 2;
          return {
            ...region,
            supportedFacilities: supported,
            documentaryState: supported ? ("strong" as const) : ("low" as const),
            documentaryLabel: supported
              ? "Strong nearby documentary support"
              : "Low nearby documentary support; external validation required",
          };
        }),
    ),
  getSurveyContext: (districtId: string) =>
    withServiceFallback(
      async () => mapSurvey(await request<BackendSurveyContext>(`/districts/${districtId}/survey-context`)),
      surveyContext,
    ),
  getFacility: (facilityId: string, capabilityId: CapabilityId) =>
    withServiceFallback(
      async () => {
        const [detail, evidence] = await Promise.all([
          request<BackendFacilityDetail>(`/facilities/${facilityId}`),
          request<BackendEvidence[]>(`/facilities/${facilityId}/evidence?capability_id=${capabilityId}`),
        ]);
        return mapFacility(detail, evidence, capabilityId);
      },
      facilities.find((facility) => facility.id === facilityId && facility.capabilityId === capabilityId) ??
        facilities.find((facility) => facility.id === facilityId) ??
        facilities[0],
    ),
  getVerificationQueue: () =>
    withServiceFallback(
      async () => (await request<BackendVerificationItem[]>("/verification/queue")).map(mapVerification),
      verificationItems,
    ),
  getExternalVerificationEvidence: (itemId: string) =>
    withServiceFallback(
      async () => {
        const value = await request<BackendExternalVerificationResult>(
          `/verification/items/${itemId}/external-evidence`,
          { method: "POST" },
        );
        return {
          mode: value.mode,
          query: value.query,
          results: value.results,
          limitation: value.limitation,
          traceId: value.trace_id,
        } satisfies ExternalVerificationResult;
      },
      {
        mode: "cached",
        query: "",
        results: [],
        limitation: "Cached mode made no external request.",
        traceId: `tavily:${itemId}`,
      },
    ),
  decideVerificationItem: async (
    item: VerificationItem,
    decision: VerificationItem["status"],
    reason: string,
  ) => {
    const backendStatus =
      decision === "resolved" ? "confirmed" : decision;
    return mapVerification(
      await request<BackendVerificationItem>(`/verification/items/${item.id}/decision`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
          status: backendStatus,
          reason: reason.trim() || "Reviewed in the Data Readiness Desk.",
          evidence_ids: [],
          expected_version: item.backendVersion ?? 1,
        }),
      }),
    );
  },
  listScenarios: () =>
    withServiceFallback(
      async () => (await request<BackendScenario[]>("/scenarios")).map(mapScenario),
      loadLocalScenarios(),
    ),
  saveScenario: async (
    scenario: Omit<Scenario, "id" | "createdAt" | "updatedAt" | "version" | "traceId" | "changeSummary">,
  ) =>
    mapScenario(
      await request<BackendScenario>("/scenarios", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
          name: scenario.name,
          capability_id: scenario.capabilityId,
          geography_id: scenario.geography,
          radius_km: scenario.radiusKm,
          selected_region_ids: scenario.selectedRegionIds,
          shortlisted_facility_ids: scenario.facilityIds,
          notes: scenario.notes,
          decision_rationale: scenario.notes,
          collaborators: [],
        }),
      }),
    ),
};
