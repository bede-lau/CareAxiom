# Databricks App packaging

`scripts/package_app.py` builds the React frontend into
`src/medical_desert/presentation/static` and creates the exact deployable source
root at `.dist/react-app`.

The package intentionally excludes repository tests, fixtures, source frontend
files, local databases, credentials, and pipeline implementation. Pipeline code
is synchronized separately for the recalculation Job by the bundle.

Required user-created resources are supplied as bundle variables:

- `project_catalog`
- `sql_warehouse_id`
- `sql_warehouse_http_path`
- `lakebase_branch`
- `lakebase_database`
- `lakebase_host`
- `tavily_secret_scope`

Local validation does not deploy, bind, grant, or modify any remote resource.

Production enables the Databricks gold-table analytical adapter and Lakebase
operational store. SQL connections use Databricks App OAuth. Lakebase connections
use the app service principal with per-connection OAuth credential rotation.
Review writes commit to Lakebase with audit and outbox records, then idempotently
merge review and event overlays into Delta before the outbox event becomes
`applied`. MLflow tracing is enabled by the bundle and health verifies a trace write.

Deployment remains a manual external action. Use the commands in
`docs/deployment.md` or trigger `.github/workflows/deploy.yml` after configuring
its protected `prod` environment variables.
