from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast


@dataclass(frozen=True)
class StatementExecution:
    statement_id: str
    state: str


class SqlExecutor(Protocol):
    def execute(self, statement: str) -> StatementExecution: ...


class DatabricksSqlExecutor:
    def __init__(
        self,
        warehouse_id: str,
        profile: str,
        *,
        cli_path: str = "databricks",
        timeout_seconds: int = 900,
        poll_seconds: float = 2.0,
    ) -> None:
        self.warehouse_id = warehouse_id
        self.profile = profile
        self.cli_path = cli_path
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds

    def execute(self, statement: str) -> StatementExecution:
        payload: dict[str, object] = {
            "warehouse_id": self.warehouse_id,
            "statement": statement,
            "wait_timeout": "50s",
            "on_wait_timeout": "CONTINUE",
            "disposition": "INLINE",
            "format": "JSON_ARRAY",
        }
        response = self._api("post", "/api/2.0/sql/statements", payload)
        deadline = time.monotonic() + self.timeout_seconds
        status = cast(dict[str, Any], response["status"])
        while status["state"] in {"PENDING", "RUNNING"}:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Databricks statement {response['statement_id']} exceeded "
                    f"{self.timeout_seconds} seconds"
                )
            time.sleep(self.poll_seconds)
            response = self._api("get", f"/api/2.0/sql/statements/{response['statement_id']}")
            status = cast(dict[str, Any], response["status"])

        state = str(status["state"])
        if state != "SUCCEEDED":
            error = cast(dict[str, Any], status.get("error", {}))
            raise RuntimeError(
                f"Databricks statement {response['statement_id']} failed: "
                f"{error.get('error_code', state)} {error.get('message', '')}".strip()
            )
        return StatementExecution(str(response["statement_id"]), state)

    def _api(
        self, method: str, endpoint: str, payload: dict[str, object] | None = None
    ) -> dict[str, object]:
        command = [
            self.cli_path,
            "api",
            method,
            endpoint,
            "--profile",
            self.profile,
            "--output",
            "json",
        ]
        temp_path: Path | None = None
        try:
            if payload is not None:
                handle, raw_path = tempfile.mkstemp(suffix=".json")
                os.close(handle)
                temp_path = Path(raw_path)
                temp_path.write_text(json.dumps(payload), encoding="utf-8")
                command.extend(["--json", f"@{temp_path}"])
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
            return cast(dict[str, object], json.loads(completed.stdout))
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)


class SparkSqlExecutor:
    def __init__(self) -> None:
        SparkSession = import_module("pyspark.sql").SparkSession
        self.spark = SparkSession.builder.getOrCreate()

    def execute(self, statement: str) -> StatementExecution:
        self.spark.sql(statement).collect()
        return StatementExecution("spark-sql", "SUCCEEDED")
