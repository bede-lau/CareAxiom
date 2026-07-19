from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast
from uuid import uuid4

import uvicorn
from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from medical_desert.adapters.databricks_analytics import DatabricksGoldAnalyticsAdapter
from medical_desert.adapters.databricks_sql import DatabricksSQLAdapter
from medical_desert.adapters.demo_analytics import DemoAnalyticsAdapter
from medical_desert.adapters.tavily import TavilyAdapter
from medical_desert.adapters.tracing import MLflowTracingAdapter, NoopTracingAdapter
from medical_desert.application.errors import ApplicationError
from medical_desert.application.services import MedicalDesertService
from medical_desert.config.settings import Settings, get_settings
from medical_desert.domain.models import (
    Actor,
    Capability,
    CapabilityId,
    CrisisAnalysis,
    CrisisAnalyzeRequest,
    DocumentaryQuery,
    DocumentaryQueryResult,
    ErrorBody,
    ErrorCode,
    EvidenceSpan,
    ExternalVerificationResult,
    FacilityDetail,
    Geography,
    HealthResponse,
    OverrideRequest,
    ProductRole,
    ReferralRequest,
    ReferralShortlist,
    ReviewStatus,
    Scenario,
    ScenarioChange,
    ScenarioCreate,
    ScenarioUpdate,
    SurveyContext,
    VerificationDecision,
    VerificationItem,
    VerificationItemCreate,
)
from medical_desert.identity.actor import ActorProvider
from medical_desert.persistence.lakebase import LakebaseOperationalStore
from medical_desert.persistence.sqlite import SQLiteOperationalStore
from medical_desert.ports.analytics import AnalyticsPort

PLANNING_BOUNDARY = (
    "Planning support only. Facility capabilities may be incomplete or stale. "
    "Do not use this application for emergency dispatch, diagnosis, or confirmation "
    "of current service availability."
)


def _error_response(
    request: Request,
    *,
    code: ErrorCode,
    message: str,
    recovery: str,
    status_code: int,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", f"request-{uuid4()}")
    body = ErrorBody(
        code=code,
        message=message,
        recovery=recovery,
        details=details or {},
        request_id=request_id,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    store: SQLiteOperationalStore
    if settings.lakebase_enabled:
        if not settings.lakebase_host or not settings.lakebase_endpoint_name:
            raise ValueError(
                "Lakebase host and endpoint name are required when Lakebase is enabled."
            )
        store = LakebaseOperationalStore(
            host=settings.lakebase_host,
            database=settings.lakebase_database,
            endpoint_name=settings.lakebase_endpoint_name,
            user=settings.lakebase_user,
            port=settings.lakebase_port,
            sslmode=settings.lakebase_sslmode,
        )
    else:
        store = SQLiteOperationalStore(settings.database_path)
    store.initialize()
    tracing = (
        MLflowTracingAdapter(settings.mlflow_experiment_name)
        if settings.mlflow_enabled
        else NoopTracingAdapter()
    )
    web_verification = (
        None
        if settings.tavily_mode == "off"
        else TavilyAdapter(settings.tavily_mode, settings.tavily_api_key)
    )
    sql_query = (
        DatabricksSQLAdapter(
            settings.databricks_server_hostname,
            settings.databricks_http_path,
            settings.databricks_access_token,
        )
        if settings.databricks_enabled and settings.databricks_http_path
        else None
    )
    analytics: AnalyticsPort
    if settings.databricks_enabled:
        if sql_query is None:
            raise ValueError(
                "Databricks SQL HTTP path is required when Databricks analytics is enabled."
            )
        analytics = DatabricksGoldAnalyticsAdapter(
            sql_query,
            project_catalog=settings.project_catalog,
            source_bundle_id=settings.analytical_source_bundle_id,
            policy_version=settings.policy_version,
            scoring_version=settings.scoring_version,
            focus_state=settings.focus_state,
            focus_district=settings.focus_district,
        )
    else:
        analytics = DemoAnalyticsAdapter()
    service = MedicalDesertService(
        settings,
        analytics,
        store,
        tracing,
        web_verification,
        sql_query,
    )
    provider = ActorProvider(settings)
    app.state.settings = settings
    app.state.service = service
    app.state.actor_provider = provider
    bootstrap_actor = Actor(
        actor_id=settings.demo_actor_id,
        display_name="Medical Desert Planner bootstrap",
        roles=[
            ProductRole.PLANNER,
            ProductRole.REVIEWER,
            ProductRole.ADMINISTRATOR,
        ],
        identity_mode=settings.identity_mode,
    )
    service.bootstrap_verification_queue(bootstrap_actor)
    service.materialize_pending_events()
    yield


app = FastAPI(
    title="Medical Desert Planner API",
    version="0.1.0",
    description=PLANNING_BOUNDARY,
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request.state.request_id = request.headers.get("x-request-id") or f"request-{uuid4()}"
    response = await call_next(request)
    response.headers["x-request-id"] = request.state.request_id
    response.headers["x-planning-boundary"] = PLANNING_BOUNDARY
    return response


@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, error: ApplicationError) -> JSONResponse:
    return _error_response(
        request,
        code=error.code,
        message=error.message,
        recovery=error.recovery,
        status_code=error.status_code,
        details=error.details,
    )


@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, error: PermissionError) -> JSONResponse:
    return _error_response(
        request,
        code=ErrorCode.FORBIDDEN,
        message=str(error),
        recovery="Use a trusted actor with the required product role.",
        status_code=403,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    return _error_response(
        request,
        code=ErrorCode.VALIDATION_ERROR,
        message="The request did not match the API contract.",
        recovery="Correct the documented fields and retry.",
        status_code=422,
        details={"errors": error.errors()},
    )


def service(request: Request) -> MedicalDesertService:
    return cast(MedicalDesertService, request.app.state.service)


def settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def actor(
    request: Request,
    x_forwarded_user: str | None = Header(default=None, alias="X-Forwarded-User"),
    x_forwarded_email: str | None = Header(default=None, alias="X-Forwarded-Email"),
) -> Actor:
    provider: ActorProvider = request.app.state.actor_provider
    return provider.resolve(x_forwarded_user, x_forwarded_email)


def idempotency_key(
    request: Request, value: str | None = Header(default=None, alias="Idempotency-Key")
) -> str:
    if not value:
        raise ApplicationError(
            ErrorCode.IDEMPOTENCY_KEY_REQUIRED,
            "Idempotency-Key is required for write operations.",
            "Retry with a stable unique key for this logical operation.",
            status_code=400,
        )
    if len(value) > 200:
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            "Idempotency-Key is too long.",
            "Use a key of 200 characters or fewer.",
            status_code=422,
        )
    return value


def request_id(request: Request) -> str:
    return str(request.state.request_id)


@app.get("/api/health", response_model=HealthResponse)
def get_health(svc: MedicalDesertService = Depends(service)) -> HealthResponse:
    return svc.health()


@app.get("/api/identity", response_model=Actor)
def get_identity(current_actor: Actor = Depends(actor)) -> Actor:
    return current_actor


@app.get("/api/capabilities", response_model=list[Capability])
def get_capabilities(svc: MedicalDesertService = Depends(service)) -> list[Capability]:
    return svc.capabilities()


@app.get("/api/geographies", response_model=list[Geography])
def get_geographies(
    include_disabled: bool = Query(default=True),
    svc: MedicalDesertService = Depends(service),
) -> list[Geography]:
    values = svc.analytics.list_geographies()
    return values if include_disabled else [value for value in values if value.selectable]


@app.post("/api/documentary-evidence/query", response_model=DocumentaryQueryResult)
def query_documentary_evidence(
    payload: DocumentaryQuery,
    svc: MedicalDesertService = Depends(service),
    _: Actor = Depends(actor),
) -> DocumentaryQueryResult:
    return svc.query(payload)


@app.get("/api/regions/{region_id}", response_model=DocumentaryQueryResult)
def get_region(
    region_id: str,
    capability_id: CapabilityId = Query(default=CapabilityId.MATERNAL_EMERGENCY),
    radius_km: int = Query(default=25),
    svc: MedicalDesertService = Depends(service),
    _: Actor = Depends(actor),
) -> DocumentaryQueryResult:
    if radius_km not in {10, 25, 50}:
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            "Unsupported radius.",
            "Use one of the versioned presets: 10, 25, or 50 km.",
            status_code=422,
        )
    return svc.query(
        DocumentaryQuery(
            capability_id=capability_id,
            geography_id=region_id,
            radius_km=radius_km,
        )
    )


@app.get("/api/districts/{district_id}/survey-context", response_model=SurveyContext)
def get_survey_context(
    district_id: str,
    svc: MedicalDesertService = Depends(service),
    _: Actor = Depends(actor),
) -> SurveyContext:
    context = svc.analytics.get_survey_context(district_id)
    if context is None:
        raise ApplicationError(
            ErrorCode.NOT_FOUND,
            "District survey context was not found.",
            "Use a district identifier returned by /api/geographies.",
            status_code=404,
        )
    return context


@app.get("/api/facilities/{facility_id}", response_model=FacilityDetail)
def get_facility(
    facility_id: str,
    svc: MedicalDesertService = Depends(service),
    _: Actor = Depends(actor),
) -> FacilityDetail:
    return svc.facility(facility_id)


@app.get("/api/facilities/{facility_id}/evidence", response_model=list[EvidenceSpan])
def get_facility_evidence(
    facility_id: str,
    capability_id: CapabilityId | None = Query(default=None),
    svc: MedicalDesertService = Depends(service),
    _: Actor = Depends(actor),
) -> list[EvidenceSpan]:
    return svc.evidence(facility_id, capability_id)


@app.post("/api/facilities/{facility_id}/override")
def create_facility_override(
    facility_id: str,
    payload: OverrideRequest,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
    key: str = Depends(idempotency_key),
    current_request_id: str = Depends(request_id),
) -> dict[str, object]:
    return svc.override(facility_id, payload, current_actor, key, current_request_id)


@app.post("/api/verification/items", response_model=VerificationItem)
def create_verification_item(
    payload: VerificationItemCreate,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
    key: str = Depends(idempotency_key),
    current_request_id: str = Depends(request_id),
) -> VerificationItem:
    return svc.create_verification_item(payload, current_actor, key, current_request_id)


@app.get("/api/verification/queue", response_model=list[VerificationItem])
def get_verification_queue(
    status: ReviewStatus | None = Query(default=None),
    svc: MedicalDesertService = Depends(service),
    _: Actor = Depends(actor),
) -> list[VerificationItem]:
    items = svc.store.list_verification_items()
    return items if status is None else [item for item in items if item.status == status]


@app.post(
    "/api/verification/items/{item_id}/external-evidence",
    response_model=ExternalVerificationResult,
)
def get_external_verification_evidence(
    item_id: str,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
) -> ExternalVerificationResult:
    return svc.external_verification(item_id, current_actor)


@app.post("/api/verification/items/{item_id}/decision", response_model=VerificationItem)
def decide_verification_item(
    item_id: str,
    payload: VerificationDecision,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
    key: str = Depends(idempotency_key),
    current_request_id: str = Depends(request_id),
) -> VerificationItem:
    return svc.decide_verification_item(item_id, payload, current_actor, key, current_request_id)


@app.post("/api/scenarios", response_model=Scenario)
def create_scenario(
    payload: ScenarioCreate,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
    key: str = Depends(idempotency_key),
    current_request_id: str = Depends(request_id),
) -> Scenario:
    return svc.create_scenario(payload, current_actor, key, current_request_id)


@app.get("/api/scenarios", response_model=list[Scenario])
def list_scenarios(
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
) -> list[Scenario]:
    return svc.store.list_scenarios(current_actor.actor_id)


@app.get("/api/scenarios/{scenario_id}", response_model=Scenario)
def get_scenario(
    scenario_id: str,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
) -> Scenario:
    return svc.get_scenario(scenario_id, current_actor)


@app.put("/api/scenarios/{scenario_id}", response_model=Scenario)
def update_scenario(
    scenario_id: str,
    payload: ScenarioUpdate,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
    key: str = Depends(idempotency_key),
    current_request_id: str = Depends(request_id),
) -> Scenario:
    return svc.update_scenario(scenario_id, payload, current_actor, key, current_request_id)


@app.get("/api/scenarios/{scenario_id}/changes", response_model=list[ScenarioChange])
def get_scenario_changes(
    scenario_id: str,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
) -> list[ScenarioChange]:
    return svc.scenario_changes(scenario_id, current_actor)


@app.get("/api/scenarios/{scenario_id}/exports/json")
@app.get("/api/scenarios/{scenario_id}/export.json", include_in_schema=False)
def export_scenario_json(
    scenario_id: str,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
) -> PlainTextResponse:
    return PlainTextResponse(
        svc.export_json(scenario_id, current_actor),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{scenario_id}.json"'},
    )


@app.get("/api/scenarios/{scenario_id}/exports/csv")
@app.get("/api/scenarios/{scenario_id}/export.csv", include_in_schema=False)
def export_scenario_csv(
    scenario_id: str,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
) -> PlainTextResponse:
    return PlainTextResponse(
        svc.export_csv(scenario_id, current_actor),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{scenario_id}.csv"'},
    )


@app.get("/api/scenarios/{scenario_id}/decision-brief")
def export_decision_brief(
    scenario_id: str,
    svc: MedicalDesertService = Depends(service),
    current_actor: Actor = Depends(actor),
) -> PlainTextResponse:
    return PlainTextResponse(
        svc.decision_brief(scenario_id, current_actor),
        media_type="text/markdown",
    )


@app.post("/api/crisis/analyze", response_model=CrisisAnalysis)
def analyze_crisis(
    payload: CrisisAnalyzeRequest,
    svc: MedicalDesertService = Depends(service),
    _: Actor = Depends(actor),
) -> CrisisAnalysis:
    return svc.crisis(payload)


def create_referral_shortlist(
    payload: ReferralRequest,
    svc: MedicalDesertService = Depends(service),
    _: Actor = Depends(actor),
) -> ReferralShortlist:
    return svc.referral(payload)


if get_settings().referral_enabled:
    app.post("/api/referral/shortlist", response_model=ReferralShortlist)(create_referral_shortlist)

static_directory = Path(__file__).resolve().parents[1] / "presentation" / "static"
if (static_directory / "index.html").is_file():
    app.mount("/", StaticFiles(directory=static_directory, html=True), name="application")


def run() -> None:
    port = int(os.environ.get("DATABRICKS_APP_PORT", "8000"))
    uvicorn.run("medical_desert.api.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
