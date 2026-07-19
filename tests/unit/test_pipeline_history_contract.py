from __future__ import annotations

from pathlib import Path

import yaml


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


def test_serverless_job_does_not_import_the_repository_as_a_dependency(
    repo_root: Path,
) -> None:
    jobs = yaml.safe_load((repo_root / "resources" / "jobs.yml").read_text(encoding="utf-8"))
    environments = jobs["resources"]["jobs"]["recalculation"]["environments"]

    for environment in environments:
        spec = environment["spec"]
        assert spec["environment_version"] == "5"
        assert "client" not in spec
        dependencies = spec.get("dependencies", [])
        assert not {".", "..", "./", "../"}.intersection(dependencies)
