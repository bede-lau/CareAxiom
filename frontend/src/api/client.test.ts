import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiClient } from "./client";

function jsonResponse(value: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(value), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function errorResponse(status: number, message: string) {
  return Promise.resolve(
    new Response(
      JSON.stringify({
        message,
        code: "SERVICE_UNAVAILABLE",
        recovery: "Retry after the service recovers.",
      }),
      {
        status,
        headers: { "Content-Type": "application/json" },
      },
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("apiClient backend DTO adapters", () => {
  it("maps Geography objects and preserves disabled city options", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        jsonResponse([
          {
            geography_id: "district:br:darbhanga",
            geography_type: "district",
            name: "Darbhanga",
            state: "Bihar",
            district: "Darbhanga",
            pin: null,
            selectable: true,
            unavailable_reason: null,
            metadata: {},
          },
          {
            geography_id: "city:darbhanga",
            geography_type: "city",
            name: "Darbhanga city",
            state: "Bihar",
            district: "Darbhanga",
            pin: null,
            selectable: false,
            unavailable_reason: "City normalization gate has not passed.",
            metadata: {},
          },
        ]),
      ),
    );

    const values = await apiClient.getGeographies();

    expect(values[0]).toMatchObject({
      id: "district:br:darbhanga",
      type: "district",
      selectable: true,
    });
    expect(values[1]).toMatchObject({
      id: "city:darbhanga",
      selectable: false,
      unavailableReason: "City normalization gate has not passed.",
    });
  });

  it("sends the backend documentary query contract and maps one result", async () => {
    const fetchMock = vi.fn((_input: RequestInfo | URL, _init?: RequestInit) =>
      jsonResponse({
        result_id: "result-live",
        capability_id: "maternal_emergency_documentation",
        geography: {
          geography_id: "district:br:darbhanga",
          geography_type: "district",
          name: "Darbhanga",
          state: "Bihar",
          district: "Darbhanga",
          pin: null,
          selectable: true,
          unavailable_reason: null,
          metadata: {},
        },
        radius_km: 25,
        classification: "low_nearby_documentary_support",
        classification_label: "Low nearby documentary support; external validation required",
        observed_record_assessability: {
          observed_record_assessability: 0.78,
          n_region_entities: 15,
          source_bundle_version: "bundle-live",
        },
        distinct_observed_facilities: 15,
        qualifying_facilities: 0,
        contradiction_count: 2,
        excluded_counts: { geography_conflict: 2 },
        facilities: [
          {
            facility_id: "b69b988a-1179-44df-8349-e0d632ebfb83",
            name: "Darbhanga Medical College",
            city: "Laheriasarai",
            district: "Darbhanga",
            state: "Bihar",
            pin: "846003",
            latitude: 26.17,
            longitude: 85.9,
            assessment: {
              facility_id: "b69b988a-1179-44df-8349-e0d632ebfb83",
              capability_id: "maternal_emergency_documentation",
              documentary_support_index: 42,
              support_band: "claim_only_or_weak",
              contradiction_state: "none",
              evidence_sufficiency: "limited",
              decision_readiness: "review_required",
              score_factors: null,
              missing_prerequisites: [],
              contradictions: [],
              evidence_ids: [],
              rule_version: "rule-live",
              machine_assessed_at: "2026-07-19T12:00:00Z",
              human_reviewed_verdict: null,
              human_review_reason: null,
              review_version: 0,
            },
            contribution_reason: "Observed record contributes documentary evidence within the radius.",
          },
        ],
        survey_context: null,
        planning_priority_candidate: true,
        external_validation_required: true,
        source_bundle_id: "bundle-live",
        policy_version: "policy-live",
        materialization_state: "failed",
        trace_id: "trace-live",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiClient.queryDocumentaryEvidence({
      capabilityId: "maternal_emergency_documentation",
      geography: "district:br:darbhanga",
      radiusKm: 25,
    });

    const requestBody = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(requestBody).toEqual({
      capability_id: "maternal_emergency_documentation",
      geography_id: "district:br:darbhanga",
      radius_km: 25,
      include_facilities: true,
    });
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      id: "district:br:darbhanga",
      documentaryState: "validation",
      observedFacilities: 15,
      supportedFacilities: 0,
      materializationState: "failed",
      traceId: "trace-live",
    });
    expect(result[0].facilityOptions[0].name).toBe("Darbhanga Medical College");
  });

  it("maps a backend location conflict and does not fabricate a source URL", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        jsonResponse({
          facility_id: "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
          name: "Lifecare Hospital",
          description: "Conflicting source geography.",
          city: "Siwan",
          district: "Darbhanga",
          state: "Bihar",
          pin: "846001",
          latitude: 26.1955,
          longitude: 84.3447,
          observed_fields: {
            quality_signals: [
              {
                code: "pin_coordinate_city_conflict",
                severity: "high",
                detail: "City is Siwan and longitude is 84.3447, inconsistent with the Darbhanga PIN-derived assignment.",
              },
            ],
          },
          assessments: [
            {
              facility_id: "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
              capability_id: "maternal_emergency_documentation",
              documentary_support_index: null,
              support_band: "insufficient_evidence",
              contradiction_state: "unresolved",
              evidence_sufficiency: "insufficient",
              decision_readiness: "abstain",
              score_factors: null,
              missing_prerequisites: ["Accepted geography assignment"],
              contradictions: [],
              evidence_ids: ["ev-conflict"],
              rule_version: "geo-rule-live",
              machine_assessed_at: "2026-07-19T12:00:00Z",
              human_reviewed_verdict: null,
              human_review_reason: null,
              review_version: 0,
            },
          ],
          review_history: [],
        }),
      )
      .mockImplementationOnce(() =>
        jsonResponse([
          {
            evidence_id: "ev-conflict",
            facility_id: "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
            capability_id: "maternal_emergency_documentation",
            source_field: "address_city, address_zipOrPostcode, longitude",
            exact_text: "City and coordinate conflict.",
            source_url: null,
            publisher: "Shared catalog",
            source_family: "virtue_facility_source",
            retrieval_time: "2026-07-19T12:00:00Z",
            extraction_method: "deterministic_validator",
            extraction_version: "0.2.0",
            entity_attribution_confidence: 0.91,
            polarity: "uncertain",
          },
        ]),
      );
    vi.stubGlobal("fetch", fetchMock);

    const facility = await apiClient.getFacility(
      "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
      "maternal_emergency_documentation",
    );

    expect(facility.locationConflict).toMatchObject({
      city: "Siwan",
      longitude: 84.3447,
      pinDistrict: "Darbhanga",
    });
    expect(facility.locationConflict?.disposition).toContain("Excluded from confident planning results");
    expect(facility.evidence[0].url).toBeNull();
  });

  it("preserves an unparseable survey qualifier", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        jsonResponse({
          district_id: "district:br:darbhanga",
          district: "Darbhanga",
          state: "Bihar",
          survey_context_availability: "matched",
          indicators: [
            {
              label: "Institutional births",
              raw_value: "not reported",
              numeric_value: null,
              qualifier: "unparseable",
              unit: "percent",
              survey_period: "2019-2021",
            },
          ],
          limitations: ["Malformed source value retained for review."],
        }),
      ),
    );

    const survey = await apiClient.getSurveyContext("district:br:darbhanga");

    expect(survey.metrics[0].qualifier).toBe("unparseable");
    expect(survey.metrics[0].rawValue).toBe("not reported");
  });

  it("does not fabricate a successful read after a service failure", async () => {
    vi.stubGlobal("fetch", vi.fn(() => errorResponse(503, "Warehouse unavailable")));

    await expect(apiClient.getCapabilities()).rejects.toBeInstanceOf(ApiError);
  });

  it("does not persist a local scenario when the write fails", async () => {
    vi.stubGlobal("fetch", vi.fn(() => errorResponse(503, "Operational store unavailable")));

    await expect(
      apiClient.saveScenario({
        name: "Failed write",
        capabilityId: "maternal_emergency_documentation",
        geography: "district:br:darbhanga",
        radiusKm: 25,
        selectedRegionIds: ["district:br:darbhanga"],
        facilityIds: [],
        notes: "Must remain unsaved.",
        sourceBundleId: "bundle",
        policyVersion: "policy",
        evidenceSnapshotId: "evidence",
      }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(localStorage.length).toBe(0);
  });
});
