export type CapabilityId =
  | "maternal_emergency_documentation"
  | "emergency_surgery_documentation"
  | "advanced_imaging_documentation";

export type DocumentaryState =
  | "strong"
  | "low"
  | "validation"
  | "mixed"
  | "insufficient"
  | "unavailable";

export type HealthState = "healthy" | "degraded" | "unavailable";

export interface Capability {
  id: CapabilityId;
  label: string;
  shortLabel: string;
  description: string;
}

export interface GeographyOption {
  id: string;
  type: "state" | "district" | "city" | "pin" | "map_area";
  name: string;
  state?: string;
  district?: string;
  pin?: string;
  selectable: boolean;
  unavailableReason?: string;
}

export interface RegionResult {
  id: string;
  name: string;
  district: string;
  state: string;
  pin: string;
  x: number;
  y: number;
  stateCode: string;
  documentaryState: DocumentaryState;
  documentaryLabel: string;
  supportedFacilities: number;
  observedFacilities: number;
  assessability: number;
  priority: number;
  postalMethod: string;
  postalAmbiguity: string;
  dispersionKm: number;
  materializationState: "applied" | "pending" | "failed" | "blocked_dependency";
  traceId: string;
  facilityOptions: Array<{
    id: string;
    name: string;
    contributionReason: string;
  }>;
}

export interface Evidence {
  id: string;
  polarity: "supporting" | "contradicting" | "unknown";
  text: string;
  sourceField: string;
  publisher: string;
  sourceFamily: string;
  url: string | null;
  retrievedAt: string;
  extractionVersion: string;
}

export interface Facility {
  id: string;
  name: string;
  location: string;
  capabilityId: CapabilityId;
  machineVerdict: string;
  humanVerdict?: string;
  supportIndex: number | null;
  supportBand: string;
  contradictionState: "none" | "unresolved" | "confirmed";
  freshness: string;
  attributionConfidence: number;
  missingPrerequisites: string[];
  locationConflict?: {
    city: string;
    longitude: number;
    pinDistrict: string;
    disposition: string;
  };
  factors: Array<{ label: string; value: number; max: number }>;
  evidence: Evidence[];
  history: Array<{ actor: string; action: string; time: string; reason: string }>;
}

export interface SurveyMetric {
  label: string;
  value: string;
  rawValue: string;
  qualifier: "standard" | "low_sample_25_49" | "suppressed_lt_25" | "unparseable";
}

export interface SurveyContext {
  district: string;
  state: string;
  period: string;
  availability: "matched" | "crosswalked" | "unavailable";
  metrics: SurveyMetric[];
  householdsSurveyed: number | null;
  note: string;
}

export interface VerificationItem {
  id: string;
  facilityId: string;
  facilityName: string;
  issue: string;
  whyItMatters: string;
  capability: string;
  region: string;
  priority: number;
  affectedRegions: number;
  scenarioReferences: number;
  ageDays: number;
  status: "open" | "in_review" | "deferred" | "resolved" | "unresolved";
  traceId: string;
  flag?: "location_conflict" | "evidence_gap" | "contradiction";
  backendVersion?: number;
}

export interface ExternalEvidence {
  url: string;
  title: string | null;
  excerpt: string | null;
  score: number | null;
}

export interface ExternalVerificationResult {
  mode: "cached" | "live";
  query: string;
  results: ExternalEvidence[];
  limitation: string;
  traceId: string;
}

export interface Scenario {
  id: string;
  name: string;
  capabilityId: CapabilityId;
  geography: string;
  radiusKm: number;
  selectedRegionIds: string[];
  facilityIds: string[];
  notes: string;
  createdAt: string;
  updatedAt: string;
  version: number;
  sourceBundleId: string;
  policyVersion: string;
  evidenceSnapshotId: string;
  traceId: string;
  changeSummary: Array<{
    field: string;
    prior: string;
    current: string;
    reason: string;
  }>;
}

export interface HealthResponse {
  state: HealthState;
  traceId: string;
  snapshotVersion: string;
  components: Array<{
    name: string;
    state: HealthState;
    detail: string;
  }>;
}

export interface DocumentaryQuery {
  capabilityId: CapabilityId;
  geography: string;
  radiusKm: number;
}
