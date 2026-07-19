from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PipelineContext:
    project_catalog: str
    source_catalog: str
    source_schema: str
    source_bundle_id: str
    policy_version: str
    geography_version: str
    warehouse_id: str | None = None
    profile: str = "careaxiom"
    repo_root: Path = field(default_factory=lambda: Path.cwd())

    @property
    def variables(self) -> Mapping[str, str]:
        return {
            "project_catalog": self.project_catalog,
            "source_catalog": self.source_catalog,
            "source_schema": self.source_schema,
            "source_bundle_id": self.source_bundle_id,
            "policy_version": self.policy_version,
            "geography_version": self.geography_version,
        }


@dataclass(frozen=True)
class StageDefinition:
    number: int
    slug: str
    description: str
    sql_path: str
    depends_on: tuple[int, ...] = ()
    validation_sql_path: str | None = None

    @property
    def stage_id(self) -> str:
        return f"{self.number:02d}_{self.slug}"


@dataclass(frozen=True)
class StageResult:
    stage_id: str
    status: str
    statement_count: int
    rendered_sql_path: Path | None = None
    statement_ids: tuple[str, ...] = ()
