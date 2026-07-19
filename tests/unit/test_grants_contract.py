from __future__ import annotations

from pathlib import Path


def test_app_grants_cover_runtime_reads_and_materialization(repo_root: Path) -> None:
    grants = (repo_root / "sql" / "grants.sql").read_text(encoding="utf-8")

    assert (
        "GRANT SELECT ON TABLE {{project_catalog}}.bronze.facility_source_snapshot"
        in grants
    )
    assert (
        "GRANT SELECT ON SCHEMA {{project_catalog}}.silver"
        " TO `{{app_service_principal}}`;"
    ) in grants
    assert (
        "GRANT SELECT ON SCHEMA {{project_catalog}}.gold"
        " TO `{{app_service_principal}}`;"
    ) in grants
    assert (
        "GRANT MODIFY ON TABLE {{project_catalog}}.gold.facility_review_overlay"
        in grants
    )
    assert (
        "GRANT MODIFY ON TABLE "
        "{{project_catalog}}.gold.operational_event_materialization"
    ) in grants
