from __future__ import annotations

import json

from sum_contracts.models import Chunk, EmbeddingProfile, ServiceError
from sum_database import SqlDatabase

from .embeddings import validate_vectors


class PgVectorRepository:
    def __init__(self, database_url: str, pool_size: int = 5):
        self.database = SqlDatabase(database_url, pool_size, 60000)

    def open(self):
        self.database.open()

    def close(self):
        self.database.close()

    @staticmethod
    def json(value):
        return value

    def begin(self, context: dict, profile: EmbeddingProfile, chunks: int):
        with self.database.connection() as conn:
            conn.execute(
                "INSERT INTO institutional.generations(id,document_id,version_id,profile,metadata,expected_chunks) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING",
                (
                    context["job_id"],
                    context["document_id"],
                    context["version_id"],
                    self.json(profile.to_dict()),
                    self.json(context["metadata"]),
                    chunks,
                ),
            )
            row = conn.execute(
                "SELECT * FROM institutional.generations WHERE id=%s", (context["job_id"],)
            ).fetchone()
            if (
                row["profile"] != profile.to_dict()
                or row["expected_chunks"] != chunks
                or str(row["version_id"]) != context["version_id"]
                or str(row["document_id"]) != context["document_id"]
            ):
                raise ServiceError(
                    "MODELO_INCOMPATIBLE", "La generación existente usa un perfil diferente."
                )

    def upsert_batch(
        self,
        generation_id: str,
        chunks: list[Chunk],
        vectors: list[list[float]],
        profile: EmbeddingProfile,
    ):
        validate_vectors(vectors, len(chunks), profile.dimension)
        with self.database.connection() as conn:
            generation = conn.execute(
                "SELECT ready,profile FROM institutional.generations WHERE id=%s FOR UPDATE",
                (generation_id,),
            ).fetchone()
            if generation is None or generation["profile"] != profile.to_dict():
                raise ServiceError(
                    "MODELO_INCOMPATIBLE", "La generación no coincide con el perfil de embeddings."
                )
            if generation["ready"]:
                return
            conn.execute(
                "INSERT INTO institutional.chunks(id,generation_id,ordinal,page,locator,content,token_count,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING",
                [
                    (
                        c.chunk_id,
                        generation_id,
                        c.ordinal,
                        c.page,
                        c.locator,
                        c.text,
                        c.token_count,
                        self.json(c.metadata),
                    )
                    for c in chunks
                ],
            )
            conn.execute(
                "INSERT INTO institutional.embeddings(chunk_id,model,revision,dimension,embedding) VALUES(%s,%s,%s,%s,CAST(%s AS vector)) ON CONFLICT(chunk_id) DO NOTHING",
                [
                    (
                        c.chunk_id,
                        profile.model,
                        profile.revision,
                        profile.dimension,
                        json.dumps(v, allow_nan=False),
                    )
                    for c, v in zip(chunks, vectors, strict=True)
                ],
            )

    def ready(self, generation_id: str, manifest: dict):
        with self.database.connection() as conn:
            generation = conn.execute(
                "SELECT * FROM institutional.generations WHERE id=%s FOR UPDATE", (generation_id,)
            ).fetchone()
            count = conn.execute(
                """SELECT count(*) AS n,min(c.ordinal) AS first,max(c.ordinal) AS last
                FROM institutional.chunks c JOIN institutional.embeddings e ON e.chunk_id=c.id
                WHERE c.generation_id=%s AND e.model=%s AND e.revision=%s AND e.dimension=%s""",
                (
                    generation_id,
                    manifest["profile"]["model"],
                    manifest["profile"]["revision"],
                    manifest["profile"]["dimension"],
                ),
            ).fetchone()
            expected = manifest["chunks"]
            if (
                generation is None
                or generation["expected_chunks"] != expected
                or generation["profile"] != manifest["profile"]
                or count["n"] != expected
                or count["first"] != 0
                or count["last"] != expected - 1
            ):
                raise ServiceError(
                    "MODELO_INCOMPATIBLE",
                    "La generación no está completa o contiene un perfil incompatible.",
                )
            if generation["ready"] and generation["manifest"] != manifest:
                raise ServiceError("MODELO_INCOMPATIBLE", "Una generación publicada es inmutable.")
            conn.execute(
                "UPDATE institutional.generations SET ready=true,manifest=%s WHERE id=%s",
                (self.json(manifest), generation_id),
            )
            conn.execute(
                "INSERT INTO institutional.outcomes(job_id,kind,payload) VALUES(%s,'completed',%s) ON CONFLICT(job_id) DO NOTHING",
                (generation_id, self.json(manifest)),
            )

    def enqueue_failure(self, job_id: str, code: str):
        with self.database.connection() as conn:
            # A fully prepared generation takes precedence over a late failure.
            conn.execute(
                "INSERT INTO institutional.outcomes(job_id,kind,payload) VALUES(%s,'failed',%s) ON CONFLICT(job_id) DO NOTHING",
                (job_id, self.json({"code": code})),
            )

    def pending_outcomes(self, limit: int = 100):
        with self.database.connection() as conn:
            return conn.execute(
                "SELECT * FROM institutional.outcomes WHERE delivered_at IS NULL ORDER BY created_at LIMIT %s",
                (limit,),
            ).fetchall()

    def acknowledge_outcome(self, job_id: str):
        with self.database.connection() as conn:
            conn.execute(
                "UPDATE institutional.outcomes SET delivered_at=now() WHERE job_id=%s", (job_id,)
            )
