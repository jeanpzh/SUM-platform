from __future__ import annotations

import asyncio
import codecs
import hashlib
import hmac
import json
import logging
import tempfile
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException
from sum_contracts.models import TERMINAL, Metadata, ServiceError, require_uuid
from sum_storage.objects import from_env

from .ai_client import AiServiceClient
from .ai_metrics import MetricsProjector
from .ai_repository import AiRunRepository
from .ai_routes import create_ai_router
from .config import Settings
from .repository import PostgresJobs
from .student_routes import create_student_router


def detect_mime(sample: bytes, declared: str | None) -> str:
    if b"%PDF-" in sample[:1024]:
        return "application/pdf"
    if sample.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if sample.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if declared == "text/plain" and b"\x00" not in sample:
        try:
            codecs.getincrementaldecoder("utf-8")().decode(sample, final=False)
            return "text/plain"
        except UnicodeDecodeError:
            pass
    raise ServiceError("FORMATO_NO_ADMITIDO", "Se admiten PDF, PNG, JPEG y texto UTF-8.", 415)


class BodyLimit:
    def __init__(self, app, limit: int):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = self.limit + 1
        if length > self.limit:
            return await JSONResponse(
                {
                    "codigo": "ARCHIVO_DEMASIADO_GRANDE",
                    "mensaje": "La solicitud supera el tamaño permitido.",
                },
                status_code=413,
            )(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > self.limit:
                if headers.get(b"content-type", b"").startswith(b"multipart/form-data"):
                    # The multipart parser closes its spooled files on this exception.
                    raise MultiPartException("SUM_UPLOAD_LIMIT")
                raise HTTPException(413)
            return message

        await self.app(scope, bounded_receive, send)


def create_app(settings: Settings | None = None, repository=None, storage=None,
               ai_repository=None, ai_client=None) -> FastAPI:
    settings = settings or Settings.from_env()
    own_repository = repository is None
    repository = repository or PostgresJobs(
        settings.database_url, settings.pool_size, settings.max_pending_jobs
    )
    storage = storage or from_env()
    own_ai_repository = ai_repository is None and own_repository
    ai_repository = ai_repository or (AiRunRepository(settings.database_url, settings.pool_size)
                                      if own_repository else None)
    ai_client = ai_client or (AiServiceClient(settings.ai_service_url, settings.internal_token)
                              if ai_repository else None)

    async def cleanup_objects(document_id=None):
        pending = await asyncio.to_thread(repository.pending_object_deletions, document_id)
        failed = False
        for item in pending:
            try:
                operation = storage.delete_prefix if item["kind"] == "prefix" else storage.delete
                await asyncio.to_thread(operation, item["object_key"])
                await asyncio.to_thread(repository.acknowledge_object_deletion, item["object_key"])
            except Exception:
                failed = True
                logging.getLogger("sum.backend").warning(
                    "Limpieza de almacenamiento pendiente de reintento."
                )
        return failed or len(pending) == 100

    async def cleanup_loop():
        while True:
            try:
                await cleanup_objects()
            except Exception:
                logging.getLogger("sum.backend").warning(
                    "No se pudo consultar la limpieza pendiente."
                )
            await asyncio.sleep(30)

    async def metrics_loop():
        projector = MetricsProjector(ai_repository.database)
        while True:
            try:
                await asyncio.to_thread(projector.project)
                await asyncio.to_thread(projector.purge)
            except Exception:
                logging.getLogger("sum.backend").warning("La proyección de métricas de IA queda pendiente.")
            await asyncio.sleep(15)

    @asynccontextmanager
    async def lifespan(app):
        if own_repository:
            await asyncio.to_thread(repository.open)
        if own_ai_repository:
            await asyncio.to_thread(ai_repository.open)
        cleanup_task = asyncio.create_task(cleanup_loop()) if own_repository else None
        metrics_task = asyncio.create_task(metrics_loop()) if own_ai_repository else None
        try:
            yield
        finally:
            if cleanup_task:
                cleanup_task.cancel()
                await asyncio.gather(cleanup_task, return_exceptions=True)
            if metrics_task:
                metrics_task.cancel()
                await asyncio.gather(metrics_task, return_exceptions=True)
            if own_repository:
                await asyncio.to_thread(repository.close)
            if own_ai_repository:
                await asyncio.to_thread(ai_repository.close)

    app = FastAPI(title="SUM — Documentos e indexación", version="0.1.0", lifespan=lifespan)
    if ai_repository:
        app.include_router(create_ai_router(ai_repository, settings, ai_client))
        app.include_router(create_student_router(ai_repository, settings, ai_client))
    app.add_middleware(BodyLimit, limit=settings.max_upload_bytes + 65536)

    def authenticate(request: Request, internal: bool = False) -> str:
        expected = settings.internal_token if internal else settings.admin_token
        header = request.headers.get("authorization", "")
        token = header.removeprefix("Bearer ") if header.startswith("Bearer ") else ""
        if not hmac.compare_digest(token.encode(), expected.encode()):
            raise ServiceError("NO_AUTORIZADO", "Se requiere una credencial válida.", 401)
        return settings.admin_identity

    @app.middleware("http")
    async def authorize_early(request: Request, call_next):
        try:
            if request.method != "OPTIONS" and request.url.path.startswith(("/v1/", "/internal/")):
                authenticate(request, internal=request.url.path.startswith("/internal/"))
            return await call_next(request)
        except ServiceError as exc:
            return JSONResponse(
                {"codigo": exc.code, "mensaje": exc.message}, status_code=exc.status
            )

    @app.exception_handler(ServiceError)
    async def service_error(request, exc):
        headers = {"Retry-After": str(exc.retry_after)} if hasattr(exc, "retry_after") else None
        return JSONResponse({"codigo": exc.code, "mensaje": exc.message}, status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            {
                "codigo": "SOLICITUD_INVALIDA",
                "mensaje": "Revise los campos obligatorios y sus formatos.",
                "campos": [".".join(map(str, error["loc"])) for error in exc.errors()],
            },
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        if exc.detail == "SUM_UPLOAD_LIMIT":
            exc = HTTPException(413)
        messages = {
            404: "La ruta no existe.",
            405: "El método no está permitido.",
            413: "La solicitud supera el tamaño permitido.",
            400: "No se pudo leer la solicitud.",
        }
        return JSONResponse(
            {
                "codigo": f"HTTP_{exc.status_code}",
                "mensaje": messages.get(exc.status_code, "La solicitud no se pudo completar."),
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return JSONResponse(
            {
                "codigo": "SERVICIO_NO_DISPONIBLE",
                "mensaje": "El servicio no está disponible. Intente más tarde.",
            },
            status_code=503,
        )

    @app.get("/health")
    async def health():
        return {"estado": "disponible"}

    async def accept(
        request: Request, archivo: UploadFile, metadatos: str, document_id: str | None = None
    ):
        owner = authenticate(request)
        key = request.headers.get("idempotency-key", "")
        if not 1 <= len(key) <= 200:
            raise ServiceError(
                "CLAVE_IDEMPOTENCIA_INVALIDA",
                "Se requiere una cabecera Idempotency-Key de hasta 200 caracteres.",
            )
        if document_id is not None:
            document_id = require_uuid(document_id)
        if len(metadatos.encode()) > 32768:
            raise ServiceError("METADATOS_INVALIDOS", "Los metadatos superan el tamaño permitido.")
        try:
            metadata = Metadata.parse(json.loads(metadatos))
        except json.JSONDecodeError:
            raise ServiceError(
                "METADATOS_INVALIDOS", "Los metadatos deben contener JSON válido."
            ) from None
        if metadata.es_prueba and settings.env_mode != "DEVELOPMENT":
            raise ServiceError(
                "MODO_NO_ADMITIDO", "Los documentos de prueba solo se admiten en DEVELOPMENT.", 403
            )
        digest, size, sample = hashlib.sha256(), 0, b""
        object_key = f"originals/{uuid4()}"
        with tempfile.TemporaryFile() as temporary:
            while part := await archivo.read(1024 * 1024):
                size += len(part)
                if size > settings.max_upload_bytes:
                    raise ServiceError(
                        "ARCHIVO_DEMASIADO_GRANDE", "El archivo supera el tamaño permitido.", 413
                    )
                if not sample:
                    sample = part[:1024]
                digest.update(part)
                temporary.write(part)
            if size == 0:
                raise ServiceError("ARCHIVO_VACIO", "El archivo está vacío.")
            mime = detect_mime(sample, archivo.content_type)
            temporary.seek(0)
            await asyncio.to_thread(storage.put, object_key, temporary, mime)
        source = {"key": object_key, "mime": mime, "sha256": digest.hexdigest(), "size": size}
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "sha256": source["sha256"],
                    "metadata": metadata.to_dict(),
                    "document_id": document_id,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        # If the transaction's outcome is uncertain, keep the blob for reconciliation.
        # Removing it on a connection error could destroy a successfully committed source.
        try:
            result, created = await asyncio.to_thread(
                repository.accept, owner, key, fingerprint, source, metadata, document_id
            )
        except ServiceError:
            # Explicit pre-commit rejections leave no document referencing this blob.
            await asyncio.to_thread(storage.delete, object_key)
            raise
        if not created:
            await asyncio.to_thread(storage.delete, object_key)
        status = 200 if result["estado"] in TERMINAL else 202
        return JSONResponse(result, status_code=status, headers={"Location": result["estado_url"]})

    @app.post("/v1/documents", status_code=202, summary="Recibir un documento")
    async def upload(request: Request, archivo: UploadFile = File(), metadatos: str = Form()):
        return await accept(request, archivo, metadatos)

    @app.post(
        "/v1/documents/{document_id}/versions", status_code=202, summary="Recibir una nueva versión"
    )
    async def upload_version(
        document_id: str, request: Request, archivo: UploadFile = File(), metadatos: str = Form()
    ):
        return await accept(request, archivo, metadatos, document_id)

    @app.get("/v1/admin/capabilities", include_in_schema=False)
    async def capabilities(request: Request):
        authenticate(request)
        profile = await asyncio.to_thread(repository.embedding_profile)
        stale = await asyncio.to_thread(repository.stale_profile_count, authenticate(request))
        return {
            "env_mode": settings.env_mode,
            "embedding_profile": profile,
            "stale_documents": stale,
        }

    @app.get("/v1/indexing-jobs", summary="Listar historial de trabajos")
    async def list_jobs(
        request: Request,
        status: str | None = Query(None),
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        return await asyncio.to_thread(
            repository.list_jobs, authenticate(request), status, limit, offset
        )

    @app.get("/v1/admin/embedding-profile", summary="Consultar el modelo de embeddings")
    async def embedding_profile(request: Request):
        authenticate(request)
        return await asyncio.to_thread(repository.embedding_profile)

    @app.patch("/v1/admin/embedding-profile", summary="Configurar el modelo de embeddings")
    async def update_embedding_profile(request: Request):
        authenticate(request)
        data = await body(request)
        return await asyncio.to_thread(repository.set_embedding_profile, data)

    @app.post("/v1/documents/{document_id}/reindex", summary="Crear una versión para reindexar")
    async def reindex(document_id: str, request: Request):
        return await asyncio.to_thread(repository.reindex, authenticate(request), document_id)

    @app.post(
        "/v1/admin/reindex-stale", summary="Reindexar documentos publicados con un perfil diferente"
    )
    async def reindex_stale(request: Request, limit: int = Query(100, ge=1, le=100)):
        return await asyncio.to_thread(repository.reindex_stale, authenticate(request), limit)

    @app.delete("/v1/documents/{document_id}", summary="Eliminar un documento de prueba")
    async def delete_test_document(document_id: str, request: Request):
        owner = authenticate(request)
        data = await body(request)
        deleted = await asyncio.to_thread(
            repository.delete_test_document,
            owner,
            document_id,
            data.get("confirmar_titulo"),
            settings.env_mode,
        )
        deleted["limpieza_pendiente"] = await cleanup_objects(document_id)
        return deleted

    @app.get("/v1/documents", summary="Listar documentos publicados")
    async def documents(
        request: Request,
        q: str = Query("", max_length=300),
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        return await asyncio.to_thread(
            repository.library.list, authenticate(request), q, limit, offset
        )

    @app.get("/v1/documents/{document_id}/chunks", summary="Leer fragmentos publicados")
    async def chunks(
        document_id: str,
        request: Request,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        version_id: str | None = None,
    ):
        return await asyncio.to_thread(
            repository.library.chunks, document_id, authenticate(request), limit, offset, version_id
        )

    @app.get("/v1/indexing-jobs/{job_id}", summary="Consultar el estado")
    async def status(job_id: str, request: Request):
        return await asyncio.to_thread(repository.get, job_id, authenticate(request))

    @app.post("/v1/indexing-jobs/{job_id}/cancel", summary="Cancelar la indexación")
    async def cancel(job_id: str, request: Request):
        return await asyncio.to_thread(repository.cancel, job_id, authenticate(request))

    @app.get("/v1/indexing-jobs/{job_id}/events", summary="Seguir el progreso")
    async def events(job_id: str, request: Request):
        owner = authenticate(request)
        current = await asyncio.to_thread(repository.get, job_id, owner)
        try:
            after = int(request.headers.get("last-event-id", "0"))
            if after < 0:
                raise ValueError
        except ValueError:
            raise ServiceError(
                "SECUENCIA_INVALIDA", "Last-Event-ID debe ser un número positivo o cero."
            ) from None
        if after > current["secuencia"]:
            raise ServiceError(
                "SECUENCIA_INVALIDA",
                "La secuencia supera el progreso disponible. Recargue el estado del trabajo.",
            )

        async def stream():
            sequence = after
            while not await request.is_disconnected():
                rows = await asyncio.to_thread(repository.events, job_id, sequence, owner)
                for row in rows:
                    sequence = row["secuencia"]
                    yield f"id: {sequence}\nevent: progreso\ndata: {json.dumps(row, ensure_ascii=False)}\n\n"
                    if row["estado"] in TERMINAL:
                        return
                if not rows:
                    current = await asyncio.to_thread(repository.get, job_id, owner)
                    if current["estado"] in TERMINAL:
                        return
                yield ": conexión activa\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/internal/indexing-jobs/{job_id}", include_in_schema=False)
    async def context(job_id: str):
        return await asyncio.to_thread(repository.context, job_id)

    async def body(request: Request) -> dict:
        try:
            value = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise ServiceError("SOLICITUD_INVALIDA", "Se requiere un objeto JSON válido.") from None
        if not isinstance(value, dict):
            raise ServiceError("SOLICITUD_INVALIDA", "Se requiere un objeto JSON válido.")
        return value

    @app.post("/internal/indexing-jobs/{job_id}/progress", include_in_schema=False)
    async def progress(job_id: str, request: Request):
        return await asyncio.to_thread(repository.progress, job_id, await body(request))

    @app.put("/internal/indexing-jobs/{job_id}/embedding-profile", include_in_schema=False)
    async def job_profile(job_id: str, request: Request):
        return await asyncio.to_thread(
            repository.set_job_embedding_profile, job_id, await body(request)
        )

    @app.post("/internal/indexing-jobs/{job_id}/timing", include_in_schema=False)
    async def timing(job_id: str, request: Request):
        return await asyncio.to_thread(repository.timing, job_id, await body(request))

    @app.post("/internal/indexing-jobs/{job_id}/complete", include_in_schema=False)
    async def complete(job_id: str, request: Request):
        return await asyncio.to_thread(repository.complete, job_id, await body(request))

    @app.post("/internal/indexing-jobs/{job_id}/fail", include_in_schema=False)
    async def fail(job_id: str, request: Request):
        data = await body(request)
        code = data.get("code", "REINTENTOS_AGOTADOS")
        if not isinstance(code, str):
            raise ServiceError("SOLICITUD_INVALIDA", "El código de error no es válido.")
        return await asyncio.to_thread(repository.fail, job_id, code)

    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.allowed_origins),
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "Last-Event-ID"],
            expose_headers=["Location"],
        )
    return app
