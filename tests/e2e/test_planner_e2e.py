from __future__ import annotations

import os

import pytest


def _base_url() -> str:
    value = os.getenv("E2E_BASE_URL")
    if not value:
        pytest.skip("E2E_BASE_URL is not configured")
    return value


@pytest.mark.e2e
@pytest.mark.gate("G4")
def test_planner_opens_facility_trust_desk() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(_base_url(), wait_until="networkidle")
        page.get_by_role("heading", name="Planner", exact=True).wait_for()
        page.get_by_text("Facility Trust Desk", exact=True).wait_for()
        browser.close()


@pytest.mark.e2e
@pytest.mark.gate("G4")
def test_nfhs_context_is_visually_labeled_as_separate_axis() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(_base_url(), wait_until="networkidle")
        page.get_by_text("Separate context axis", exact=True).wait_for()
        page.get_by_text("NFHS district context", exact=True).wait_for()
        browser.close()


@pytest.mark.e2e
@pytest.mark.gate("G5")
def test_scenario_can_be_saved_and_reopened() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(_base_url(), wait_until="networkidle")
        page.get_by_role("button", name="Save scenario").click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_label("Name").fill("E2E saved scenario")
        dialog.get_by_role("button", name="Save scenario").click()
        dialog.wait_for(state="hidden")
        page.get_by_role("button", name="Scenarios").click()
        page.get_by_role("heading", name="E2E saved scenario", exact=True).wait_for()
        browser.close()


@pytest.mark.e2e
@pytest.mark.gate("G7")
def test_referral_copilot_is_not_in_default_navigation() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(_base_url(), wait_until="networkidle")
        assert page.get_by_role("navigation").get_by_text("Referral Copilot").count() == 0
        browser.close()
