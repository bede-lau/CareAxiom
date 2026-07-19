from __future__ import annotations

import os

import pytest


def _credentials() -> tuple[str, str, str]:
    values = (
        os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        os.getenv("DATABRICKS_HTTP_PATH"),
        os.getenv("DATABRICKS_TOKEN"),
    )
    if not all(values):
        pytest.skip("Databricks credentials are not configured")
    return values  # type: ignore[return-value]


@pytest.mark.connected
@pytest.mark.gate("G0")
def test_live_catalog_row_counts_match_frozen_source_contract(load_fixture) -> None:
    dbsql = pytest.importorskip("databricks.sql")
    hostname, http_path, token = _credentials()
    fixture = load_fixture("fixtures/contracts/source_bundle_contract_core.json")
    catalog = fixture["catalog"]
    schema = fixture["schema"]
    with dbsql.connect(
        server_hostname=hostname,
        http_path=http_path,
        access_token=token,
    ) as connection:
        with connection.cursor() as cursor:
            for table, expected in fixture["tables"].items():
                cursor.execute(f"SELECT COUNT(*) FROM {catalog}.{schema}.{table}")
                assert cursor.fetchone()[0] == expected["rows"]
