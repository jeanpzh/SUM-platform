"""Published-only vector retrieval with generation pinning and rank fusion."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, cast, column, select, table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sum_contracts.ai import Evidence, RunContext
from sum_contracts.models import EmbeddingProfile, ServiceError
from sum_database import SqlDatabase


@dataclass(frozen=True)
class RetrievalBatch:
    evidence: tuple[Evidence, ...]
    pinned: dict[str, str]
    profiles: tuple[EmbeddingProfile, ...] = ()


class PublishedStore:
    catalog = table("published_catalog", column("document_id", PgUUID),
                    column("generation_id", PgUUID), column("version_id", PgUUID),
                    column("publication_metadata", JSONB), column("embedding_profile", JSONB),
                    schema="institutional")
    def __init__(self, database_url: str):
        self.database = SqlDatabase(database_url, 5, 3000)

    chunks = table("published_chunks", column("id", PgUUID), column("document_id", PgUUID),
        column("version_id", PgUUID), column("generation_id", PgUUID), column("page", Integer),
        column("locator", String), column("content", String), column("ordinal", Integer),
        column("model", String), column("revision", String), column("dimension", Integer),
        column("embedding", Vector(768)), schema="institutional")

    @staticmethod
    def evidence_columns(chunks):
        return [chunks.c.id.label("chunk_id"), chunks.c.document_id, chunks.c.version_id,
                chunks.c.generation_id, chunks.c.page, chunks.c.locator, chunks.c.content.label("text")]

    def profiles(self, ids: tuple[str, ...]) -> list[EmbeddingProfile]:
        query = select(self.catalog.c.embedding_profile).distinct().limit(3)
        if ids:
            query = query.where(self.catalog.c.document_id.in_([UUID(value) for value in ids]))
        with self.database.engine.begin() as conn:
            rows = conn.execute(query).mappings().all()
        if len(rows) > 2:
            raise ServiceError("EMBEDDING_PROFILES_EXCEEDED", "Hay demasiados perfiles publicados.", 422)
        return [EmbeddingProfile(**row["embedding_profile"]) for row in rows]

    def snapshot(self, ids: tuple[str, ...]) -> dict[str, str]:
        query = select(self.catalog.c.document_id, self.catalog.c.generation_id).limit(10001)
        if ids:
            query = query.where(self.catalog.c.document_id.in_([UUID(value) for value in ids]))
        with self.database.engine.begin() as conn:
            rows = conn.execute(query).mappings().all()
        if len(rows) > 10000:
            raise ServiceError("AI_CORPUS_SCOPE_LIMIT", "Seleccione documentos para acotar la búsqueda.", 422)
        return {str(row["document_id"]): str(row["generation_id"]) for row in rows}

    def search(self, vector: list[float], profile: EmbeddingProfile, ids: tuple[str, ...], top_k: int):
        if profile.dimension != 768:
            raise ServiceError("EMBEDDING_PROFILE_UNAVAILABLE", "La dimensión del índice no está admitida.", 503)
        c = self.chunks.c
        distance = cast(c.embedding, Vector(768)).cosine_distance(vector)
        query = select(*self.evidence_columns(self.chunks), distance.label("score")).where(
            c.model == profile.model, c.revision == profile.revision, c.dimension == profile.dimension)
        if ids:
            query = query.where(c.document_id.in_([UUID(value) for value in ids]))
        with self.database.engine.begin() as conn:
            return conn.execute(query.order_by(distance, c.id).limit(top_k)).mappings().all()

    def current(self, pinned):
        actual = self.snapshot(tuple(pinned)) if pinned else {}
        return all(actual.get(doc) == generation for doc, generation in pinned.items())

    def adjacent(self, generation_id, chunk_id, radius):
        if not 0 <= radius <= 2:
            raise ServiceError("AI_INPUT_INVALID", "El radio de contexto no es válido.")
        center = self.chunks.alias("center")
        c = self.chunks.c
        query = select(*self.evidence_columns(self.chunks)).select_from(self.chunks.join(center,
            center.c.generation_id == c.generation_id)).where(center.c.id == UUID(chunk_id),
            c.generation_id.in_([UUID(value) for value in (generation_id if isinstance(generation_id, tuple) else (generation_id,))]), c.ordinal.between(center.c.ordinal - radius,
            center.c.ordinal + radius)).order_by(c.ordinal).limit(5)
        with self.database.engine.begin() as conn:
            return conn.execute(query).mappings().all()

    def metadata(self, document_id, generation_id):
        query = select(self.catalog.c.publication_metadata, self.catalog.c.version_id).where(
            self.catalog.c.document_id == UUID(document_id), self.catalog.c.generation_id == UUID(generation_id))
        with self.database.engine.begin() as conn:
            row = conn.execute(query).mappings().first()
        if row is None:
            raise ServiceError("CORPUS_CHANGED", "La publicación cambió durante la ejecución.", 409)
        return {"document_id": document_id, "generation_id": generation_id,
                "version_id": str(row["version_id"]), "metadata": row["publication_metadata"]}

    def metadata_batch(self, pinned: dict[str, str]):
        """One bound query for metadata and declared relationships of up to eight documents."""
        query = select(self.catalog).where(self.catalog.c.document_id.in_([UUID(value) for value in pinned]))
        with self.database.engine.begin() as conn:
            rows = conn.execute(query).mappings().all()
        if len(rows) != len(pinned) or any(str(row["generation_id"]) != pinned[str(row["document_id"])] for row in rows):
            raise ServiceError("CORPUS_CHANGED", "La publicación cambió durante la consulta.", 409)
        return [{"document_id": str(row["document_id"]), "generation_id": str(row["generation_id"]),
                 "version_id": str(row["version_id"]), "metadata": row["publication_metadata"]} for row in rows]


class PublishedRetriever:
    def __init__(self, store: PublishedStore, embedder):
        self.store, self.embedder = store, embedder
        self._pins: dict[str, dict[str, str]] = {}

    def pin(self, run_id, batch: RetrievalBatch):
        self._pins[str(run_id)] = batch.pinned

    def unpin(self, run_id):
        self._pins.pop(str(run_id), None)

    async def assert_current(self, run: RunContext):
        pinned = self._pins.get(str(run.run_id))
        ids = tuple(str(value) for value in run.request.document_ids)
        if pinned is None or await asyncio.to_thread(self.store.snapshot, ids) != pinned or not await asyncio.to_thread(self.store.current, pinned):
            raise ServiceError("CORPUS_CHANGED", "La publicación cambió durante la ejecución.", 409)

    async def retrieve(self, question: str, document_ids: tuple[str, ...], top_k: int) -> RetrievalBatch:
        if not 1 <= top_k <= 10:
            raise ServiceError("AI_INPUT_INVALID", "top_k no es válido.")
        ids = tuple(str(UUID(str(value))) for value in document_ids)
        pinned = await asyncio.to_thread(self.store.snapshot, ids)
        profiles = await asyncio.to_thread(self.store.profiles, ids)
        if not profiles:
            return RetrievalBatch((), pinned)
        rankings = []
        for profile in profiles:
            vector = await self.embedder.embed(question, profile)
            rows = await asyncio.to_thread(self.store.search, vector, profile, ids, min(top_k, 8))
            rankings.append(rows)
        fused: dict[str, tuple[float, dict]] = {}
        for ranking in rankings:
            for rank, row in enumerate(ranking, 1):
                key = str(row["chunk_id"])
                score = fused.get(key, (0, row))[0] + 1 / (60 + rank)
                fused[key] = (score, row)
        ordered = sorted(fused.values(), key=lambda item: item[0], reverse=True)[: min(top_k, 8)]
        evidence = tuple(Evidence(**dict(row), rank=rank) for rank, (_, row) in enumerate(ordered, 1))
        if any(pinned.get(str(item.document_id)) != str(item.generation_id) for item in evidence) or not await asyncio.to_thread(self.store.current, pinned) or await asyncio.to_thread(self.store.snapshot, ids) != pinned:
            raise ServiceError("CORPUS_CHANGED", "La publicación cambió durante la ejecución.", 409)
        return RetrievalBatch(evidence, pinned, tuple(profiles))

    async def more(self, run: RunContext, query: str, top_k: int) -> RetrievalBatch:
        pinned = self._pins.get(str(run.run_id), {})
        await self.assert_current(run)
        batch = await self.retrieve(query, tuple(str(item) for item in run.request.document_ids), top_k)
        if batch.pinned != pinned:
            raise ServiceError("CORPUS_CHANGED", "La publicación cambió durante la ejecución.", 409)
        return batch

    async def context(self, run: RunContext, chunk_id: str, radius: int) -> list[Evidence]:
        pinned = self._pins.get(str(run.run_id), {})
        await self.assert_current(run)
        rows = await asyncio.to_thread(self.store.adjacent, tuple(pinned.values()), chunk_id, radius)
        return [Evidence(**dict(row), rank=index) for index, row in enumerate(rows, 1)]
