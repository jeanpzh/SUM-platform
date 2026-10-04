from __future__ import annotations

import math
import re
import threading

from sum_contracts.models import EmbeddingProfile, ServiceError


def validate_vectors(vectors: list, count: int, dimension: int) -> list[list[float]]:
    if not isinstance(vectors, list) or len(vectors) != count:
        raise ServiceError(
            "MODELO_INCOMPATIBLE", "El modelo devolvió una cantidad inesperada de vectores."
        )
    for vector in vectors:
        if (
            not isinstance(vector, list)
            or len(vector) != dimension
            or any(type(x) not in {float, int} or not math.isfinite(x) for x in vector)
        ):
            raise ServiceError("MODELO_INCOMPATIBLE", "El modelo devolvió vectores inválidos.")
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            raise ServiceError("MODELO_INCOMPATIBLE", "El modelo devolvió un vector vacío.")
        for i in range(len(vector)):
            vector[i] /= norm
    return vectors


class TeiEmbeddingProvider:
    def __init__(self, url: str, model: str, revision: str, dimension: int, max_tokens: int):
        import httpx

        self.client = httpx.Client(base_url=url, timeout=120)
        self.model, self.revision, self.dimension, self.max_tokens = (
            model,
            revision,
            dimension,
            max_tokens,
        )
        self._profile = None
        self.lock = threading.Lock()

    @property
    def profile(self) -> EmbeddingProfile:
        with self.lock:
            if self._profile is None:
                response = self.client.get("/info")
                response.raise_for_status()
                info = response.json()
                actual_model, actual_revision = info.get("model_id"), info.get("model_sha")
                if (
                    actual_model != self.model
                    or not re.fullmatch(r"[0-9a-f]{40}", str(actual_revision))
                    or actual_revision != self.revision
                ):
                    raise ServiceError(
                        "MODELO_INCOMPATIBLE",
                        "El servidor de embeddings usa un modelo o revisión diferente.",
                    )
                if info.get("max_input_length", 0) < self.max_tokens:
                    raise ServiceError(
                        "MODELO_INCOMPATIBLE",
                        "El límite de tokens del servidor es inferior al configurado.",
                    )
                self._profile = EmbeddingProfile(
                    self.model, actual_revision, self.dimension, self.max_tokens
                )
            return self._profile

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        profile = self.profile
        response = self.client.post(
            "/embed",
            json={
                "inputs": [profile.passage_prefix + text for text in texts],
                "truncate": False,
                "normalize": True,
            },
        )
        response.raise_for_status()
        return validate_vectors(response.json(), len(texts), profile.dimension)

    def close(self):
        self.client.close()


class LocalEmbeddingProvider:
    """Optional local-model extra. One model instance per process, never per PDF."""

    def __init__(self, model: str, revision: str, dimension: int, max_tokens: int):
        self.model_id, self.revision, self.dimension, self.max_tokens = (
            model,
            revision,
            dimension,
            max_tokens,
        )
        self.model = None
        self._profile = None
        self.lock = threading.Lock()

    @property
    def profile(self) -> EmbeddingProfile:
        with self.lock:
            if self._profile is None:
                from huggingface_hub import HfApi
                from sentence_transformers import SentenceTransformer

                sha = HfApi().model_info(self.model_id, revision=self.revision).sha
                self.model = SentenceTransformer(self.model_id, revision=sha)
                if self.model.get_sentence_embedding_dimension() != self.dimension:
                    raise ServiceError(
                        "MODELO_INCOMPATIBLE",
                        "La dimensión del modelo no coincide con la configuración.",
                    )
                self._profile = EmbeddingProfile(
                    self.model_id, sha, self.dimension, self.max_tokens
                )
            return self._profile

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        profile = self.profile
        with self.lock:
            vectors = self.model.encode(
                [profile.passage_prefix + text for text in texts],
                batch_size=len(texts),
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()
        return validate_vectors(vectors, len(texts), profile.dimension)

    def close(self):
        self.model = None


class OllamaEmbeddingProvider:
    """Ollama's native /api/embed API; the registry digest pins the model revision."""

    def __init__(self, url: str, model: str, revision: str, dimension: int, max_tokens: int):
        import httpx

        self.client = httpx.Client(base_url=url, timeout=180)
        self.model, self.revision, self.dimension, self.max_tokens = (
            model,
            revision,
            dimension,
            max_tokens,
        )
        self._profile = None

    @property
    def profile(self):
        if self._profile is None:
            response = self.client.get("/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            found = next(
                (
                    item
                    for item in models
                    if item.get("name") == self.model
                    or item.get("model") == self.model
                    or item.get("name", "").removesuffix(":latest") == self.model
                ),
                None,
            )
            if not found:
                raise ServiceError(
                    "MODELO_INCOMPATIBLE", "El modelo configurado no está instalado en Ollama."
                )
            digest = found.get("digest")
            if (
                not isinstance(digest, str)
                or len(digest) < 32
                or (self.revision != "auto" and self.revision != digest)
            ):
                raise ServiceError(
                    "MODELO_INCOMPATIBLE", "La revisión del modelo de Ollama cambió."
                )
            self.revision = digest
            sample = self.client.post("/api/embed", json={"model": self.model, "input": ["test"]})
            sample.raise_for_status()
            vectors = sample.json().get("embeddings", [])
            if len(vectors) != 1 or len(vectors[0]) != self.dimension:
                raise ServiceError(
                    "MODELO_INCOMPATIBLE",
                    "La dimensión del modelo Ollama no coincide con el índice.",
                )
            self._profile = EmbeddingProfile(
                "ollama:" + self.model,
                digest,
                self.dimension,
                self.max_tokens,
                passage_prefix="",
                query_prefix="",
            )
        return self._profile

    def embed_passages(self, texts):
        profile = self.profile
        response = self.client.post(
            "/api/embed",
            json={
                "model": self.model,
                "input": [profile.passage_prefix + t for t in texts],
                "truncate": False,
            },
        )
        response.raise_for_status()
        return validate_vectors(response.json().get("embeddings"), len(texts), profile.dimension)

    def close(self):
        self.client.close()


class OpenAIEmbeddingProvider:
    """Official OpenAI embeddings endpoint; API keys remain in indexer environment."""

    def __init__(
        self, url: str, key: str, model: str, revision: str, dimension: int, max_tokens: int
    ):
        import httpx

        if not key:
            raise ValueError("OPENAI_API_KEY debe configurarse para el proveedor OpenAI.")
        self.client = httpx.Client(
            base_url=url, headers={"Authorization": "Bearer " + key}, timeout=120
        )
        self.model, self.revision, self.dimension, self.max_tokens = (
            model,
            revision,
            dimension,
            max_tokens,
        )
        self._profile = None

    @property
    def profile(self):
        if self._profile is None:
            response = self.client.post(
                "/embeddings",
                json={
                    "model": self.model,
                    "input": "profile check",
                    "encoding_format": "float",
                    "dimensions": self.dimension,
                },
            )
            response.raise_for_status()
            data = response.json()
            vectors = data.get("data", [])
            if (
                data.get("model") != self.model
                or len(vectors) != 1
                or len(vectors[0].get("embedding", [])) != self.dimension
            ):
                raise ServiceError(
                    "MODELO_INCOMPATIBLE", "OpenAI devolvió un modelo o dimensión diferente."
                )
            self._profile = EmbeddingProfile(
                "openai:" + self.model,
                self.revision,
                self.dimension,
                self.max_tokens,
                passage_prefix="",
                query_prefix="",
            )
        return self._profile

    def embed_passages(self, texts):
        profile = self.profile
        response = self.client.post(
            "/embeddings",
            json={
                "model": self.model,
                "input": [profile.passage_prefix + t for t in texts],
                "encoding_format": "float",
                "dimensions": profile.dimension,
            },
        )
        response.raise_for_status()
        data = response.json()
        vectors = sorted(data.get("data", []), key=lambda row: row.get("index", -1))
        if data.get("model") != self.model:
            raise ServiceError("MODELO_INCOMPATIBLE", "OpenAI devolvió un modelo inesperado.")
        return validate_vectors(
            [row.get("embedding") for row in vectors], len(texts), profile.dimension
        )

    def close(self):
        self.client.close()
