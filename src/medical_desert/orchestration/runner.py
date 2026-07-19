from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .contracts import PipelineContext, StageDefinition, StageResult
from .executor import DatabricksSqlExecutor, SparkSqlExecutor, SqlExecutor
from .sql import read_and_render, split_sql_statements, write_rendered_sql


class PipelineRunner:
    def __init__(self, context: PipelineContext) -> None:
        self.context = context

    def render(self, stage: StageDefinition) -> list[str]:
        path = self.context.repo_root / stage.sql_path
        return split_sql_statements(read_and_render(path, self.context.variables))

    def run(
        self,
        stage: StageDefinition,
        *,
        dry_run: bool,
        rendered_dir: Path | None = None,
    ) -> StageResult:
        statements = self.render(stage)
        rendered_path: Path | None = None
        if rendered_dir is not None:
            rendered_path = rendered_dir / f"{stage.stage_id}.sql"
            write_rendered_sql(rendered_path, statements)

        if dry_run:
            return StageResult(stage.stage_id, "DRY_RUN", len(statements), rendered_path)
        executor: SqlExecutor
        try:
            executor = SparkSqlExecutor()
        except (ImportError, RuntimeError) as error:
            if not self.context.warehouse_id:
                raise ValueError(
                    "--warehouse-id is required outside a Databricks Spark runtime"
                ) from error
            executor = DatabricksSqlExecutor(
                warehouse_id=self.context.warehouse_id,
                profile=self.context.profile,
            )
        statement_ids = tuple(executor.execute(sql).statement_id for sql in statements)
        return StageResult(
            stage.stage_id,
            "SUCCEEDED",
            len(statements),
            rendered_path,
            statement_ids,
        )

    def run_many(
        self,
        stages: Iterable[StageDefinition],
        *,
        dry_run: bool,
        rendered_dir: Path | None = None,
    ) -> list[StageResult]:
        return [self.run(stage, dry_run=dry_run, rendered_dir=rendered_dir) for stage in stages]
