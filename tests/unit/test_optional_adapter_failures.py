from __future__ import annotations

import pytest

from medical_desert.config.settings import Settings


@pytest.mark.gate("G6")
def test_tavily_defaults_to_cached_mode_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.tavily_mode == "cached"
    assert settings.tavily_api_key is None


@pytest.mark.contract
@pytest.mark.gate("G6")
def test_optional_failure_fixture_defines_deterministic_fallbacks(load_fixture) -> None:
    fixture = load_fixture("fixtures/contracts/optional_adapter_failures.json")
    assert {case["adapter"] for case in fixture["cases"]} >= {
        "tavily",
        "ai_search",
        "model_serving",
        "lakebase",
        "recalculation_job",
    }
