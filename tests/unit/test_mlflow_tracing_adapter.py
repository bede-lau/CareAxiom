from __future__ import annotations

import sys
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from medical_desert.adapters.tracing import MLflowTracingAdapter, TracePersistenceError


def test_mlflow_adapter_flushes_trace_before_returning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    @contextmanager
    def start_span(*, name: str, attributes: dict[str, Any]) -> Any:
        events.append(f"start:{name}:{attributes['request_id']}")
        yield SimpleNamespace(trace_id="tr-managed")
        events.append("finish")

    class FakeMlflowClient:
        def get_trace(self, trace_id: str, *, display: bool) -> Any:
            events.append(f"get:{trace_id}:{display}")
            return SimpleNamespace(data=SimpleNamespace(spans=[object()]))

    fake_mlflow = SimpleNamespace(
        set_experiment=lambda name: events.append(f"experiment:{name}"),
        start_span=start_span,
        flush_trace_async_logging=lambda: events.append("flush"),
        MlflowClient=FakeMlflowClient,
    )
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    trace_id = MLflowTracingAdapter("/Shared/medical-desert").record(
        "planner.decision",
        {"request_id": "request-1"},
    )

    assert trace_id == "tr-managed"
    assert events == [
        "experiment:/Shared/medical-desert",
        "start:planner.decision:request-1",
        "finish",
        "flush",
        "get:tr-managed:False",
    ]


def test_mlflow_adapter_rejects_trace_without_persisted_span_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_trace_calls = 0

    @contextmanager
    def start_span(*, name: str, attributes: dict[str, Any]) -> Any:
        del name, attributes
        yield SimpleNamespace(trace_id="tr-missing")

    class FakeMlflowClient:
        def get_trace(self, trace_id: str, *, display: bool) -> Any:
            nonlocal get_trace_calls
            del trace_id, display
            get_trace_calls += 1
            raise RuntimeError("missing span data")

    fake_mlflow = SimpleNamespace(
        set_experiment=lambda name: None,
        start_span=start_span,
        flush_trace_async_logging=lambda: None,
        MlflowClient=FakeMlflowClient,
    )
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    adapter = MLflowTracingAdapter("/Shared/medical-desert")
    with pytest.raises(TracePersistenceError, match="could not reload persisted span data"):
        adapter.record(
            "planner.decision",
            {"request_id": "request-1"},
        )
    with pytest.raises(TracePersistenceError, match="could not reload persisted span data"):
        adapter.record(
            "planner.decision",
            {"request_id": "request-2"},
        )

    assert get_trace_calls == 1
