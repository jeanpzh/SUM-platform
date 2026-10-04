from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import inngest
import inngest.fast_api
from fastapi import FastAPI
from sum_storage.objects import from_env

from .chunking import HuggingFaceTokenizer
from .config import Settings
from .cpu import CpuPool
from .embeddings import (
    LocalEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    TeiEmbeddingProvider,
)
from .pipeline import Pipeline
from .reporter import HttpJobReporter
from .vectors import PgVectorRepository
from .workflows import register


def build_provider(settings, profile):
    model, revision, dimension, max_tokens = (
        profile["model"],
        profile["revision"],
        profile["dimension"],
        profile["max_tokens"],
    )
    if model.startswith("ollama:"):
        return OllamaEmbeddingProvider(
            settings.ollama_url, model.removeprefix("ollama:"), revision, dimension, max_tokens
        )
    if model.startswith("openai:"):
        return OpenAIEmbeddingProvider(
            settings.openai_url,
            settings.openai_api_key,
            model.removeprefix("openai:"),
            revision,
            dimension,
            max_tokens,
        )
    if model.startswith("local:"):
        return LocalEmbeddingProvider(model.removeprefix("local:"), revision, dimension, max_tokens)
    return TeiEmbeddingProvider(settings.embedding_url, model, revision, dimension, max_tokens)


def create_app() -> FastAPI:
    settings = Settings.from_env()
    if os.environ.get("INNGEST_DEV", "").lower() not in {"1", "true"} and not os.environ.get(
        "INNGEST_SIGNING_KEY"
    ):
        raise ValueError(
            "Configure INNGEST_SIGNING_KEY para autenticar las invocaciones en producción."
        )
    storage = from_env()
    reporter = HttpJobReporter(settings.backend_url, settings.service_token)
    cpu = CpuPool(settings.cpu_processes, settings.stage_timeout)
    vectors = PgVectorRepository(settings.database_url, settings.writing_concurrency + 2)
    if settings.embedding_driver == "tei":
        embeddings = TeiEmbeddingProvider(
            settings.embedding_url,
            settings.model,
            settings.revision,
            settings.dimension,
            settings.max_tokens,
        )
    elif settings.embedding_driver == "local":
        embeddings = LocalEmbeddingProvider(
            settings.model, settings.revision, settings.dimension, settings.max_tokens
        )
    elif settings.embedding_driver == "ollama":
        embeddings = OllamaEmbeddingProvider(
            settings.ollama_url,
            settings.model,
            settings.revision,
            settings.dimension,
            settings.max_tokens,
        )
    elif settings.embedding_driver == "openai":
        embeddings = OpenAIEmbeddingProvider(
            settings.openai_url,
            settings.openai_api_key,
            settings.model,
            settings.revision,
            settings.dimension,
            settings.max_tokens,
        )
    else:
        raise ValueError("EMBEDDING_DRIVER debe ser tei, ollama, openai o local.")
    pipeline = Pipeline(
        settings,
        storage,
        reporter,
        cpu,
        embeddings,
        vectors,
        lambda profile: HuggingFaceTokenizer(settings.tokenizer_model, settings.tokenizer_revision),
        embedding_factory=lambda profile: build_provider(settings, profile),
    )

    @asynccontextmanager
    async def lifespan(app):
        await asyncio.to_thread(vectors.open)
        await cpu.start()
        try:
            yield
        finally:
            await cpu.close()
            await reporter.close()
            await asyncio.to_thread(embeddings.close)
            await asyncio.to_thread(vectors.close)

    app = FastAPI(title="SUM — Indexador interno", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"estado": "disponible"}

    client = inngest.Inngest(app_id="sum-indexer", logger=logging.getLogger("sum.indexer"))
    inngest.fast_api.serve(app, client, register(client, pipeline))
    return app
