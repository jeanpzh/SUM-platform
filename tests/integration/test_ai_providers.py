"""Versioned configurations use real PostgreSQL and never call a cloud model."""
import os
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import delete, select
from sum_backend.ai_providers import ProviderRepository, connections, revisions
from sum_contracts.ai_providers import ProviderInput
from sum_contracts.models import ServiceError
from sum_database import SqlDatabase

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Compose test profile required")


def test_encrypted_versions_ownership_and_disable():
    database = SqlDatabase(os.environ["DATABASE_URL"], 3, 3000)
    cleanup = SqlDatabase(os.environ["TEST_DATABASE_URL"], 1, 3000)
    owner = "providers-test-" + str(uuid4())
    repo = ProviderRepository(database, Fernet.generate_key().decode(), ("localhost",))
    data = ProviderInput(provider="groq", name="Research", base_url="https://api.groq.com/openai/v1",
        api_key="secret-test-groq", models=[dict(model="openai/gpt-oss-20b", input_usd_per_million=1,
        output_usd_per_million=2, pricing_date="2026-10-03")])
    identifier = None
    try:
        one = repo.save(owner, data)
        identifier = UUID(one["id"])
        assert one["revision"] == 1 and one["has_api_key"]
        assert "secret-test-groq" not in str(repo.list(owner))
        assert repo.list("other-admin") == []
        with database.engine.begin() as conn:
            encrypted = conn.scalar(select(revisions.c.encrypted_key).where(revisions.c.config_id == identifier))
        assert encrypted != "secret-test-groq" and "secret-test-groq" not in encrypted
        changed = data.model_copy(update={"enabled": False, "api_key": __import__("pydantic").SecretStr(""), "expected_revision": 1})
        two = repo.save(owner, changed, one["id"])
        assert two["revision"] == 2 and two["has_api_key"]
        assert repo.runtime(owner, identifier, 1).api_key.get_secret_value() == "secret-test-groq"
        assert not repo.catalog(owner)[0]["available"]
        with pytest.raises(ServiceError) as stale:
            repo.runtime(owner, identifier, 1, current=True)
        assert stale.value.status == 409
        with pytest.raises(ServiceError):
            repo.save(owner, changed, one["id"])
        with pytest.raises(ServiceError) as denied:
            repo.runtime("other-admin", identifier, 1)
        assert denied.value.status == 404
        custom = data.model_copy(update={"provider": "custom", "base_url": "http://unapproved:8080/v1"})
        with pytest.raises(ServiceError) as host:
            repo.save(owner, custom)
        assert host.value.code == "AI_PROVIDER_HOST_DENIED"
    finally:
        if identifier:
            with cleanup.engine.begin() as conn:
                conn.execute(delete(revisions).where(revisions.c.config_id == identifier))
                conn.execute(delete(connections).where(connections.c.id == identifier))
        database.close()
        cleanup.close()


def test_provider_api_pins_revision_and_never_returns_public_secret():
    import asyncio
    import hashlib
    import hmac
    import json
    import time
    from unittest.mock import Mock

    import httpx
    from sum_backend.ai_repository import AiRunRepository
    from sum_backend.ai_tables import runs
    from sum_backend.app import create_app
    from sum_backend.config import Settings

    async def exercise():
        owner = "provider-api-" + str(uuid4())
        cipher = Fernet.generate_key().decode()
        settings = Settings(os.environ["DATABASE_URL"], "a" * 32, "s" * 32,
            ai_identity_secret="i" * 32, ai_provider_encryption_key=cipher)
        repository = AiRunRepository(settings.database_url, event_delay_seconds=3600)
        class Catalog:
            async def list_models(self):
                return []
            async def admit_request(self, *_):
                pass
        app = create_app(settings, Mock(), Mock(), repository, Catalog())
        def headers(method, path, body=b""):
            claims = dict(sub=owner, role="admin", exp=int(time.time()) + 60, method=method,
                path=path, body_sha256=hashlib.sha256(body).hexdigest())
            data = json.dumps(claims).encode()
            return {"Authorization": "Bearer " + settings.admin_token, "Content-Type": "application/json",
                "X-Admin-Assertion": data.hex() + "." + hmac.new(settings.ai_identity_secret.encode(), data, hashlib.sha256).hexdigest()}
        config_id = None
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                path = "/v1/admin/ai/providers"
                body = json.dumps(dict(provider="groq", name="API fixture", base_url="https://api.groq.com/openai/v1",
                    api_key="fixture-api-secret", models=[dict(model="fixture", input_usd_per_million=1,
                    output_usd_per_million=2, pricing_date="2026-10-03")])).encode()
                saved = await client.post(path, content=body, headers=headers("POST", path, body))
                assert saved.status_code == 201
                config_id = UUID(saved.json()["id"])
                assert "fixture-api-secret" not in saved.text and "api_key" not in saved.json()
                query_path = "/v1/admin/ai/runs"
                body = json.dumps(dict(question="Pregunta de una norma", provider="groq", model="fixture",
                    provider_config_id=str(config_id), provider_revision=1)).encode()
                accepted = await client.post(query_path, content=body,
                    headers={**headers("POST", query_path, body), "Idempotency-Key": str(uuid4())})
                assert accepted.status_code == 202
                run_id = accepted.json()["run_id"]
                view_path = query_path + "/" + run_id
                viewed = await client.get(view_path, headers=headers("GET", view_path))
                assert viewed.json()["configuration"]["revision"] == 1
                assert "fixture-api-secret" not in viewed.text
                edit_path = path + "/" + str(config_id)
                updated = {key: value for key, value in saved.json().items() if key not in {"id", "revision", "created_at", "has_api_key"}}
                updated.update(api_key="", enabled=False, expected_revision=1)
                body = json.dumps(updated).encode()
                edited = await client.post(edit_path, content=body, headers=headers("POST", edit_path, body))
                assert edited.status_code == 200 and edited.json()["revision"] == 2
                runtime = await client.get("/internal/ai/runs/" + run_id,
                    headers={"Authorization": "Bearer " + settings.internal_token})
                assert runtime.status_code == 200
                assert runtime.json()["provider_runtime"]["revision"] == 1
                assert runtime.json()["provider_runtime"]["api_key"] == "fixture-api-secret"
                denied = await client.get("/internal/ai/runs/" + run_id)
                assert denied.status_code == 401
        finally:
            with repository.database.engine.begin() as conn:
                conn.execute(delete(runs).where(runs.c.owner_id == owner))
            if config_id:
                cleanup = SqlDatabase(os.environ["TEST_DATABASE_URL"], 1, 3000)
                with cleanup.engine.begin() as conn:
                    conn.execute(delete(revisions).where(revisions.c.config_id == config_id))
                    conn.execute(delete(connections).where(connections.c.id == config_id))
                cleanup.close()
            repository.close()
    asyncio.run(exercise())
