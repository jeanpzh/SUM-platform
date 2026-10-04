"""Query embeddings compatible with the profile fixed by the indexer."""

from __future__ import annotations

import hashlib
import json
import math
import time
from contextvars import ContextVar
from uuid import uuid4

import httpx
from sum_contracts.ai import AuditEvent
from sum_contracts.models import EmbeddingProfile, ServiceError

from .config import AiSettings

# Request context is isolated by asyncio task, including concurrent workflows.
embedding_context: ContextVar[tuple | None] = ContextVar("embedding_context", default=None)


class QueryEmbedder:
    def __init__(self, settings: AiSettings, quota=None):
        self.settings = settings
        self.quota = quota
        self.cache: dict[str, tuple[float, list[float]]] = {}

    async def embed(self, question: str, profile: EmbeddingProfile) -> list[float]:
        key = hashlib.sha256(json.dumps([question, profile.to_dict()], sort_keys=True).encode()).hexdigest()
        cached = self.cache.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        text = profile.query_prefix + question
        timeout = self.settings.embedding_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout) as client:
            if profile.model.startswith("ollama:"):
                model = profile.model.removeprefix("ollama:")
                tags = await client.get(self.settings.ollama_url + "/api/tags")
                tags.raise_for_status()
                current = next((item for item in tags.json().get("models", []) if item.get("model") == model or item.get("name") == model), None)
                if not current or current.get("digest", "").removeprefix("sha256:") != profile.revision.removeprefix("sha256:"):
                    raise ServiceError("EMBEDDING_PROFILE_UNAVAILABLE", "La revisión Ollama no coincide con el índice.", 503)
                response = await client.post(self.settings.ollama_url + "/api/embed", json={"model": model, "input": [text], "truncate": False})
                response.raise_for_status()
                vectors = response.json().get("embeddings")
            elif profile.model.startswith("openai:"):
                if not self.settings.openai_api_key or self.settings.embedding_input_usd_per_million is None:
                    raise ServiceError("EMBEDDING_PROFILE_UNAVAILABLE", "El perfil de embeddings no está disponible.", 503)
                model = profile.model.removeprefix("openai:")
                context = embedding_context.get()
                if self.quota is None or context is None:
                    raise ServiceError("AI_QUOTA_UNAVAILABLE", "No se pudo confirmar la cuota de embeddings.", 503)
                actor, recorder, usage = context
                estimated = min(8000, len(text) // 3 + 1)
                reservation = await self.quota.reserve(actor, "openai", model, estimated)
                used = estimated
                try:
                    response = await client.post("https://api.openai.com/v1/embeddings",
                        headers={"Authorization": "Bearer " + self.settings.openai_api_key},
                        json={"model": model, "input": [text], "dimensions": profile.dimension})
                    response.raise_for_status()
                    data = response.json()
                    if data.get("model") != model:
                        raise ServiceError("EMBEDDING_PROFILE_UNAVAILABLE", "El modelo de embeddings no coincide con el índice.", 503)
                    used = min(9000, int(data.get("usage", {}).get("total_tokens", estimated)))
                    vectors = [item["embedding"] for item in data.get("data", [])]
                finally:
                    await self.quota.settle(reservation, used)
                    cost = used * self.settings.embedding_input_usd_per_million / 1_000_000
                    usage.input_tokens += used
                    usage.estimated_cost_usd += cost
                    await recorder.record(AuditEvent(operation_id="embedding:" + uuid4().hex, kind="usage",
                        payload={"input_tokens": used, "output_tokens": 0, "estimated_cost_usd": cost,
                                 "pricing_date": self.settings.embedding_pricing_date.isoformat(), "usage_estimated": True}))
            elif profile.model.startswith("local:"):
                raise ServiceError("EMBEDDING_PROFILE_UNAVAILABLE", "El perfil local no está disponible en AI Service.", 503)
            else:
                info = await client.get(self.settings.embedding_url + "/info")
                info.raise_for_status()
                details = info.json()
                if details.get("model_id") != profile.model or details.get("model_sha") != profile.revision:
                    raise ServiceError("EMBEDDING_PROFILE_UNAVAILABLE", "La revisión del índice no coincide con el servidor de embeddings.", 503)
                response = await client.post(self.settings.embedding_url + "/embed",
                    json={"inputs": [text], "truncate": False, "normalize": True})
                response.raise_for_status()
                vectors = response.json()
        if not isinstance(vectors, list) or len(vectors) != 1 or not isinstance(vectors[0], list) or len(vectors[0]) != profile.dimension:
            raise ServiceError("EMBEDDING_INVALID", "El embedding de consulta no es compatible.", 503)
        vector = vectors[0]
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
            raise ServiceError("EMBEDDING_INVALID", "El embedding de consulta no es válido.", 503)
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            raise ServiceError("EMBEDDING_INVALID", "El embedding de consulta está vacío.", 503)
        normalized = [x / norm for x in vector]
        self.cache[key] = (time.monotonic() + 120, normalized)
        if len(self.cache) > 500:
            self.cache = {k: v for k, v in self.cache.items() if v[0] > time.monotonic()}
            while len(self.cache) > 500:
                self.cache.pop(next(iter(self.cache)))
        return normalized
