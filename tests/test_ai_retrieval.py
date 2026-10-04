import asyncio
from uuid import uuid4

import pytest
from sum_ai.retrieval import PublishedRetriever, RetrievalBatch
from sum_contracts.ai import CreateRunRequest, RunContext
from sum_contracts.models import EmbeddingProfile, ServiceError


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    async def embed(self, question, profile):
        self.calls.append((question, profile))
        return [1.0, 0.0, 0.0]


class FakeStore:
    def __init__(self):
        self.generation = str(uuid4())
        self.document = str(uuid4())
        self.version = str(uuid4())
        self.chunk = str(uuid4())
        self.profile = EmbeddingProfile("test", "revision", 3, query_prefix="query: ")
        self.sql = []
        self.changed = False

    def profiles(self, ids):
        return [self.profile]

    def snapshot(self, ids):
        return {self.document: self.generation}

    def search(self, vector, profile, ids, top_k):
        self.sql.append((tuple(ids), top_k))
        return [{"chunk_id": self.chunk, "document_id": self.document,
                 "version_id": self.version, "generation_id": self.generation,
                 "page": 2, "locator": "p. 2", "text": "Texto publicado", "score": 0.1}]

    def current(self, pinned):
        return not self.changed

    def adjacent(self, generation_id, chunk_id, radius):
        return []


def run(store):
    from datetime import datetime, timezone
    return RunContext(run_id=uuid4(), owner_id="admin", status="running",
                      created_at=datetime.now(timezone.utc),
                      request=CreateRunRequest(question="Una pregunta", provider="ollama", model="x"))


def test_retrieval_pins_generation_and_uses_query_profile():
    store, embedder = FakeStore(), FakeEmbedder()
    retriever = PublishedRetriever(store, embedder)
    batch = asyncio.run(retriever.retrieve("Una pregunta", (), 4))
    assert isinstance(batch, RetrievalBatch)
    assert batch.pinned[store.document] == store.generation
    assert str(batch.evidence[0].chunk_id) == store.chunk
    assert embedder.calls[0][1] == store.profile
    assert store.sql == [((), 4)]


def test_changed_publication_rejects_followup():
    store = FakeStore()
    retriever = PublishedRetriever(store, FakeEmbedder())
    batch = asyncio.run(retriever.retrieve("Una pregunta", (), 4))
    context = run(store)
    retriever.pin(context.run_id, batch)
    store.changed = True
    with pytest.raises(ServiceError) as error:
        asyncio.run(retriever.more(context, "Otra pregunta", 4))
    assert error.value.code == "CORPUS_CHANGED"


def test_publication_change_during_search_is_rejected_and_pins_are_released():
    store = FakeStore()
    original = store.search
    def changing_search(*args):
        rows = original(*args)
        store.changed = True
        return rows
    store.search = changing_search
    retriever = PublishedRetriever(store, FakeEmbedder())
    with pytest.raises(ServiceError, match="publicación"):
        asyncio.run(retriever.retrieve("Una pregunta", (), 4))
    store.changed = False
    store.search = original
    batch = asyncio.run(retriever.retrieve("Una pregunta", (), 4))
    context = run(store)
    retriever.pin(context.run_id, batch)
    retriever.unpin(context.run_id)
    assert str(context.run_id) not in retriever._pins
