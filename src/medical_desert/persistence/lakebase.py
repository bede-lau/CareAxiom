from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from medical_desert.persistence.sqlite import SQLiteOperationalStore


class _PostgresCompatibilityConnection:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    @staticmethod
    def _statement(value: str) -> str:
        if value.strip().upper() == "BEGIN IMMEDIATE":
            return "BEGIN"
        return value.replace("?", "%s")

    def execute(self, statement: str, parameters: tuple[Any, ...] | list[Any] = ()) -> Any:
        return self.connection.execute(self._statement(statement), parameters)

    def commit(self) -> None:
        self.connection.commit()


class LakebaseOperationalStore(SQLiteOperationalStore):
    def __init__(
        self,
        *,
        host: str,
        database: str,
        endpoint_name: str,
        user: str | None = None,
        port: int = 5432,
        sslmode: str = "require",
        schema_path: Path = Path("sql/lakebase_schema.sql"),
    ) -> None:
        super().__init__(Path("lakebase"))
        self.host = host
        self.database = database
        self.endpoint_name = endpoint_name
        self.user = user or os.environ.get("DATABRICKS_CLIENT_ID")
        self.port = port
        self.sslmode = sslmode
        self.schema_path = schema_path
        if not self.user:
            raise ValueError("Lakebase requires a database user or DATABRICKS_CLIENT_ID.")
        self._pool = self._build_pool()

    @property
    def backend_name(self) -> str:
        return f"Lakebase database {self.database} at {self.host}"

    def _build_pool(self) -> Any:
        import psycopg
        from databricks.sdk import WorkspaceClient
        from psycopg.rows import dict_row
        from psycopg.types.json import set_json_loads
        from psycopg_pool import ConnectionPool

        workspace = WorkspaceClient()
        endpoint_name = self.endpoint_name

        class OAuthConnection(psycopg.Connection):
            @classmethod
            def connect(cls, conninfo: str = "", **kwargs: Any) -> Any:
                credential = workspace.postgres.generate_database_credential(
                    endpoint=endpoint_name
                )
                kwargs["password"] = credential.token
                connection = super().connect(conninfo, **kwargs)
                set_json_loads(
                    lambda value: value.decode() if isinstance(value, bytes) else value,
                    connection,
                )
                return connection

        conninfo = (
            f"dbname={self.database} user={self.user} host={self.host} "
            f"port={self.port} sslmode={self.sslmode}"
        )
        return ConnectionPool(
            conninfo=conninfo,
            connection_class=OAuthConnection,
            kwargs={"row_factory": dict_row},
            min_size=1,
            max_size=10,
            open=False,
        )

    @contextmanager
    def _connection(self) -> Generator[Any, None, None]:
        with self._pool.connection() as connection:
            yield _PostgresCompatibilityConnection(connection)

    def initialize(self) -> None:
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Lakebase schema not found: {self.schema_path}")
        self._pool.open(wait=True)
        statements = [
            statement.strip()
            for statement in self.schema_path.read_text(encoding="utf-8").split(";")
            if statement.strip()
        ]
        with self._connection() as connection:
            for statement in statements:
                connection.execute(statement)
            connection.commit()
