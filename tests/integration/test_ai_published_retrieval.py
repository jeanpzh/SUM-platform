"""Real pgvector corpus and least-privilege role; uses a synthetic fixture only."""
import asyncio
import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
from sum_ai.retrieval import PublishedRetriever, PublishedStore
from sum_contracts.models import EmbeddingProfile
from sum_database import SqlDatabase

DOC = "e5a1b5dd-696c-4f0d-827c-6c1899e2e041"
GENERATION = "30ec3e04-30f1-4f87-a146-cd8af0e00327"
CHUNK = "8a4dafbf-2c3c-4a34-a316-d46fed6d8818"
pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="AI Compose test profile required")


@contextmanager
def published_fixture():
    database = SqlDatabase(os.environ["TEST_DATABASE_URL"], 2, 3000)
    version = str(uuid4())
    with database.connection() as conn:
        conn.execute("INSERT INTO application.documents(id,owner_id,current_version_id) VALUES(%s,'ai-synthetic-test',%s)", (DOC, version))
        conn.execute("INSERT INTO application.document_versions(id,document_id,metadata,object_key,mime_type,sha256,size_bytes) VALUES(%s,%s,%s,%s,'text/plain',%s,100)", (version, DOC, {"titulo": "AI synthetic fixture", "tipo_documento": "otro"}, "ai-test/" + version, "a" * 64))
        profile = EmbeddingProfile("fixture-vector", "fixture-v1", 768)
        conn.execute("INSERT INTO institutional.generations(id,document_id,version_id,profile,metadata,expected_chunks,ready) VALUES(%s,%s,%s,%s,%s,1,true)", (GENERATION, DOC, version, profile.to_dict(), {"titulo": "AI synthetic fixture"}))
        conn.execute("INSERT INTO institutional.chunks(id,generation_id,ordinal,page,locator,content,token_count,metadata) VALUES(%s,%s,0,1,'p. 1','La versión publicada permanece disponible durante una actualización.',12,'{}')", (CHUNK, GENERATION))
        vector = "[1," + ",".join("0" for _ in range(767)) + "]"
        conn.execute("INSERT INTO institutional.embeddings(chunk_id,model,revision,dimension,embedding) VALUES(%s,'fixture-vector','fixture-v1',768,CAST(%s AS vector))", (CHUNK, vector))
        conn.execute("INSERT INTO application.publications(document_id,version_id,generation_id,manifest) VALUES(%s,%s,%s,'{}')", (DOC, version, GENERATION))
    try:
        yield database
    finally:
        with database.connection() as conn:
            conn.execute("DELETE FROM application.publications WHERE document_id=%s", (DOC,))
            conn.execute("DELETE FROM institutional.embeddings WHERE chunk_id=%s", (CHUNK,))
            conn.execute("DELETE FROM institutional.chunks WHERE generation_id=%s", (GENERATION,))
            conn.execute("DELETE FROM institutional.generations WHERE id=%s", (GENERATION,))
            conn.execute("DELETE FROM application.document_versions WHERE document_id=%s", (DOC,))
            conn.execute("DELETE FROM application.documents WHERE id=%s", (DOC,))
        database.close()


class SyntheticEmbedder:
    async def embed(self, question, profile):
        assert profile.revision == "fixture-v1" and profile.dimension == 768
        return [1.0] + [0.0] * 767


def test_published_vector_and_role_permissions():
    with published_fixture():
        store = PublishedStore(os.environ["RETRIEVAL_DATABASE_URL"])
        batch = asyncio.run(PublishedRetriever(store, SyntheticEmbedder()).retrieve("Una pregunta", (DOC,), 4))
        assert str(batch.evidence[0].chunk_id) == CHUNK
        assert batch.pinned[DOC] == GENERATION
        with pytest.raises(Exception):
            with store.database.connection() as conn:
                conn.execute("SELECT * FROM institutional.chunks LIMIT 1")
        with pytest.raises(Exception):
            with store.database.connection() as conn:
                conn.execute("DELETE FROM application.publications WHERE document_id=%s", (DOC,))
        store.database.close()
