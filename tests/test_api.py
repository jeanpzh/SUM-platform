import asyncio
import copy
import json
import tempfile
import threading
from pathlib import Path
from uuid import uuid4

from sum_contracts.models import CONTRACT_VERSION, JobStopped, ServiceError, Status
from sum_storage.objects import LocalStorage

from tests.support import AsyncTests

try:
    import httpx
    from sum_backend.app import create_app
    from sum_backend.config import Settings
except ImportError:
    httpx = None


class MemoryJobs:
    """API boundary double; PostgreSQL transaction checks need integration tests."""

    def __init__(self):
        self.rows, self.keys, self.contexts, self.history = {}, {}, {}, {}
        self.lock = threading.RLock()

    def accept(self, owner, key, fingerprint, source, metadata, document_id=None):
        with self.lock:
            if (owner, key) in self.keys:
                job_id, old = self.keys[(owner, key)]
                if old != fingerprint:
                    raise ServiceError(
                        "IDEMPOTENCIA_CONFLICTO",
                        "La clave ya fue usada con contenido diferente.",
                        409,
                    )
                return copy.deepcopy(self.rows[job_id]), False
            job_id, version = str(uuid4()), str(uuid4())
            document_id = document_id or str(uuid4())
            row = {
                "documento_id": document_id,
                "version_id": version,
                "trabajo_id": job_id,
                "estado": Status.QUEUED,
                "etapa": None,
                "mensaje": "Documento recibido. La indexación está pendiente.",
                "estado_url": f"/v1/indexing-jobs/{job_id}",
                "secuencia": 1,
                "progreso": {},
            }
            self.rows[job_id] = row
            self.keys[(owner, key)] = (job_id, fingerprint)
            self.contexts[job_id] = {
                "contract_version": CONTRACT_VERSION,
                "job_id": job_id,
                "document_id": document_id,
                "version_id": version,
                "metadata": metadata.to_dict(),
                "source": source,
                "status": Status.QUEUED,
            }
            self.history[job_id] = [copy.deepcopy(row)]
            return copy.deepcopy(row), True

    def get(self, job_id, owner=None):
        if job_id not in self.rows:
            raise ServiceError("TRABAJO_NO_ENCONTRADO", "El trabajo no existe.", 404)
        return copy.deepcopy(self.rows[job_id])

    def context(self, job_id):
        self.get(job_id)
        if self.rows[job_id]["estado"] == Status.CANCELLED:
            raise JobStopped()
        return copy.deepcopy(self.contexts[job_id])

    def cancel(self, job_id, owner):
        self.get(job_id, owner)
        self.rows[job_id].update(
            estado=Status.CANCELLED, secuencia=2, mensaje="La indexación fue cancelada."
        )
        self.history[job_id].append(copy.deepcopy(self.rows[job_id]))
        return self.get(job_id, owner)

    def events(self, job_id, after, owner):
        self.get(job_id, owner)
        return [copy.deepcopy(row) for row in self.history[job_id] if row["secuencia"] > after]


class ApiTests(AsyncTests):
    async def asyncSetUp(self):
        if httpx is None:
            self.skipTest("Instale las dependencias de Backend API para verificar HTTP.")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage = LocalStorage(Path(self.directory.name))
        self.jobs = MemoryJobs()
        self.settings = Settings("unused", "a" * 32, "s" * 32, max_upload_bytes=1024)
        self.app = create_app(self.settings, self.jobs, self.storage)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {self.settings.admin_token}"},
        )
        self.addAsyncCleanup(self.client.aclose)

    async def upload(
        self,
        key="document-1",
        content=b"Documento academico sintetico para indexar.",
        metadata=None,
        mime="text/plain",
    ):
        return await self.client.post(
            "/v1/documents",
            headers={"Idempotency-Key": key},
            files={"archivo": ("document.txt", content, mime)},
            data={
                "metadatos": json.dumps(
                    metadata or {"titulo": "Documento de prueba", "tipo_documento": "reglamento"}
                )
            },
        )

    async def test_parallel_documents_receive_independent_202_and_metadata(self):
        responses = await asyncio.gather(*(self.upload(f"document-{i}") for i in range(4)))
        self.assertEqual([r.status_code for r in responses], [202] * 4)
        self.assertEqual(len({r.json()["trabajo_id"] for r in responses}), 4)
        for response in responses:
            self.assertEqual(response.headers["location"], response.json()["estado_url"])
            self.assertIn("Documento recibido", response.json()["mensaje"])
            context = self.jobs.contexts[response.json()["trabajo_id"]]
            self.assertEqual(context["metadata"]["tipo_documento"], "reglamento")
            self.assertTrue(self.storage.exists(context["source"]["key"]))

    async def test_idempotent_retry_returns_same_job_and_removes_redundant_blob(self):
        first, second = await self.upload(), await self.upload()
        self.assertEqual(first.json()["trabajo_id"], second.json()["trabajo_id"])
        self.assertEqual(len(list((Path(self.directory.name) / "originals").iterdir())), 1)
        conflict = await self.upload(content=b"Otro documento academico con contenido diferente.")
        self.assertEqual(conflict.status_code, 409)
        self.assertIn("contenido diferente", conflict.json()["mensaje"])
        self.assertEqual(len(list((Path(self.directory.name) / "originals").iterdir())), 1)

    async def test_cors_headers_are_present_on_authentication_errors(self):
        settings = Settings(
            "unused", "a" * 32, "s" * 32, allowed_origins=("http://localhost:5173",)
        )
        app = create_app(settings, self.jobs, self.storage)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/v1/documents", headers={"Origin": "http://localhost:5173"}
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")

    async def test_errors_are_in_spanish_and_unsupported_formats_are_rejected(self):
        invalid = await self.upload(metadata={"titulo": "Prueba", "tipo_documento": "PDF"})
        self.assertEqual(invalid.status_code, 422)
        self.assertIn("no es válido", invalid.json()["mensaje"])
        unsupported = await self.upload(
            content=b"PK zip data",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertEqual(unsupported.status_code, 415)
        self.assertIn("Se admiten", unsupported.json()["mensaje"])
        missing = await self.client.get("/does-not-exist")
        self.assertEqual(missing.json()["mensaje"], "La ruta no existe.")

    async def test_upload_limit_and_missing_idempotency_key(self):
        oversized = await self.upload(content=b"a" * 1025)
        self.assertEqual(oversized.status_code, 413)
        missing = await self.client.post(
            "/v1/documents",
            files={"archivo": ("a.txt", b"Texto sintetico", "text/plain")},
            data={"metadatos": '{"titulo":"Prueba","tipo_documento":"otro"}'},
        )
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(missing.json()["codigo"], "CLAVE_IDEMPOTENCIA_INVALIDA")

    async def test_chunked_request_cannot_bypass_body_limit(self):
        async def body():
            yield b'--test\r\nContent-Disposition: form-data; name="archivo"; filename="a.txt"\r\nContent-Type: text/plain\r\n\r\n'
            yield b"x" * 70000
            yield b"\r\n--test--\r\n"

        response = await self.client.post(
            "/v1/documents",
            content=body(),
            headers={
                "Content-Type": "multipart/form-data; boundary=test",
                "Idempotency-Key": "too-large",
            },
        )
        self.assertEqual(response.status_code, 413)

    async def test_service_credentials_and_public_credentials_are_separate(self):
        response = await self.upload()
        job_id = response.json()["trabajo_id"]
        denied = await self.client.get(f"/internal/indexing-jobs/{job_id}")
        self.assertEqual(denied.status_code, 401)
        allowed = await self.client.get(
            f"/internal/indexing-jobs/{job_id}",
            headers={"Authorization": f"Bearer {self.settings.internal_token}"},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("source", allowed.json())
        denied_public = await self.client.get(
            response.json()["estado_url"],
            headers={"Authorization": f"Bearer {self.settings.internal_token}"},
        )
        self.assertEqual(denied_public.status_code, 401)

    async def test_cancelled_job_stream_replays_only_events_after_cursor(self):
        response = await self.upload()
        job_id = response.json()["trabajo_id"]
        cancelled = await self.client.post(f"/v1/indexing-jobs/{job_id}/cancel")
        self.assertEqual(cancelled.json()["estado"], Status.CANCELLED)
        stream = await self.client.get(
            f"/v1/indexing-jobs/{job_id}/events", headers={"Last-Event-ID": "1"}
        )
        self.assertIn("id: 2", stream.text)
        self.assertNotIn("id: 1", stream.text)
        self.assertIn("cancelado", stream.text)
        future = await self.client.get(
            f"/v1/indexing-jobs/{job_id}/events", headers={"Last-Event-ID": "3"}
        )
        self.assertEqual(future.status_code, 422)


class EmbeddingHttpTests(AsyncTests):
    async def test_tei_adapter_preserves_spanish_and_applies_model_prefix(self):
        if httpx is None:
            self.skipTest("Instale HTTPX para verificar el adaptador de embeddings.")
        from sum_indexer.embeddings import TeiEmbeddingProvider

        requests = []
        revision = "a" * 40

        def handle(request):
            if request.url.path == "/info":
                return httpx.Response(
                    200,
                    json={"model_id": "test-model", "model_sha": revision, "max_input_length": 512},
                )
            requests.append(json.loads(request.content))
            return httpx.Response(200, json=[[3.0, 4.0, 0.0]])

        provider = TeiEmbeddingProvider("http://test", "test-model", revision, 3, 512)
        provider.client.close()
        provider.client = httpx.Client(
            base_url="http://test", transport=httpx.MockTransport(handle)
        )
        try:
            vectors = provider.embed_passages(["Créditos y matrícula académica"])
            self.assertEqual(requests[0]["inputs"], ["passage: Créditos y matrícula académica"])
            self.assertFalse(requests[0]["truncate"])
            self.assertEqual(provider.profile.revision, revision)
            self.assertAlmostEqual(vectors[0][0], 0.6)
        finally:
            provider.close()
