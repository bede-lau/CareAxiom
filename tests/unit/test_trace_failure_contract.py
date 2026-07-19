from __future__ import annotations

from typing import Any

from medical_desert.application.services import MedicalDesertService


class FailingTracingAdapter:
    def trace_id(self) -> str:
        return "trace-correlation"

    def record(self, name: str, attributes: dict[str, Any]) -> str:
        del name, attributes
        raise RuntimeError("trace backend unavailable")


def test_trace_failure_returns_an_explicitly_unpersisted_correlation_id() -> None:
    service = object.__new__(MedicalDesertService)
    service.tracing = FailingTracingAdapter()
    service._trace_canary_id = None
    service._trace_error = None

    trace_id = service._record_trace("planner.decision", {"request_id": "request-1"})

    assert trace_id == "unpersisted:trace-correlation"
    assert service._trace_canary_id is None
    assert service._trace_error == "RuntimeError"
