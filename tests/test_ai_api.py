import hashlib
import hmac
import json
import time

import httpx
from sum_backend.app import create_app
from sum_backend.config import Settings
from sum_contracts.models import ServiceError

from tests.support import AsyncTests
from tests.test_api import MemoryJobs


class MemoryAi:
    def __init__(self):
        self.rows = {}
        self.keys = {}

    def create(self, owner, key, request):
        existing = self.keys.get((owner, key))
        if existing:
            if existing[1] != request.fingerprint():
                raise ServiceError("AI_IDEMPOTENCY_CONFLICT", "Conflict", 409)
            return existing[0], False
        row = {"run_id": "2ca19fd6-e1b6-4aad-8b8c-15a05944a85a", "status": "queued", "sequence": 0}
        self.rows[row["run_id"]] = row
        self.keys[(owner, key)] = (row, request.fingerprint())
        return row, True

    def get(self, run_id, owner):
        return self.rows[run_id]

    def events(self, run_id, after, owner):
        return []


class ModelClient:
    async def admit_request(self, owner, key, fingerprint):
        if key == "limited":
            error = ServiceError("AI_ADMIN_RATE_LIMIT", "Limited", 429)
            error.retry_after = 37
            raise error

    async def list_models(self):
        return [{"provider": "ollama", "model": "llama3.2", "available": True}]


class AiApiTests(AsyncTests):
    async def asyncSetUp(self):
        from unittest.mock import Mock

        self.settings = Settings("unused", "a" * 32, "s" * 32, ai_identity_secret="i" * 32)
        self.ai = MemoryAi()
        storage = Mock()
        self.app = create_app(self.settings, MemoryJobs(), storage, self.ai, ModelClient())
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),
                                        base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    def headers(self, method, path, body=b""):
        claims = {"sub": "admin-1", "role": "admin", "exp": int(time.time()) + 60,
                  "method": method, "path": path, "body_sha256": hashlib.sha256(body).hexdigest()}
        payload = json.dumps(claims, separators=(",", ":")).encode()
        signature = hmac.new(self.settings.ai_identity_secret.encode(), payload, hashlib.sha256).hexdigest()
        return {"Authorization": "Bearer " + self.settings.admin_token,
                "X-Admin-Assertion": payload.hex() + "." + signature}

    async def test_invalid_input_and_replay(self):
        path = "/v1/admin/ai/runs"
        body = json.dumps({"question": "¿Qué indica la norma?", "provider": "ollama", "model": "llama3.2"}).encode()
        headers = {**self.headers("POST", path, body), "Idempotency-Key": "same", "Content-Type": "application/json"}
        one = await self.client.post(path, content=body, headers=headers)
        assert one.status_code == 202, one.text
        two = await self.client.post(path, content=body, headers=headers)
        assert two.status_code == 202
        assert two.json()["run_id"] == one.json()["run_id"]
        other = json.dumps({"question": "Otra pregunta", "provider": "ollama", "model": "llama3.2"}).encode()
        conflict = await self.client.post(path, content=other, headers={**self.headers("POST", path, other), "Idempotency-Key": "same", "Content-Type": "application/json"})
        assert conflict.status_code == 409
        invalid = await self.client.post(path, content=b'{"question":"x","provider":"ollama","model":"llama3.2"}',
            headers={**self.headers("POST", path, b'{"question":"x","provider":"ollama","model":"llama3.2"}'), "Idempotency-Key": "new"})
        assert invalid.status_code == 422

    async def test_browser_identity_without_signature_is_rejected(self):
        result = await self.client.get("/v1/admin/ai/models", headers={
            "Authorization": "Bearer " + self.settings.admin_token,
            "X-Admin-Identity": "admin-1",
        })
        assert result.status_code == 401

    async def test_quota_rejected_before_creating_run(self):
        path = "/v1/admin/ai/runs"
        body = json.dumps({"question": "Otra consulta", "provider": "ollama", "model": "llama3.2"}).encode()
        response = await self.client.post(path, content=body, headers={**self.headers("POST", path, body),
            "Idempotency-Key": "limited", "Content-Type": "application/json"})
        assert response.status_code == 429
        assert response.headers["retry-after"] == "37"
        assert not self.ai.rows
