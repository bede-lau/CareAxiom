from __future__ import annotations

import pytest


@pytest.mark.contract
@pytest.mark.gate("G6")
def test_external_verification_is_cached_and_user_triggered_by_default(api_client) -> None:
    queue = api_client.get("/api/verification/queue")
    assert queue.status_code == 200
    item_id = queue.json()[0]["item_id"]

    response = api_client.post(f"/api/verification/items/{item_id}/external-evidence")

    assert response.status_code == 200
    assert response.json()["mode"] == "cached"
    assert response.json()["results"] == []
    assert response.json()["limitation"] == "Cached mode made no external request."
