from __future__ import annotations


def test_scenario_update_recomputes_saved_result_and_lineage(api_client) -> None:
    created = api_client.post(
        "/api/scenarios",
        headers={"Idempotency-Key": "scenario-recompute-create"},
        json={
            "name": "Maternal snapshot",
            "capability_id": "maternal_emergency_documentation",
            "geography_id": "district:br:darbhanga",
            "radius_km": 25,
            "selected_region_ids": ["district:br:darbhanga"],
            "notes": "Initial snapshot.",
            "decision_rationale": "Initial capability review.",
        },
    )
    assert created.status_code == 200
    current = created.json()

    updated = api_client.put(
        f"/api/scenarios/{current['scenario_id']}",
        headers={"Idempotency-Key": "scenario-recompute-update"},
        json={
            "name": "Surgery snapshot",
            "capability_id": "emergency_surgery_documentation",
            "geography_id": "district:br:darbhanga",
            "radius_km": 50,
            "selected_region_ids": ["district:br:darbhanga"],
            "notes": "Recomputed snapshot.",
            "decision_rationale": "Capability and radius changed.",
            "collaborators": [],
            "expected_version": current["version"],
        },
    )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["capability_id"] == "emergency_surgery_documentation"
    assert payload["radius_km"] == 50
    assert payload["saved_result"]["capability_id"] == "emergency_surgery_documentation"
    assert payload["saved_result"]["radius_km"] == 50
    assert payload["human_review_version"] == payload["saved_result"]["materialization_version"]
    assert payload["dataset_snapshot_id"] == payload["saved_result"]["source_bundle_id"]
