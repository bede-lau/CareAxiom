from __future__ import annotations

import csv
import io

import pytest


@pytest.fixture
def scenario_id(api_client) -> str:
    response = api_client.post(
        "/api/scenarios",
        headers={"Idempotency-Key": "export-contract-scenario"},
        json={
            "name": "Export contract scenario",
            "capability_id": "maternal_emergency_documentation",
            "geography_id": "district:br:darbhanga",
            "radius_km": 25,
            "selected_region_ids": ["district:br:darbhanga"],
            "notes": "Contract fixture created through the public API.",
            "decision_rationale": "Verify portable lineage exports.",
        },
    )
    assert response.status_code == 200
    return str(response.json()["scenario_id"])


@pytest.mark.contract
@pytest.mark.gate("G5")
def test_scenario_json_export_contains_required_lineage_fields(
    api_client, load_fixture, scenario_id: str
) -> None:
    contract = load_fixture("fixtures/contracts/export_contract_core.json")
    response = api_client.get(f"/api/scenarios/{scenario_id}/export.json")
    assert response.status_code == 200
    assert set(contract["required_json_fields"]).issubset(response.json())


@pytest.mark.contract
@pytest.mark.gate("G5")
def test_scenario_csv_export_contains_required_lineage_columns(
    api_client, load_fixture, scenario_id: str
) -> None:
    contract = load_fixture("fixtures/contracts/export_contract_core.json")
    response = api_client.get(f"/api/scenarios/{scenario_id}/export.csv")
    assert response.status_code == 200
    columns = next(csv.reader(io.StringIO(response.text)))
    assert set(contract["required_csv_columns"]).issubset(columns)
