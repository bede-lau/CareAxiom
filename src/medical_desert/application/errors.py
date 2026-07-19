from __future__ import annotations

from typing import Any

from medical_desert.domain.models import ErrorCode


class ApplicationError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        recovery: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.recovery = recovery
        self.status_code = status_code
        self.details = details or {}
