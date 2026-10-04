"""API→workflow→LangChain→pgvector→callback→SSE→metrics with no paid provider."""
import asyncio
import hashlib
import hmac
import json
import os
import time
from uuid import uuid4

import httpx
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from redis.asyncio import Redis
from sum_ai.config import ModelConfig
from sum_ai.quota import QuotaManager
from sum_ai.reporter import HttpAuditRecorder
from sum_ai.retrieval import PublishedRetriever, PublishedStore
from sum_ai.runner import AgentLimits, AgentRunner
from sum_ai.workflow import run_once
from sum_backend.ai_metrics import MetricsProjector
from sum_backend.ai_repository import AiRunRepository
from sum_backend.app import create_app
from sum_backend.config import Settings

from tests.integration.test_ai_published_retrieval import (
    CHUNK,
    DOC,
    SyntheticEmbedder,
    published_fixture,
)

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="AI Compose test profile required")


class ScriptedModel(BaseChatModel):
    calls: int = 0

    @property
    def _llm_type(self):
        return "integration-scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        reply = AIMessage(content="Evidencia suficiente.") if self.calls == 1 else AIMessage(content="", tool_calls=[{
            "id": "answer", "type": "tool_call", "name": "StructuredAnswer", "args": {
                "answer": "La versión publicada permanece disponible.", "citation_ids": [CHUNK]}}])
        return ChatResult(generations=[ChatGeneration(message=reply)])


class Registry:
    def __init__(self):
        self.model = ScriptedModel()

    def config(self, *_args):
        return ModelConfig(provider="ollama", model="fixture", input_usd_per_million=0,
                           output_usd_per_million=0, pricing_date="2026-10-03")

    def resolve(self, *_args):
        return self.model


class Catalog:
    async def admit_request(self, actor, key, fingerprint):
        redis = Redis.from_url(os.environ["REDIS_URL"])
        try:
            await QuotaManager(redis).admit_request(actor, key + fingerprint)
        finally:
            await redis.aclose()

    async def list_models(self):
        return [{"provider": "ollama", "model": "fixture", "available": True}]


def test_complete_audited_run_and_idempotent_metrics():
    async def exercise():
        with published_fixture():
            repo = AiRunRepository(os.environ["DATABASE_URL"], event_delay_seconds=3600)
            settings = Settings(os.environ["DATABASE_URL"], "a" * 32, "s" * 32, ai_identity_secret="i" * 32)
            app = create_app(settings, object(), object(), repo, Catalog())
            transport = httpx.ASGITransport(app=app)
            owner = "ai-test-" + str(uuid4())
            body = json.dumps({"question": "¿Qué versión se consulta?", "provider": "ollama", "model": "fixture", "document_ids": [DOC], "top_k": 4}).encode()
            def headers(method, path, content=b""):
                payload = json.dumps({"sub": owner, "role": "admin", "exp": int(time.time()) + 60,
                                      "method": method, "path": path, "body_sha256": hashlib.sha256(content).hexdigest()}).encode()
                return {"Authorization": "Bearer " + settings.admin_token, "X-Admin-Assertion": payload.hex() + "." + hmac.new(settings.ai_identity_secret.encode(), payload, hashlib.sha256).hexdigest(), "Content-Type": "application/json"}
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                path = "/v1/admin/ai/runs"
                response = await client.post(path, content=body, headers={**headers("POST", path, body), "Idempotency-Key": str(uuid4())})
                assert response.status_code == 202, response.text
                run_id = response.json()["run_id"]
                redis = Redis.from_url(os.environ["REDIS_URL"])
                store = PublishedStore(os.environ["RETRIEVAL_DATABASE_URL"])
                recorder = HttpAuditRecorder("http://test", settings.internal_token, run_id)
                await recorder.client.aclose()
                recorder.client = httpx.AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": "Bearer " + settings.internal_token}, timeout=5)
                try:
                    runner = AgentRunner(Registry(), PublishedRetriever(store, SyntheticEmbedder()), QuotaManager(redis), AgentLimits())
                    await run_once(run_id, runner, recorder)
                    final = repo.get(run_id, owner)
                    assert final["status"] == "completed"
                    assert final["result"]["citations"][0]["chunk_id"] == CHUNK
                    assert "retrieving" in final["result"]["timings"]
                    sse_path = f"{path}/{run_id}/events"
                    stream = await client.get(sse_path, headers=headers("GET", sse_path))
                    assert "event: audit" in stream.text and '"kind": "completed"' in stream.text
                    projector = MetricsProjector(repo.database)
                    projector.project()
                    first = projector.get_metrics(owner)
                    projector.project()
                    second = projector.get_metrics(owner)
                    assert first == second and first["summary"]["count"] == 1
                    assert first["quality"] is None
                    assert first["stages"][0]["mean_ms"] is not None
                finally:
                    await recorder.close()
                    await redis.aclose()
                    store.database.close()
                    with repo.database.connection() as conn:
                        conn.execute("DELETE FROM application.ai_runs WHERE owner_id=%s", (owner,))
                        conn.execute("DELETE FROM application.ai_metric_buckets WHERE owner_id=%s", (owner,))
                    repo.close()
    asyncio.run(exercise())
