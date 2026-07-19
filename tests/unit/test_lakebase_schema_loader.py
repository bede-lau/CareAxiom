from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from medical_desert.persistence.lakebase import (
    LakebaseOperationalStore,
    read_schema_statements,
)


def test_lakebase_schema_loader_ignores_semicolons_inside_comments(
    repo_root: Path,
) -> None:
    statements = read_schema_statements(repo_root / "sql" / "lakebase_schema.sql")

    assert statements
    assert "these PostgreSQL-compatible definitions shape Lakebase" in statements[0]
    assert "CREATE TABLE IF NOT EXISTS scenarios" in statements[0]
    assert all(not statement.lstrip().startswith("these PostgreSQL") for statement in statements)


def test_lakebase_connections_use_an_app_owned_schema() -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.executions: list[tuple[str, tuple[Any, ...] | list[Any]]] = []

        def execute(
            self,
            statement: str,
            parameters: tuple[Any, ...] | list[Any] = (),
        ) -> None:
            self.executions.append((statement, parameters))

    connection = FakeConnection()

    class FakePool:
        @contextmanager
        def connection(self) -> Any:
            yield connection

    store = object.__new__(LakebaseOperationalStore)
    store.schema = "medical_desert"
    store._pool = FakePool()

    with store._connection():
        pass

    assert connection.executions[:2] == [
        (
            'CREATE SCHEMA IF NOT EXISTS "medical_desert" AUTHORIZATION CURRENT_USER',
            (),
        ),
        ('SET search_path TO "medical_desert"', ()),
    ]


def test_lakebase_rejects_unsafe_schema_names() -> None:
    store = object.__new__(LakebaseOperationalStore)

    with pytest.raises(ValueError, match="simple SQL identifier"):
        LakebaseOperationalStore.__init__(
            store,
            host="example.database.databricks.com",
            database="databricks_postgres",
            endpoint_name="projects/example/branches/production",
            user="service-principal",
            schema="public; DROP SCHEMA public",
        )
