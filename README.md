# Medical Desert Planner

Medical Desert Planner is an evidence-grounded planning application for comparing nearby facility documentary support with separately presented NFHS-5 district survey context. It does not confirm current service availability, capacity, or a medical desert.

## Prerequisites

- Python 3.12
- `uv`
- Node.js 20 or newer
- npm
- Chromium for Playwright browser tests

## Setup

Install the declared application and development dependencies:

```powershell
uv sync --all-groups
npm ci
npx playwright install chromium
```

Do not add Databricks or Tavily credentials to `.env`, test output, traces, or committed files.

## Run Locally

Start the API and frontend in separate terminals:

```powershell
$env:CAREAXIOM_APP = "medical_desert.api.main:app"
uv run uvicorn medical_desert.api.main:app --reload
npm run dev
```

The local API uses the deterministic Darbhanga adapter unless Databricks is enabled.
Frontend read fallback is disabled by default; set `VITE_DEMO_FALLBACK=true` only for an
explicit offline UI demonstration. Writes never fall back to browser-local state.

## Test

Run the offline G0-G7 suite:

```powershell
uv run pytest -m "not connected and not e2e"
```

Run coverage:

```powershell
uv run pytest `
  -m "not connected and not e2e" `
  --cov=medical_desert `
  --cov-report=term-missing `
  --cov-report=html:reports/coverage
```

Run connected catalog contracts only when credentials are explicitly available:

```powershell
$env:DATABRICKS_SERVER_HOSTNAME = "dbc-..."
$env:DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/..."
$env:DATABRICKS_TOKEN = "..."
uv run pytest -m connected
```

Run browser verification. Playwright starts both the API and frontend:

```powershell
npx playwright test
```

## Fixture Integrity

Offline fixtures live in `fixtures/contracts` and `fixtures/demo`. `fixtures/manifest.sha256` records every JSON fixture hash.

Verify the manifest:

```powershell
uv run pytest tests/test_fixture_manifest.py
```

The Darbhanga fixture freezes:

- 15 observed facility records.
- 0 maternal-emergency policy matches.
- 3 emergency-surgery policy matches.
- 2 advanced-imaging policy matches.
- NFHS context values `24.9`, `69.9`, and `60.8`.
- Lifecare Hospital and Skin Hair Laser Clinic as high-priority geography conflicts excluded from confident aggregation pending review.

## Deploy

1. Run the offline pytest suite, frontend tests, frontend build, and Playwright suite.
2. Confirm Referral Copilot is disabled and absent from default navigation.
3. Build and validate the exact Databricks App artifact with `scripts/package_app.py`.
4. Supply the existing warehouse, Lakebase, project catalog, and secret-scope bundle variables.
5. Deploy the bundle, run `recalculation`, then run `medical_desert_planner` to restart the app.
6. Keep Tavily cached-only unless the deployed egress canary passes.
7. Verify `/api/health`, warm SQL and Lakebase, and rehearse the one-minute flow.

See [Deployment](docs/deployment.md), [Test Strategy](docs/test-strategy.md), and [One-Minute Demo](demo/ONE_MINUTE_DEMO.md).
