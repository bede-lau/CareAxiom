from __future__ import annotations

from pathlib import Path

import pytest

from medical_desert.config.settings import Settings


@pytest.mark.gate("G7")
def test_referral_copilot_is_disabled_by_default() -> None:
    assert Settings().referral_enabled is False


@pytest.mark.gate("G4")
def test_frontend_declares_careaxiom_with_planner_as_default_view(repo_root: Path) -> None:
    app = (repo_root / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "<strong>CareAxiom</strong>" in app
    assert 'useState<ViewId>("planner")' in app


@pytest.mark.gate("G4")
def test_facility_trust_desk_is_embedded_in_planner(repo_root: Path) -> None:
    app = (repo_root / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "Facility Trust Desk" in app
    assert "<TrustDesk" in app


@pytest.mark.gate("G4")
def test_data_readiness_is_supporting_navigation_not_default_route(repo_root: Path) -> None:
    app = (repo_root / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "Data Readiness Desk" in app
    assert 'useState<ViewId>("planner")' in app


@pytest.mark.gate("G7")
def test_referral_copilot_is_absent_from_default_navigation(repo_root: Path) -> None:
    app = (repo_root / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    navigation_block = app.split("const navigation =", maxsplit=1)[1].split("];", maxsplit=1)[0]
    assert "Referral" not in navigation_block
