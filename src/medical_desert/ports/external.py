from __future__ import annotations

from typing import Any, Protocol


class WebVerificationPort(Protocol):
    def search(self, query: str, domains: list[str] | None = None) -> list[dict[str, Any]]: ...


class TracingPort(Protocol):
    def trace_id(self) -> str: ...

    def record(self, name: str, attributes: dict[str, Any]) -> str: ...


class SQLQueryPort(Protocol):
    def execute(self, statement: str, parameters: list[Any] | None = None) -> None: ...

    def fetch_all(
        self, statement: str, parameters: list[Any] | None = None
    ) -> list[dict[str, Any]]: ...
