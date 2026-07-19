from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_pipeline
from scripts.run_pipeline import resolve_repo_root


def test_pipeline_entrypoint_uses_argv_when_databricks_omits_dunder_file(
    tmp_path: Path,
) -> None:
    entrypoint = tmp_path / "scripts" / "run_pipeline.py"

    assert resolve_repo_root(None, [str(entrypoint)]) == tmp_path


def test_pipeline_entrypoint_finds_bundle_root_from_working_directory(
    tmp_path: Path,
) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run_pipeline.py").touch()
    (tmp_path / "databricks.yml").touch()
    working_directory = tmp_path / "pipelines" / "sql"
    working_directory.mkdir(parents=True)

    assert resolve_repo_root(None, [], working_directory) == tmp_path


def test_successful_pipeline_entrypoint_returns_normally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_pipeline, "main", lambda: 0)

    assert run_pipeline.run_entrypoint() is None


def test_failed_pipeline_entrypoint_raises_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_pipeline, "main", lambda: 7)

    with pytest.raises(SystemExit) as exc_info:
        run_pipeline.run_entrypoint()

    assert exc_info.value.code == 7
