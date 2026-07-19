from __future__ import annotations

from typing import Any
from uuid import uuid4


class NoopTracingAdapter:
    def trace_id(self) -> str:
        return f"trace-{uuid4()}"

    def record(self, name: str, attributes: dict[str, Any]) -> str:
        del name, attributes
        return self.trace_id()


class MLflowTracingAdapter:
    def __init__(self, experiment_name: str) -> None:
        self.experiment_name = experiment_name

    def trace_id(self) -> str:
        return f"trace-{uuid4()}"

    def record(self, name: str, attributes: dict[str, Any]) -> str:
        import mlflow

        mlflow.set_experiment(self.experiment_name)
        with mlflow.start_span(name=name, attributes=attributes) as span:
            return str(span.trace_id)
