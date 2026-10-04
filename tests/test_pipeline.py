import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sum_contracts.models import Block, Page, ServiceError, Status
from sum_indexer.chunking import DocumentChunker
from sum_indexer.config import Settings
from sum_indexer.cpu import CpuPool
from sum_indexer.pipeline import Pipeline
from sum_indexer.workflows import reconcile_outcomes, run_stage
from sum_storage.objects import LocalStorage

from tests.support import (
    AsyncTests,
    CountingEmbeddings,
    InlineCpu,
    MemoryReporter,
    MemoryVectors,
    WordTokenizer,
)


class PipelineTests(AsyncTests):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage = LocalStorage(Path(self.directory.name))
        content = ("Documento sintético para comprobar la indexación en español. " * 30).encode()
        self.storage.put("originals/example", io.BytesIO(content))
        self.reporter = MemoryReporter(content, "originals/example")
        self.embeddings, self.vectors, self.cpu = CountingEmbeddings(), MemoryVectors(), InlineCpu()
        self.settings = Settings(
            "unused",
            "unused",
            "unused",
            cpu_processes=2,
            embedding_batch_size=2,
            chunk_tokens=12,
            chunk_overlap=2,
        )
        self.pipeline = Pipeline(
            self.settings,
            self.storage,
            self.reporter,
            self.cpu,
            self.embeddings,
            self.vectors,
            lambda profile: WordTokenizer(),
        )
        self.job_id = self.reporter.data["job_id"]

    async def prepare_chunks(self):
        for phase in ["validate", "extract", "chunk"]:
            await getattr(self.pipeline, phase)(self.job_id)

    async def prepare_generation(self):
        await self.prepare_chunks()
        await self.pipeline.embed(self.job_id)
        await self.pipeline.store(self.job_id)

    async def test_complete_text_pipeline_keeps_metadata_and_citation_locations(self):
        await self.prepare_generation()
        self.assertTrue(self.vectors.prepared)
        self.assertEqual(self.reporter.published, "previous-generation")
        await self.pipeline.publish(self.job_id)
        self.assertEqual(self.reporter.data["status"], Status.COMPLETED)
        self.assertEqual(self.reporter.published, self.job_id)
        chunk = next(iter(self.vectors.rows.values()))[0]
        self.assertEqual(chunk.metadata["tipo_documento"], "reglamento")
        self.assertIn("página 1", chunk.locator)
        self.assertLessEqual(chunk.token_count, self.embeddings.profile.max_tokens)
        self.assertIn(
            "Página 1", self.storage.read(self.pipeline.key(self.job_id, "document.txt")).decode()
        )

    async def test_embedding_retry_reuses_successful_batches(self):
        await self.prepare_chunks()
        self.embeddings.fail_on = 2
        with self.assertRaises(RuntimeError):
            await self.pipeline.embed(self.job_id)
        self.assertTrue(self.storage.exists(self.pipeline.key(self.job_id, "vectors/0.json")))
        self.embeddings.fail_on = None
        await self.pipeline.embed(self.job_id)
        manifest = await self.pipeline.read_json(self.pipeline.key(self.job_id, "chunks.json"))
        self.assertEqual(self.embeddings.calls, len(manifest["batches"]) + 1)

    async def test_repeated_extraction_and_writes_do_not_duplicate_work_or_vectors(self):
        await self.prepare_generation()
        calls, vector_count = self.cpu.calls, len(self.vectors.rows)
        await self.pipeline.extract(self.job_id)
        await self.pipeline.store(self.job_id)
        self.assertEqual(self.cpu.calls, calls)
        self.assertEqual(len(self.vectors.rows), vector_count)

    async def test_lost_completion_response_is_reconciled(self):
        await self.prepare_generation()
        self.reporter.fail_callback = True
        with self.assertRaises(RuntimeError):
            await self.pipeline.publish(self.job_id)
        self.assertEqual(self.reporter.data["status"], Status.COMPLETED)
        result = await reconcile_outcomes(self.vectors, self.reporter)
        self.assertEqual(result["delivered"], 1)
        self.assertEqual(self.vectors.pending_outcomes(), [])

    async def test_cancellation_at_publication_keeps_previous_generation(self):
        await self.prepare_generation()
        self.reporter.cancel_at_commit = True
        result = await run_stage(self.pipeline, "publish", self.job_id)
        self.assertEqual(result["status"], Status.CANCELLED)
        self.assertEqual(self.reporter.published, "previous-generation")
        await reconcile_outcomes(self.vectors, self.reporter)
        self.assertEqual(self.reporter.published, "previous-generation")

    async def test_source_checksum_mismatch_fails_before_extraction(self):
        await self.pipeline.validate(self.job_id)
        self.storage.put("originals/example", io.BytesIO(b"modified source"))
        with self.assertRaises(ServiceError) as caught:
            await self.pipeline.extract(self.job_id)
        self.assertEqual(caught.exception.code, "ARCHIVO_INVALIDO")
        self.assertEqual(self.cpu.calls, 0)

    async def test_changed_pipeline_configuration_requires_new_job(self):
        await self.pipeline.validate(self.job_id)
        changed = Settings(
            "unused", "unused", "unused", embedding_batch_size=4, chunk_tokens=12, chunk_overlap=2
        )
        other = Pipeline(
            changed,
            self.storage,
            self.reporter,
            self.cpu,
            self.embeddings,
            self.vectors,
            lambda profile: WordTokenizer(),
        )
        with self.assertRaises(ServiceError) as caught:
            await other.chunk(self.job_id)
        self.assertEqual(caught.exception.code, "MODELO_INCOMPATIBLE")

    async def test_transient_failure_does_not_mark_job_failed_prematurely(self):
        await self.prepare_chunks()
        self.embeddings.fail_on = 1
        with self.assertRaisesRegex(RuntimeError, "ERROR_TRANSITORIO"):
            await run_stage(self.pipeline, "embed", self.job_id)
        self.assertNotEqual(self.reporter.data["status"], Status.FAILED)

    async def test_stage_duration_uses_monotonic_clock_and_closes_success(self):
        with patch(
            "sum_indexer.workflows.perf_counter_ns", side_effect=[10_000_000_000, 10_054_320_000]
        ):
            await run_stage(self.pipeline, "validate", self.job_id)
        start, end = self.reporter.timings
        self.assertEqual(start["attempt_id"], end["attempt_id"])
        self.assertEqual(end["duration_ms"], 54.32)
        self.assertEqual(end["outcome"], "completado")

    async def test_stage_retries_preserve_failed_and_successful_attempts(self):
        await self.prepare_chunks()
        self.embeddings.fail_on = 1
        with self.assertRaisesRegex(RuntimeError, "ERROR_TRANSITORIO"):
            await run_stage(self.pipeline, "embed", self.job_id)
        self.embeddings.fail_on = None
        await run_stage(self.pipeline, "embed", self.job_id)
        ends = [row for row in self.reporter.timings if row["action"] == "end"]
        self.assertEqual([row["outcome"] for row in ends], ["fallido", "completado"])
        self.assertNotEqual(ends[0]["attempt_id"], ends[1]["attempt_id"])
        self.assertTrue(all(row["duration_ms"] >= 0 for row in ends))

    async def test_cancelled_stage_keeps_cancelled_attempt_duration(self):
        await self.prepare_generation()
        self.reporter.cancel_at_commit = True
        await run_stage(self.pipeline, "publish", self.job_id)
        self.assertEqual(self.reporter.timings[-1]["outcome"], "cancelado")
        self.assertGreaterEqual(self.reporter.timings[-1]["duration_ms"], 0)

    async def test_timing_delivery_failure_does_not_fail_published_document(self):
        await self.prepare_generation()
        original = self.reporter.timing

        async def lose_end(job_id, data):
            if data["action"] == "end":
                raise RuntimeError("Network unavailable")
            await original(job_id, data)

        self.reporter.timing = lose_end
        with self.assertLogs("sum.indexer", level="WARNING"):
            result = await run_stage(self.pipeline, "publish", self.job_id)
        self.assertEqual(result["status"], Status.COMPLETED)
        self.assertEqual(self.reporter.data["status"], Status.COMPLETED)


class ChunkingTests(unittest.TestCase):
    def test_table_rows_retain_their_page_and_locator(self):
        from sum_contracts.models import Metadata

        embeddings = CountingEmbeddings()
        chunker = DocumentChunker(WordTokenizer(), embeddings.profile, 12, 2)
        page = Page(
            7, (Block("Curso: Matemática | Créditos: 4 | Ciclo: II", "table", "tabla 1, fila 2"),)
        )
        chunks = chunker.chunks(
            "12345678-1234-5678-1234-567812345678",
            Metadata("Plan sintético", "plan_estudios"),
            [page],
        )
        self.assertEqual(chunks[0].page, 7)
        self.assertEqual(chunks[0].metadata["tipo_bloque"], "table")
        self.assertIn("tabla 1, fila 2", chunks[0].locator)
        self.assertEqual(
            chunks,
            chunker.chunks(
                "12345678-1234-5678-1234-567812345678",
                Metadata("Plan sintético", "plan_estudios"),
                [page],
            ),
        )


class CpuTests(AsyncTests):
    async def test_real_spawn_pool_processes_independent_text_documents(self):
        import asyncio

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.txt"
            path.write_text("Texto académico sintético en español.", encoding="utf-8")
            pool = CpuPool(2, 15)
            try:
                await pool.start()
            except PermissionError as exc:
                self.skipTest(f"El entorno restringe los semáforos de multiprocessing: {exc}")
            try:
                one, two = await asyncio.gather(
                    pool.call("extract", "text/plain", str(path)),
                    pool.call("extract", "text/plain", str(path)),
                )
                self.assertEqual(one, two)
                self.assertIn("español", one[0]["blocks"][0]["text"])
            finally:
                await pool.close()
