from __future__ import annotations

import importlib
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))


def pytest_configure(config: pytest.Config) -> None:
    markers = {
        "contract": "frozen source or API contract verification",
        "connected": "requires configured external credentials or deployed resources",
        "e2e": "browser end-to-end verification",
        "hypothesis": "property-based verification",
        "integration": "cross-component offline integration verification",
        "gate(name)": "G0-G7 release gate association",
    }
    for marker, description in markers.items():
        config.addinivalue_line("markers", f"{marker}: {description}")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def load_fixture():
    def _load(relative_path: str) -> Any:
        with (ROOT / relative_path).open(encoding="utf-8") as handle:
            return json.load(handle)

    return _load


def import_first(candidates: Iterable[str]):
    errors: list[str] = []
    for name in candidates:
        try:
            return importlib.import_module(name)
        except ModuleNotFoundError as exc:
            errors.append(f"{name}: {exc}")
    pytest.skip("Production module not available: " + "; ".join(errors))


def require_callable(modules: Iterable[Any], names: Iterable[str]):
    for module in modules:
        for name in names:
            value = getattr(module, name, None)
            if callable(value):
                return value
    pytest.skip(f"Production callable not available; expected one of {list(names)}")


@pytest.fixture(scope="session")
def production_app():
    override = os.getenv("CAREAXIOM_APP")
    candidates = [
        override,
        "medical_desert.api.main:app",
        "medical_desert.api.app:app",
        "medical_desert.main:app",
        "src.medical_desert.api.main:app",
        "app.main:app",
        "main:app",
    ]
    errors: list[str] = []
    for candidate in filter(None, candidates):
        module_name, _, symbol = candidate.partition(":")
        symbol = symbol or "app"
        try:
            module = importlib.import_module(module_name)
            app = getattr(module, symbol)
        except (ModuleNotFoundError, AttributeError) as exc:
            errors.append(f"{candidate}: {exc}")
            continue
        return app
    pytest.skip("FastAPI application not available: " + "; ".join(errors))


@pytest.fixture(scope="session")
def api_client(production_app):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    with TestClient(production_app) as client:
        yield client
