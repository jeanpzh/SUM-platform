"""Internal HTTP entry point for model discovery and Inngest functions."""

from __future__ import annotations

import asyncio
import hmac
import logging
from uuid import uuid4
from contextlib import asynccontextmanager

import inngest
import inngest.fast_api
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from redis.asyncio import Redis
from sum_contracts.ai_providers import ConnectionProbeResult, InternalConnectionProbe, ProviderKind

from .config import AiSettings
from .embeddings import QueryEmbedder
from .models import ModelRegistry
from .litellm_adapter import model_pricing, probe_connection
from .quota import QuotaManager, QuotaRejected
from .reporter import HttpAuditRecorder
from .retrieval import PublishedRetriever, PublishedStore
from .runner import AgentLimits, AgentRunner
from .student_context import HttpAcademicGateway, RuleRegistry
from .student_runner import AudienceRunner, StudentOrchestrator
from .workflow import register


class AdmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_id: str = Field(min_length=1, max_length=200)
    key: str = Field(min_length=1, max_length=200)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


def create_app(settings: AiSettings | None = None, registry: ModelRegistry | None = None,
               runner: AgentRunner | None = None) -> FastAPI:
    settings = settings or AiSettings.from_env()
    registry = registry or ModelRegistry.from_settings(settings)
    redis = Redis.from_url(settings.redis_url)
    quota = QuotaManager(redis,
        student_requests_per_minute=settings.student_requests_per_minute,
        student_requests_per_day=settings.student_requests_per_day,
        student_tokens_per_minute=settings.student_tokens_per_minute,
        student_tokens_per_day=settings.student_tokens_per_day)
    runner = runner or AgentRunner(registry, PublishedRetriever(PublishedStore(settings.database_url),
                QueryEmbedder(settings, quota)), quota, AgentLimits(timeout_seconds=settings.run_timeout_seconds))

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            await redis.aclose()
            await asyncio.to_thread(runner.retriever.store.database.close)

    app = FastAPI(title="SUM — AI Service interno", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Probe requests contain credentials; never echo invalid input values.
        return JSONResponse({"codigo": "SOLICITUD_INVALIDA", "mensaje": "Revisa los campos de la solicitud."},
                            status_code=422)

    @app.get("/health")
    async def health():
        try:
            async with asyncio.timeout(3):
                await redis.ping()
                await asyncio.to_thread(runner.retriever.store.database.open)
        except Exception:
            return JSONResponse({"estado": "no_disponible"}, status_code=503)
        return {"estado": "disponible", "database": "ready", "redis": "ready",
                "configured_models": len(registry.list_available())}

    @app.post("/internal/admit")
    async def admit(data: AdmissionRequest, authorization: str = Header(default="")):
        if not hmac.compare_digest(authorization, "Bearer " + settings.service_token):
            raise HTTPException(status_code=401)
        try:
            await quota.admit_request(data.actor_id, data.key + ":" + data.fingerprint)
        except QuotaRejected as exc:
            return JSONResponse({"codigo": exc.code, "mensaje": exc.message}, status_code=exc.status,
                                headers={"Retry-After": str(exc.retry_after)})
        return {"admitted": True}

    @app.get("/internal/models")
    async def models(authorization: str = Header(default="")):
        expected = "Bearer " + settings.service_token
        if not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401)
        return [item.model_dump() for item in registry.list_available()]

    @app.get("/internal/models/pricing")
    async def pricing(provider: ProviderKind,
                      model: str = Query(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9._:/-]+$"),
                      authorization: str = Header(default="")):
        if not hmac.compare_digest(authorization, "Bearer " + settings.service_token):
            raise HTTPException(status_code=401)
        return await asyncio.to_thread(model_pricing, provider, model)

    @app.post("/internal/providers/test")
    async def test_connection(data: InternalConnectionProbe, authorization: str = Header(default="")):
        if not hmac.compare_digest(authorization, "Bearer " + settings.service_token):
            raise HTTPException(status_code=401)
        try:
            async with asyncio.timeout(10):
                await quota.admit_request(data.actor_id, "probe:" + str(uuid4()))
                result = await probe_connection(registry, quota, data.actor_id, data.runtime, data.model)
            return ConnectionProbeResult.model_validate(result).model_dump(mode="json")
        except QuotaRejected as exc:
            return JSONResponse({"codigo": exc.code, "mensaje": exc.message}, status_code=exc.status,
                headers={"Retry-After": str(exc.retry_after)})
        except TimeoutError:
            return JSONResponse({"success": False, "code": "AI_PROVIDER_TIMEOUT", "latency_ms": 10000,
                "tools_supported": False, "input_tokens": 0, "output_tokens": 0})

    client = inngest.Inngest(app_id="sum-ai", logger=logging.getLogger("sum.ai"))
    audience_runner = AudienceRunner(runner, StudentOrchestrator(runner,
        HttpAcademicGateway(settings.academic_gateway_url, settings.service_token),
        RuleRegistry.load(settings.student_rules_file)))
    inngest.fast_api.serve(app, client, register(client, audience_runner,
        lambda run_id: HttpAuditRecorder(settings.backend_url, settings.service_token, run_id)))

    return app
