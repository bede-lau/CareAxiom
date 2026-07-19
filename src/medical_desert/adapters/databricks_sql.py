from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlparse


class DatabricksSQLAdapter:
    def __init__(
        self,
        server_hostname: str | None,
        http_path: str,
        access_token: str | None = None,
    ) -> None:
        self.server_hostname = server_hostname
        self.http_path = http_path
        self._access_token = access_token

    @staticmethod
    def _hostname(value: str) -> str:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        return parsed.hostname or value

    @contextmanager
    def connection(self) -> Iterator[Any]:
        from databricks import sql

        if self._access_token:
            if not self.server_hostname:
                raise ValueError("A server hostname is required with token authentication.")
            connection = sql.connect(
                server_hostname=self._hostname(self.server_hostname),
                http_path=self.http_path,
                access_token=self._access_token,
            )
        else:
            from databricks.sdk.core import Config

            config = Config(host=self.server_hostname) if self.server_hostname else Config()
            if not config.host:
                raise ValueError("Databricks App OAuth did not provide a workspace host.")
            connection = sql.connect(
                server_hostname=self._hostname(config.host),
                http_path=self.http_path,
                credentials_provider=lambda: config.authenticate,
            )
        try:
            yield connection
        finally:
            connection.close()

    def fetch_all(
        self, statement: str, parameters: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        self._validate_statement(statement)
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement, parameters or [])
                columns = [item[0] for item in cursor.description]
                return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def execute(self, statement: str, parameters: list[Any] | None = None) -> None:
        self._validate_statement(statement)
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement, parameters or [])

    @staticmethod
    def _validate_statement(statement: str) -> None:
        if ";" in statement.rstrip(";"):
            raise ValueError("Only one parameterized statement is allowed.")
