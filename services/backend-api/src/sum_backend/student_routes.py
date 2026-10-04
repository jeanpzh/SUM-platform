"""Session-scoped consultations and Vercel AI SDK v1 streams over durable runs."""
import asyncio
import hashlib
import json
import time

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sum_contracts.ai import CreateRunRequest
from sum_contracts.models import ServiceError, require_uuid
from sum_contracts.student import StudentConsultation

from .ai_metrics import MetricsProjector
from .ai_security import verify_identity_assertion


def create_student_router(repository, settings, ai_client):
    router = APIRouter(prefix="/v1/student/ai")
    metrics = MetricsProjector(repository.database) if hasattr(repository, "database") else None

    async def actor(request):
        return verify_identity_assertion(request.headers.get("x-student-assertion", ""),
            request.method, request.url.path, hashlib.sha256(await request.body()).hexdigest(),
            settings.ai_identity_secret, "student")

    async def get_owned(run_id, owner):
        value = await asyncio.to_thread(repository.get, require_uuid(run_id), owner)
        if value.get("audience") != "student":
            raise ServiceError("AI_RUN_NOT_FOUND", "La consulta no existe.", 404)
        return value

    def packet(value):
        return "data: " + json.dumps(value, ensure_ascii=False, default=str) + "\n\n"

    async def ui_stream(request, run_id, owner, after=0):
        yield packet({"type": "start", "messageId": run_id,
                      "messageMetadata": {"run_id": run_id}})
        yield packet({"type": "data-run", "id": run_id, "data": {"run_id": run_id}})
        sequence, deadline = after, time.monotonic() + 180
        while not await request.is_disconnected():
            rows = await asyncio.to_thread(repository.events, run_id, sequence, owner)
            for row in rows:
                sequence = row["sequence"]
                # Academic values, prompts and arbitrary tool arguments never enter public progress.
                public = {key: row[key] for key in ("sequence", "kind", "stage", "duration_ms", "code", "created_at")}
                public["tool"] = row["payload"].get("tool") if row["kind"] == "tool" else None
                yield packet({"type": "data-audit", "id": str(sequence), "data": public})
            current = await get_owned(run_id, owner)
            if current["status"] in {"completed", "failed", "cancelled"} and sequence >= current["sequence"]:
                if current["status"] == "completed":
                    result = current["result"]
                    yield packet({"type": "data-result", "id": run_id, "data": result})
                    yield packet({"type": "text-start", "id": run_id + ":answer"})
                    yield packet({"type": "text-delta", "id": run_id + ":answer", "delta": result["answer"]})
                    yield packet({"type": "text-end", "id": run_id + ":answer"})
                else:
                    yield packet({"type": "error", "errorText": "Consulta cancelada." if current["status"] == "cancelled"
                                  else "No se pudo completar la consulta. Código: " + (current.get("error_code") or "AI_FAILED")})
                yield packet({"type": "finish"})
                yield "data: [DONE]\n\n"
                return
            if time.monotonic() >= deadline:
                yield packet({"type": "error", "errorText": "La consulta sigue en curso. Reabre su enlace para continuar."})
                yield "data: [DONE]\n\n"
                return
            yield ": keepalive\n\n"
            await asyncio.sleep(1)

    def streaming(request, run_id, owner, after=0):
        return StreamingResponse(ui_stream(request, run_id, owner, after), media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no",
                     "x-vercel-ai-ui-message-stream": "v1", "X-Run-Id": run_id})

    @router.post("/chat")
    async def chat(request: Request, data: StudentConsultation):
        owner = await actor(request)
        key = request.headers.get("idempotency-key", "")
        if not 1 <= len(key) <= 200:
            raise ServiceError("AI_IDEMPOTENCY_KEY_INVALID", "Se requiere Idempotency-Key.")
        run_request = CreateRunRequest(question=data.question, provider=settings.student_ai_provider,
            model=settings.student_ai_model, audience="student", student_options=data.options, top_k=6)
        previous = await asyncio.to_thread(repository.replay, owner, key, run_request)
        if previous:
            return streaming(request, previous["run_id"], owner)
        choices = await ai_client.list_models()
        if not any(item["provider"] == run_request.provider and item["model"] == run_request.model
                   and item.get("available") for item in choices):
            raise ServiceError("AI_MODEL_UNAVAILABLE", "El asistente no tiene un modelo habilitado.", 503)
        try:
            await ai_client.admit_request(owner, key, run_request.fingerprint())
        except ServiceError as exc:
            if exc.status == 429 and metrics:
                await asyncio.to_thread(metrics.record_rejection, owner, run_request.provider, run_request.model)
            raise
        value, _ = await asyncio.to_thread(repository.create, owner, key, run_request)
        return streaming(request, value["run_id"], owner)

    @router.get("/runs")
    async def history(request: Request, limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000)):
        return await asyncio.to_thread(repository.list, await actor(request), limit, offset)

    @router.get("/runs/{run_id}")
    async def detail(run_id: str, request: Request):
        return JSONResponse(await get_owned(run_id, await actor(request)), headers={"Cache-Control": "no-store"})

    @router.get("/runs/{run_id}/stream")
    async def resume(run_id: str, request: Request, after: int = Query(0, ge=0)):
        owner = await actor(request)
        value = await get_owned(run_id, owner)
        if after > value["sequence"]:
            raise ServiceError("AI_CURSOR_INVALID", "Recarga la consulta para sincronizar el progreso.", 409)
        return streaming(request, value["run_id"], owner, after)

    @router.post("/runs/{run_id}/cancel")
    async def cancel(run_id: str, request: Request):
        owner = await actor(request)
        await get_owned(run_id, owner)
        return await asyncio.to_thread(repository.cancel, require_uuid(run_id), owner)

    return router
