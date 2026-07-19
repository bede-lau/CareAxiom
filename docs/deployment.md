# Deployment Runbook

## External Resources

Create or identify these before deployment:

- A writable Unity Catalog project catalog, normally `medical_desert`.
- The existing Serverless SQL warehouse and its HTTP path.
- A Lakebase Autoscaling branch, database, endpoint resource name, and host.
- A Databricks secret scope containing `TAVILY_API_KEY`.
- The workspace group allowed to open the single-team hackathon app.

The source catalog remains read-only:
`databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset`.

## Access

The bundle gives the app service principal resource-level access to the warehouse,
Lakebase database, recalculation Job, MLflow experiment, and Tavily secret.

Grant the deployment or Job principal `SELECT` on the three shared source tables and
`USE CATALOG`, `USE SCHEMA`, `CREATE TABLE`, `SELECT`, and `MODIFY` across the project
catalog schemas. Grant the app service principal `USE CATALOG`, `USE SCHEMA`, and
`SELECT` on the project gold schema, plus `MODIFY` on
`facility_review_overlay` and `operational_event_materialization`.

The Lakebase app resource creates or reuses the OAuth Postgres role for the app
service principal. If schema initialization fails, confirm that the resource binding
granted the role `CONNECT` and creation privileges on the selected database.

## Variables

Supply these bundle variables with actual resource values:

```text
project_catalog
sql_warehouse_id
sql_warehouse_http_path
lakebase_branch
lakebase_database
lakebase_host
lakebase_database_name
tavily_secret_scope
app_access_group
```

`lakebase_branch` and `lakebase_database` are full resource names. `lakebase_host`
is the endpoint hostname from the Lakebase Connect dialog.

## Preflight

```powershell
uv sync --all-groups --frozen
npm ci
uv run pytest -m "not connected and not e2e"
npm test
npx playwright test
uv run python scripts/package_app.py
uv run python scripts/validate_artifact.py
```

Confirm Referral Copilot is disabled and Tavily remains `cached` until a deployed
egress canary succeeds.

## Manual Deployment

Use the same `--var` values for every command:

```powershell
databricks bundle validate -t prod --profile careaxiom <bundle variables>
databricks bundle deploy -t prod --profile careaxiom <bundle variables>
databricks bundle run recalculation -t prod --profile careaxiom <bundle variables>
databricks bundle run medical_desert_planner -t prod --profile careaxiom <bundle variables>
databricks apps get medical-desert-planner --profile careaxiom
```

`bundle deploy` updates resources and source but does not restart the app. The final
`bundle run medical_desert_planner` step is required.

The protected manual workflow in `.github/workflows/deploy.yml` performs the same
package, validate, deploy, pipeline, restart, and health-poll sequence using GitHub
OIDC. Configure its `prod` environment variables before triggering it.

## Health Verification

Verify `/api/health` reports:

- FastAPI running.
- Databricks SQL OAuth canary healthy.
- Gold analytical read model configured.
- Lakebase operational store healthy.
- No unexpected pending, failed, or blocked outbox events.
- MLflow trace write healthy.
- Tavily mode explicitly cached or live.
- Dataset snapshot version equal to the deployed source bundle.

Then query all three capabilities, open a facility evidence drill-down, commit one
review correction, and confirm its materialization state reaches `applied`.

## Rollback

Redeploy and run the previous saved bundle version. Preserve Lakebase review, audit,
idempotency, and outbox tables. Do not delete Delta overlay history. Re-run health
checks and the immutable source-bundle validation after rollback.
