from __future__ import annotations

from typing import Any
from uuid import uuid4


class TracePersistenceError(RuntimeError):
    pass


class NoopTracingAdapter:
    def trace_id(self) -> str:
        return f"trace-{uuid4()}"

    def record(self, name: str, attributes: dict[str, Any]) -> str:
        del name, attributes
        return self.trace_id()


class MLflowTracingAdapter:
    def __init__(self, experiment_name: str) -> None:
        self.experiment_name = experiment_name
        self._persistence_error: TracePersistenceError | None = None

    def trace_id(self) -> str:
        return f"trace-{uuid4()}"

    def record(self, name: str, attributes: dict[str, Any]) -> str:
        import mlflow

        if self._persistence_error is not None:
            raise self._persistence_error
        mlflow.set_experiment(self.experiment_name)
        with mlflow.start_span(name=name, attributes=attributes) as span:
            trace_id = str(span.trace_id)
        mlflow.flush_trace_async_logging()
        try:
            persisted_trace = mlflow.MlflowClient().get_trace(trace_id, display=False)
        except Exception as error:
            self._persistence_error = TracePersistenceError(
                f"MLflow could not reload persisted span data for {trace_id}."
            )
            raise self._persistence_error from error
        if not persisted_trace.data.spans:
            self._persistence_error = TracePersistenceError(
                f"MLflow returned no persisted spans for {trace_id}."
            )
            raise self._persistence_error
        return trace_id
