import asyncio
import hashlib
import os
import unittest
from uuid import uuid4

from sum_contracts.models import EmbeddingProfile, JobStopped, Metadata, Status
from sum_indexer.extractors import process_source


class LocalLoop(asyncio.SelectorEventLoop):
    def _write_to_self(self):
        # Local IPC only: this sandbox denies socket.send even for a socketpair.
        # os.write preserves asyncio's wakeup semantics without network access.
        if self._csock is not None:
            try:
                os.write(self._csock.fileno(), b"\0")
            except OSError:
                pass


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    def _setupAsyncioRunner(self):
        self._asyncioRunner = asyncio.Runner(debug=True, loop_factory=LocalLoop)


class WordTokenizer:
    def count(self, text):
        return len(text.split()) + 2

    def split(self, text, limit, overlap):
        words = text.split()
        result = []
        for start in range(0, len(words), limit - overlap):
            result.append(" ".join(words[start : start + limit]))
            if start + limit >= len(words):
                break
        return result


class InlineCpu:
    def __init__(self):
        self.calls = 0

    async def call(self, action, mime, path, first=0, last=0, options=None):
        self.calls += 1
        return process_source(action, mime, path, first, last, options or {})


class CountingEmbeddings:
    profile = EmbeddingProfile("test-only", "fixed-test-revision", 3, 64)

    def __init__(self):
        self.calls = 0
        self.fail_on = None

    def embed_passages(self, texts):
        self.calls += 1
        if self.calls == self.fail_on:
            raise RuntimeError("Simulated provider outage")
        return [[1.0, 0.0, 0.0] for _ in texts]


class MemoryVectors:
    def __init__(self):
        self.rows = {}
        self.outcomes = {}
        self.expected = None
        self.prepared = False

    def begin(self, context, profile, chunks):
        self.expected = chunks

    def upsert_batch(self, generation_id, chunks, vectors, profile):
        for chunk, vector in zip(chunks, vectors, strict=True):
            self.rows[chunk.chunk_id] = (chunk, vector)

    def ready(self, generation_id, manifest):
        if len(self.rows) != self.expected:
            raise RuntimeError("Incomplete generation")
        self.prepared = True
        self.outcomes[generation_id] = {
            "job_id": generation_id,
            "kind": "completed",
            "payload": manifest,
            "delivered": False,
        }

    def enqueue_failure(self, job_id, code):
        self.outcomes.setdefault(
            job_id,
            {"job_id": job_id, "kind": "failed", "payload": {"code": code}, "delivered": False},
        )

    def pending_outcomes(self):
        return [dict(outcome) for outcome in self.outcomes.values() if not outcome["delivered"]]

    def acknowledge_outcome(self, job_id):
        self.outcomes[job_id]["delivered"] = True


class MemoryReporter:
    def __init__(self, content, object_key):
        self.data = {
            "job_id": str(uuid4()),
            "document_id": str(uuid4()),
            "version_id": str(uuid4()),
            "status": Status.QUEUED,
            "metadata": Metadata("Documento sintético", "reglamento").to_dict(),
            "source": {
                "key": object_key,
                "mime": "text/plain",
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            },
        }
        self.published = "previous-generation"
        self.updates = []
        self.fail_callback = False
        self.cancel_at_commit = False
        self.timings = []

    async def context(self, job_id):
        if self.data["status"] in {Status.CANCELLED, Status.FAILED}:
            raise JobStopped()
        return dict(self.data)

    async def progress(self, job_id, operation, stage, message, counts=None):
        await self.context(job_id)
        self.data["status"] = Status.PROCESSING
        self.updates.append((operation, stage, message, counts))

    async def embedding_profile(self, job_id, profile):
        await self.context(job_id)

    async def timing(self, job_id, data):
        if data["action"] == "start":
            await self.context(job_id)
        self.timings.append(dict(data))

    async def complete(self, job_id, manifest):
        if self.cancel_at_commit:
            self.data["status"] = Status.CANCELLED
        await self.context(job_id)
        self.published = manifest["generation_id"]
        self.data["status"] = Status.COMPLETED
        if self.fail_callback:
            self.fail_callback = False
            raise RuntimeError("Response lost after commit")

    async def fail(self, job_id, code):
        if self.data["status"] not in {Status.COMPLETED, Status.CANCELLED}:
            self.data["status"] = Status.FAILED
