from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from medical_desert.domain.models import IdentityMode, ProductRole


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDICAL_DESERT_",
        env_file=".env",
        extra="ignore",
    )

    environment: str = "local"
    database_path: Path = Path(".medical_desert/operational.db")
    identity_mode: IdentityMode = IdentityMode.SINGLE_TEAM_DEMO
    demo_actor_id: str = "demo-planner"
    demo_actor_name: str = "CareAxiom Demo Planner"
    full_rbac_role_assignments: dict[str, list[ProductRole]] = Field(default_factory=dict)
    crisis_enabled: bool = False
    referral_enabled: bool = False
    databricks_enabled: bool = False
    databricks_server_hostname: str | None = None
    databricks_http_path: str | None = None
    databricks_access_token: str | None = Field(default=None, repr=False)
    project_catalog: str = Field(
        default="medical_desert",
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    )
    analytical_source_bundle_id: str = "virtue-dais-2026-profiled-2026-07-19"
    policy_version: str = "documentary-policy-v1"
    scoring_version: str = "documentary-policy-v1"
    focus_state: str = "Bihar"
    focus_district: str = "Darbhanga"
    lakebase_enabled: bool = False
    lakebase_host: str | None = None
    lakebase_database: str = "databricks_postgres"
    lakebase_user: str | None = None
    lakebase_port: int = 5432
    lakebase_sslmode: str = "require"
    lakebase_endpoint_name: str | None = None
    mlflow_enabled: bool = False
    mlflow_experiment_name: str = "/Shared/medical-desert-planner"
    tavily_mode: str = "cached"
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY", repr=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def load_yaml_config(name: str) -> dict[str, Any]:
    path = Path("config") / name
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value
