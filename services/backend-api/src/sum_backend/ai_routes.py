"""Authenticated administrative AI APIs and internal audit callbacks."""

from __future__ import annotations

import asyncio
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sum_contracts.ai import AuditEvent, CreateRunRequest
from sum_contracts.ai_providers import ConnectionProbe, ProviderInput, ProviderKind
from sum_contracts.models import ServiceError, require_uuid

from .ai_evaluations import EvaluationRepository
from .ai_metrics import MetricsProjector
from .ai_providers import ProviderRepository
from .ai_security import verify_admin_assertion
from .config import Settings


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=30)
    model: str = Field(min_length=1, max_length=150)
    provider_config_id: UUID | None = None
    provider_revision: int | None = Field(default=None, ge=1)


def create_ai_router(repository, settings: Settings, ai_client) -> APIRouter:
    router = APIRouter()
    metrics = MetricsProjector(repository.database) if hasattr(repository, "database") else None
    providers = ProviderRepository(repository.database, settings.ai_provider_encryption_key,
        settings.ai_provider_allowed_hosts) if metrics else None
    evaluations = EvaluationRepository(repository.database, settings.ai_evaluation_dir) if metrics else None

    async def actor(request: Request) -> str:
        digest = hashlib.sha256(await request.body()).hexdigest()
        return verify_admin_assertion(request.headers.get("x-admin-assertion", ""),
                                      request.method, request.url.path, digest,
                                      settings.ai_identity_secret)

    @router.get("/v1/admin/ai/providers")
    async def list_providers(request: Request):
        owner = await actor(request)
        if not providers:
            raise ServiceError("AI_PROVIDERS_UNAVAILABLE", "Settings no está disponible.", 503)
        return await asyncio.to_thread(providers.list, owner)

    @router.post("/v1/admin/ai/providers", status_code=201)
    async def add_provider(request: Request, data: ProviderInput):
        owner = await actor(request)
        if not providers:
            raise ServiceError("AI_PROVIDERS_UNAVAILABLE", "Settings no está disponible.", 503)
        return await asyncio.to_thread(providers.save, owner, data)

    @router.get("/v1/admin/ai/providers/pricing")
    async def provider_pricing(request: Request, provider: ProviderKind,
                               model: str = Query(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9._:/-]+$")):
        await actor(request)
        return await ai_client.model_pricing(provider, model)

    @router.post("/v1/admin/ai/providers/test")
    async def test_provider(request: Request, data: ConnectionProbe):
        owner = await actor(request)
        if not providers:
            raise ServiceError("AI_PROVIDERS_UNAVAILABLE", "Settings no está disponible.", 503)
        runtime = await asyncio.to_thread(providers.probe_runtime, owner, data)
        result = await ai_client.test_provider(owner, runtime, data.model)
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    @router.post("/v1/admin/ai/providers/{config_id}")
    async def edit_provider(config_id: str, request: Request, data: ProviderInput):
        owner = await actor(request)
        if not providers:
            raise ServiceError("AI_PROVIDERS_UNAVAILABLE", "Settings no está disponible.", 503)
        return await asyncio.to_thread(providers.save, owner, data, require_uuid(config_id))

    async def catalog(owner):
        configured = await asyncio.to_thread(providers.catalog, owner) if providers and settings.ai_provider_encryption_key else []
        return configured + await ai_client.list_models()

    @router.get("/v1/admin/ai/models")
    async def models(request: Request):
        owner = await actor(request)
        try:
            return await catalog(owner)
        except Exception as exc:
            raise ServiceError("AI_CATALOG_UNAVAILABLE", "El catálogo de modelos no está disponible.", 503) from exc

    @router.get("/v1/admin/ai/metrics")
    async def get_metrics(request: Request, days: int = Query(7, ge=1, le=90),
                          provider: str = Query("", max_length=30), model: str = Query("", max_length=150),
                          generation: str = Query("", max_length=36), status: str = Query("", max_length=20)):
        owner = await actor(request)
        if generation:
            generation = require_uuid(generation)
        if not metrics:
            raise ServiceError("AI_METRICS_UNAVAILABLE", "Las métricas no están disponibles.", 503)
        return await asyncio.to_thread(metrics.get_metrics, owner, days, provider, model, generation, status)

    @router.get("/v1/admin/ai/evaluations")
    async def list_evaluations(request: Request):
        owner = await actor(request)
        if not evaluations:
            return {"datasets": [], "evaluations": []}
        return {"datasets": await asyncio.to_thread(evaluations.catalog),
                "evaluations": await asyncio.to_thread(evaluations.list, owner)}

    @router.post("/v1/admin/ai/evaluations", status_code=202)
    async def evaluate(request: Request, data: EvaluationRequest):
        owner = await actor(request)
        if not evaluations:
            raise ServiceError("AI_DATASET_UNKNOWN", "No hay conjuntos instalados.", 422)
        choices = await catalog(owner)
        if not any(item.get("provider") == data.provider and item.get("model") == data.model and item.get("available") and item.get("provider_config_id") == (str(data.provider_config_id) if data.provider_config_id else None)
                   and item.get("provider_revision") == data.provider_revision for item in choices):
            raise ServiceError("AI_MODEL_UNKNOWN", "El modelo no está permitido.", 422)
        key = request.headers.get("idempotency-key", "")
        if not 1 <= len(key) <= 200:
            raise ServiceError("AI_IDEMPOTENCY_KEY_INVALID", "Se requiere Idempotency-Key.")
        if data.provider_config_id:
            await asyncio.to_thread(providers.runtime, owner, data.provider_config_id, data.provider_revision, current=True)
        await ai_client.admit_request(owner, key, hashlib.sha256(data.model_dump_json().encode()).hexdigest())
        return await asyncio.to_thread(evaluations.create, owner, key, data.dataset_id, data.provider, data.model, data.provider_config_id, data.provider_revision)

    @router.post("/v1/admin/ai/runs", status_code=202)
    async def create(request: Request, data: CreateRunRequest):
        owner = await actor(request)
        if data.audience != "admin":
            raise ServiceError("AI_SCOPE_INVALID", "Usa el endpoint estudiantil para esta consulta.", 403)
        key = request.headers.get("idempotency-key", "")
        if not 1 <= len(key) <= 200:
            raise ServiceError("AI_IDEMPOTENCY_KEY_INVALID", "Se requiere Idempotency-Key.")
        if hasattr(repository, "replay"):
            previous = await asyncio.to_thread(repository.replay, owner, key, data)
            if previous:
                return JSONResponse(previous, status_code=202)
        try:
            choices = await catalog(owner)
        except Exception as exc:
            raise ServiceError("AI_CATALOG_UNAVAILABLE", "El catálogo de modelos no está disponible.", 503) from exc
        choice = next((item for item in choices if item.get("provider") == data.provider and item.get("model") == data.model and
                       item.get("provider_config_id") == (str(data.provider_config_id) if data.provider_config_id else None) and
                       item.get("provider_revision") == data.provider_revision), None)
        if choice is None:
            raise ServiceError("AI_MODEL_UNKNOWN", "El modelo no está permitido.", 422)
        if not choice.get("available"):
            raise ServiceError("AI_MODEL_UNAVAILABLE", "El modelo no está disponible.", 503)
        if data.provider_config_id:
            runtime = await asyncio.to_thread(providers.runtime, owner, data.provider_config_id, data.provider_revision, current=True)
            if runtime.provider != data.provider or not any(item.model == data.model for item in runtime.models):
                raise ServiceError("AI_MODEL_UNKNOWN", "El modelo no pertenece a la conexión.", 422)
        try:
            await ai_client.admit_request(owner, key, data.fingerprint())
        except ServiceError as exc:
            if exc.status == 429 and metrics:
                await asyncio.to_thread(metrics.record_rejection, owner, data.provider, data.model)
            raise
        result, _ = await asyncio.to_thread(repository.create, owner, key, data)
        return JSONResponse(result, status_code=202,
                            headers={"Location": f"/v1/admin/ai/runs/{result['run_id']}"})

    @router.get("/v1/admin/ai/runs")
    async def list_runs(request: Request, limit: int = Query(25, ge=1, le=100),
                        offset: int = Query(0, ge=0), days: int | None = Query(None, ge=1, le=90),
                        provider: str = Query("", max_length=30), model: str = Query("", max_length=150),
                        generation: str = Query("", max_length=36), status: str = Query("", max_length=20)):
        owner = await actor(request)
        if generation:
            generation = require_uuid(generation)
        if days is not None or provider or model or generation or status:
            return await asyncio.to_thread(repository.list, owner, limit, offset, days, provider, model, generation, status)
        return await asyncio.to_thread(repository.list, owner, limit, offset)

    @router.get("/v1/admin/ai/runs/{run_id}")
    async def get(run_id: str, request: Request):
        owner = await actor(request)
        value = await asyncio.to_thread(repository.get, require_uuid(run_id), owner)
        if value.get("provider_config_id"):
            value["configuration"] = await asyncio.to_thread(providers.public_revision, owner,
                value["provider_config_id"], value["provider_revision"])
        return value

    @router.post("/v1/admin/ai/runs/{run_id}/cancel")
    async def cancel(run_id: str, request: Request):
        owner = await actor(request)
        return await asyncio.to_thread(repository.cancel, require_uuid(run_id), owner)

    @router.get("/v1/admin/ai/runs/{run_id}/events")
    async def events(run_id: str, request: Request):
        owner = await actor(request)
        run_id = require_uuid(run_id)
        current = await asyncio.to_thread(repository.get, run_id, owner)
        try:
            after = int(request.headers.get("last-event-id", request.query_params.get("after", "0")))
        except ValueError:
            raise ServiceError("AI_CURSOR_INVALID", "La secuencia no es válida.") from None
        if after < 0 or after > current["sequence"]:
            raise ServiceError("AI_CURSOR_INVALID", "La secuencia no es válida.")

        async def stream():
            sequence = after
            while not await request.is_disconnected():
                rows = await asyncio.to_thread(repository.events, run_id, sequence, owner)
                for row in rows:
                    sequence = row["sequence"]
                    yield f"id: {sequence}\nevent: audit\ndata: {json.dumps(row, ensure_ascii=False, default=str)}\n\n"
                current = await asyncio.to_thread(repository.get, run_id, owner)
                if current["status"] in {"completed", "failed", "cancelled"}:
                    return
                yield ": keepalive\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @router.get("/internal/ai/runs/{run_id}", include_in_schema=False)
    async def context(run_id: str):
        value = await asyncio.to_thread(repository.context, require_uuid(run_id))
        if value.request.provider_config_id:
            runtime = await asyncio.to_thread(providers.runtime, value.owner_id, value.request.provider_config_id,
                                              value.request.provider_revision)
            value = value.model_copy(update={"provider_runtime": runtime})
        output = value.model_dump(mode="json")
        if value.provider_runtime:
            output["provider_runtime"]["api_key"] = value.provider_runtime.api_key.get_secret_value()
        return JSONResponse(output, headers={"Cache-Control": "no-store"})

    @router.post("/internal/ai/runs/{run_id}/events", include_in_schema=False)
    async def audit(run_id: str, event: AuditEvent):
        return await asyncio.to_thread(repository.apply_event, require_uuid(run_id), event)

    return router
