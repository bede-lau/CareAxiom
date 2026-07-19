from __future__ import annotations

import pytest


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_health_identifies_medical_desert_planner(api_client) -> None:
    response = api_client.get("/api/health")
    if response.status_code == 404:
        response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["product"] == "Medical Desert Planner"


@pytest.mark.contract
@pytest.mark.gate("G6")
def test_health_reports_optional_services_without_fabricating_healthy_state(api_client) -> None:
    response = api_client.get("/api/health")
    if response.status_code == 404:
        response = api_client.get("/health")
    components = response.json()["components"]
    for name in ("tavily", "ai_search"):
        if name in components:
            assert components[name]["status"] in {"healthy", "degraded", "disabled", "unavailable"}
