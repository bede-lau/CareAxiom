from __future__ import annotations

from pathlib import Path

import yaml


def test_databricks_app_keeps_managed_mlflow_ready_but_off_the_request_path(
    repo_root: Path,
) -> None:
    config = yaml.safe_load(
        (repo_root / "resources" / "app.yml").read_text(encoding="utf-8")
    )
    app = config["resources"]["apps"]["medical_desert_planner"]
    environment = {
        item["name"]: item.get("value")
        for item in app["config"]["env"]
        if "value" in item
    }

    assert environment["MEDICAL_DESERT_MLFLOW_ENABLED"] == "false"
    assert environment["MLFLOW_TRACKING_URI"] == "databricks"
    assert environment["MLFLOW_HTTP_REQUEST_TIMEOUT"] == "5"
    assert environment["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] == "0"
    assert environment["MLFLOW_ASYNC_TRACE_LOGGING_RETRY_TIMEOUT"] == "5"
    assert environment["MEDICAL_DESERT_MLFLOW_EXPERIMENT_NAME"].startswith("/Shared/")
    assert any(resource["name"] == "mlflow-experiment" for resource in app["resources"])
