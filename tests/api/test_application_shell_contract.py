from __future__ import annotations

import pytest


@pytest.mark.contract
@pytest.mark.gate("G4")
def test_packaged_application_serves_the_frontend_shell(api_client) -> None:
    response = api_client.get("/")
    assert response.status_code == 200
    assert "<title>CareAxiom</title>" in response.text
    assert 'id="root"' in response.text
