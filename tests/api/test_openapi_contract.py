from __future__ import annotations

import pytest


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_openapi_exposes_health_and_core_planner_routes(production_app) -> None:
    paths = production_app.openapi()["paths"]
    assert "/api/health" in paths or "/health" in paths
    assert any("documentary" in path for path in paths)
    assert any("facilit" in path for path in paths)
    assert any("scenario" in path for path in paths)


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_openapi_uses_canonical_documentary_field_names(production_app) -> None:
    schema = production_app.openapi()
    serialized = str(schema)
    for field in (
        "documentary_support_index",
        "observed_record_assessability",
        "survey_context_availability",
        "materialization_state",
    ):
        assert field in serialized


@pytest.mark.contract
@pytest.mark.gate("G7")
def test_openapi_referral_route_is_absent_when_default_off(production_app) -> None:
    paths = production_app.openapi()["paths"]
    assert not any("referral" in path.lower() for path in paths)
