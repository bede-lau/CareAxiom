from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from medical_desert.orchestration.contracts import PipelineContext, StageDefinition  # noqa: E402
from medical_desert.orchestration.registry import STAGES, get_stage  # noqa: E402
from medical_desert.orchestration.runner import PipelineRunner  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render or execute the Medical Desert Planner pipeline."
    )
    parser.add_argument(
        "stage",
        help="Stage number/id, comma-separated list, range such as 0-6, or 'all'.",
    )
    parser.add_argument("--execute", action="store_true", help="Execute rendered SQL.")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Render or execute canonical project DDL before selected stages.",
    )
    parser.add_argument("--warehouse-id")
    parser.add_argument("--profile", default="careaxiom")
    parser.add_argument("--project-catalog", default="medical_desert")
    parser.add_argument(
        "--source-catalog",
        default="databricks_virtue_foundation_dataset_dais_2026",
    )
    parser.add_argument("--source-schema", default="virtue_foundation_dataset")
    parser.add_argument("--source-bundle-id", default="virtue-dais-2026-20260719")
    parser.add_argument("--policy-version", default="documentary-policy-v1")
    parser.add_argument("--geography-version", default="postal-median-v1")
    parser.add_argument(
        "--rendered-dir",
        type=Path,
        default=REPO_ROOT / ".dist" / "rendered-sql",
    )
    return parser.parse_args()


def select_stages(value: str) -> tuple[StageDefinition, ...]:
    if value == "all":
        return STAGES
    selected: list[StageDefinition] = []
    for token in value.split(","):
        token = token.strip()
        if "-" in token and token.replace("-", "").isdigit():
            start, end = (int(part) for part in token.split("-", 1))
            selected.extend(get_stage(number) for number in range(start, end + 1))
        else:
            selected.append(get_stage(token))
    return tuple(dict.fromkeys(selected))


def main() -> int:
    args = parse_args()
    context = PipelineContext(
        project_catalog=args.project_catalog,
        source_catalog=args.source_catalog,
        source_schema=args.source_schema,
        source_bundle_id=args.source_bundle_id,
        policy_version=args.policy_version,
        geography_version=args.geography_version,
        warehouse_id=args.warehouse_id,
        profile=args.profile,
        repo_root=REPO_ROOT,
    )
    runner = PipelineRunner(context)
    bootstrap_result = None
    if args.bootstrap:
        bootstrap_result = runner.run(
            StageDefinition(
                -1,
                "bootstrap_contracts",
                "Create project-owned schemas, tables, and views.",
                "sql/unity_catalog_tables.sql",
            ),
            dry_run=not args.execute,
            rendered_dir=args.rendered_dir,
        )
    results = runner.run_many(
        select_stages(args.stage),
        dry_run=not args.execute,
        rendered_dir=args.rendered_dir,
    )
    print(
        json.dumps(
            [
                {
                    "stage_id": result.stage_id,
                    "status": result.status,
                    "statement_count": result.statement_count,
                    "rendered_sql_path": (
                        str(result.rendered_sql_path)
                        if result.rendered_sql_path
                        else None
                    ),
                    "statement_ids": result.statement_ids,
                }
                for result in ([bootstrap_result] if bootstrap_result else []) + results
            ],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
