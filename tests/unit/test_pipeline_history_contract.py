from __future__ import annotations

from pathlib import Path


def test_pipeline_materializations_preserve_other_source_bundles(repo_root: Path) -> None:
    sql_files = sorted((repo_root / "pipelines" / "sql").glob("*.sql"))
    materialization_sql = "\n".join(path.read_text(encoding="utf-8") for path in sql_files)

    assert "CREATE OR REPLACE TABLE" not in materialization_sql
    for path in sql_files[1:]:
        text = path.read_text(encoding="utf-8")
        for statement in text.split(";"):
            if statement.lstrip().upper().startswith("DELETE FROM"):
                assert "source_bundle_id" in statement, (
                    f"{path.name} has an unscoped DELETE that could erase bundle history"
                )
