from __future__ import annotations

import asyncio
import hashlib
import io
import json
import tempfile
from pathlib import Path

from sum_contracts.models import Block, Chunk, Metadata, Page, ServiceError, Status, require_uuid
from sum_storage.objects import ObjectStorage

from .chunking import PIPELINE_VERSION, DocumentChunker
from .config import Settings
from .ports import EmbeddingProvider, JobReporter, Tokenizer, VectorRepository


class Pipeline:
    def __init__(
        self,
        settings: Settings,
        storage: ObjectStorage,
        reporter: JobReporter,
        cpu,
        embeddings: EmbeddingProvider,
        vectors: VectorRepository,
        tokenizer_factory,
        embedding_factory=None,
    ):
        self.settings, self.storage, self.reporter = settings, storage, reporter
        self.cpu, self.embeddings, self.vectors = cpu, embeddings, vectors
        self.tokenizer_factory = tokenizer_factory
        self._tokenizer: Tokenizer | None = None
        self._tokenizers: dict[str, Tokenizer] = {}
        self.embedding_factory = embedding_factory
        self._embedding_instances = {}

    @staticmethod
    def key(job_id: str, name: str) -> str:
        return f"derived/{require_uuid(job_id)}/{name}"

    async def read_json(self, key: str):
        return json.loads(await asyncio.to_thread(self.storage.read, key))

    async def put_json(self, key: str, data):
        content = io.BytesIO(json.dumps(data, ensure_ascii=False, allow_nan=False).encode())
        await asyncio.to_thread(self.storage.put, key, content, "application/json")

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self.storage.exists, key)

    async def context(self, job_id: str):
        return await self.reporter.context(require_uuid(job_id))

    def embedding_provider(self, context):
        if self.embedding_factory is None:
            return self.embeddings
        profile = context["embedding_profile"]
        key = json.dumps(profile, sort_keys=True)
        if key not in self._embedding_instances:
            self._embedding_instances[key] = self.embedding_factory(profile)
        return self._embedding_instances[key]

    async def descriptor(self, job_id: str):
        run = await self.read_json(self.key(job_id, "run.json"))
        context = await self.context(job_id)
        embeddings = self.embedding_provider(context)
        profile = await asyncio.to_thread(lambda: embeddings.profile)
        config = {
            "tokens": self.settings.chunk_tokens,
            "overlap": self.settings.chunk_overlap,
            "batch": self.settings.embedding_batch_size,
            "pages": self.settings.page_batch_size,
        }
        if (
            run["profile"] != profile.to_dict()
            or run["pipeline_version"] != PIPELINE_VERSION
            or run["config"] != config
        ):
            raise ServiceError(
                "MODELO_INCOMPATIBLE",
                "La configuración cambió. Cree un nuevo trabajo de indexación.",
            )
        return run

    async def validate(self, job_id: str) -> dict:
        context = await self.context(job_id)
        key = self.key(job_id, "run.json")
        if context["status"] == Status.COMPLETED:
            return {"job_id": job_id, "status": Status.COMPLETED}
        await self.reporter.progress(
            job_id, "validating", "validando", "Validando el documento y su configuración."
        )
        embeddings = self.embedding_provider(context)
        profile = await asyncio.to_thread(lambda: embeddings.profile)
        await self.reporter.embedding_profile(job_id, profile.to_dict())
        if await self.exists(key):
            run = await self.descriptor(job_id)
            if (
                run["context"]["version_id"] != context["version_id"]
                or run["context"]["source"] != context["source"]
            ):
                raise ServiceError("ARCHIVO_INVALIDO", "La fuente del trabajo cambió.")
        else:
            Metadata.parse(context["metadata"])
            run = {
                "context": context,
                "profile": profile.to_dict(),
                "pipeline_version": PIPELINE_VERSION,
                "config": {
                    "tokens": self.settings.chunk_tokens,
                    "overlap": self.settings.chunk_overlap,
                    "batch": self.settings.embedding_batch_size,
                    "pages": self.settings.page_batch_size,
                },
            }
            await self.put_json(key, run)
        return {"job_id": job_id, "artifact_key": key}

    async def extract(self, job_id: str) -> dict:
        context = await self.context(job_id)
        if context["status"] == Status.COMPLETED:
            return {"job_id": job_id, "status": Status.COMPLETED}
        await self.descriptor(job_id)
        manifest_key = self.key(job_id, "extraction.json")
        if await self.exists(manifest_key):
            return {"job_id": job_id, "artifact_key": manifest_key}
        await self.reporter.progress(
            job_id,
            "extracting",
            "extrayendo",
            "Extrayendo texto y aplicando OCR cuando hace falta.",
        )
        source, ranges, characters = context["source"], [], 0
        with tempfile.TemporaryDirectory(prefix="sum-index-") as directory:
            path = Path(directory) / "source"
            await asyncio.to_thread(self.storage.download, source["key"], path)
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while piece := stream.read(1024 * 1024):
                    digest.update(piece)
            if path.stat().st_size != source["size"] or digest.hexdigest() != source["sha256"]:
                raise ServiceError(
                    "ARCHIVO_INVALIDO", "El archivo no coincide con su huella registrada."
                )
            count = await self.cpu.call("count", source["mime"], str(path))
            if count <= 0 or count > self.settings.max_pages:
                raise ServiceError(
                    "LIMITE_PAGINAS", "El documento supera el límite de páginas permitido."
                )
            text_path = Path(directory) / "document.txt"

            async def extract_range(start):
                await self.context(job_id)
                end = min(start + self.settings.page_batch_size, count)
                key = self.key(job_id, f"pages/{start}-{end}.json")
                if await self.exists(key):
                    pages = await self.read_json(key)
                else:
                    pages = await self.cpu.call(
                        "extract", source["mime"], str(path), start, end, context["metadata"]
                    )
                    await self.put_json(key, pages)
                return end, key, pages

            starts = list(range(0, count, self.settings.page_batch_size))
            window = self.settings.cpu_processes
            pending = {
                start: asyncio.create_task(extract_range(start)) for start in starts[:window]
            }
            try:
                with text_path.open("w", encoding="utf-8") as output:
                    for index, start in enumerate(starts):
                        end, key, pages = await pending.pop(start)
                        next_index = index + window
                        if next_index < len(starts):
                            next_start = starts[next_index]
                            pending[next_start] = asyncio.create_task(extract_range(next_start))
                        ranges.append(key)
                        for page in pages:
                            output.write(f"\n--- Página {page['number']} ---\n")
                            for block in page["blocks"]:
                                characters += len(block["text"].strip())
                                output.write(block["text"] + "\n\n")
                        await self.reporter.progress(
                            job_id,
                            f"pages-{end}",
                            "extrayendo",
                            f"Procesadas {end} de {count} páginas.",
                            {"paginas": end},
                        )
            finally:
                for task in pending.values():
                    task.cancel()
                await asyncio.gather(*pending.values(), return_exceptions=True)
            if characters < 20:
                raise ServiceError(
                    "TEXTO_INSUFICIENTE", "No se encontró texto suficiente para indexar."
                )
            text_key = self.key(job_id, "document.txt")
            with text_path.open("rb") as output:
                await asyncio.to_thread(
                    self.storage.put, text_key, output, "text/plain; charset=utf-8"
                )
        await self.put_json(manifest_key, {"pages": count, "ranges": ranges, "text_key": text_key})
        return {"job_id": job_id, "artifact_key": manifest_key}

    async def chunk(self, job_id: str) -> dict:
        context = await self.context(job_id)
        if context["status"] == Status.COMPLETED:
            return {"job_id": job_id, "status": Status.COMPLETED}
        await self.descriptor(job_id)
        key = self.key(job_id, "chunks.json")
        if await self.exists(key):
            return {"job_id": job_id, "artifact_key": key}
        await self.reporter.progress(
            job_id, "chunking", "fragmentando", "Creando fragmentos con referencias a sus páginas."
        )
        embeddings = self.embedding_provider(context)
        profile = await asyncio.to_thread(lambda: embeddings.profile)
        token_key = json.dumps(profile.to_dict(), sort_keys=True)
        if token_key not in self._tokenizers:
            self._tokenizers[token_key] = await asyncio.to_thread(self.tokenizer_factory, profile)
        chunker = DocumentChunker(
            self._tokenizers[token_key],
            profile,
            self.settings.chunk_tokens,
            self.settings.chunk_overlap,
        )
        extraction = await self.read_json(self.key(job_id, "extraction.json"))
        batches, buffer, ordinal = [], [], 0
        for page_range in extraction["ranges"]:
            await self.context(job_id)
            for raw_page in await self.read_json(page_range):
                for block in raw_page["blocks"]:
                    page = Page(raw_page["number"], (Block(**block),), raw_page.get("ocr", False))
                    pieces = await asyncio.to_thread(
                        chunker.chunks, job_id, Metadata.parse(context["metadata"]), [page], ordinal
                    )
                    ordinal += len(pieces)
                    for chunk in pieces:
                        buffer.append(chunk.to_dict())
                        if len(buffer) == self.settings.embedding_batch_size:
                            batch_key = self.key(job_id, f"chunks/{len(batches)}.json")
                            await self.put_json(batch_key, buffer)
                            batches.append(batch_key)
                            buffer = []
        if buffer:
            batch_key = self.key(job_id, f"chunks/{len(batches)}.json")
            await self.put_json(batch_key, buffer)
            batches.append(batch_key)
        if not ordinal:
            raise ServiceError("TEXTO_INSUFICIENTE", "No se generaron fragmentos útiles.")
        await self.put_json(key, {"count": ordinal, "batches": batches})
        await self.reporter.progress(
            job_id,
            "chunks-ready",
            "fragmentando",
            f"Se generaron {ordinal} fragmentos.",
            {"fragmentos": ordinal},
        )
        return {"job_id": job_id, "artifact_key": key}

    async def embed(self, job_id: str) -> dict:
        context = await self.context(job_id)
        if context["status"] == Status.COMPLETED:
            return {"job_id": job_id, "status": Status.COMPLETED}
        await self.descriptor(job_id)
        chunks = await self.read_json(self.key(job_id, "chunks.json"))
        count = 0
        for i, batch_key in enumerate(chunks["batches"]):
            await self.context(job_id)
            batch = await self.read_json(batch_key)
            vectors_key = self.key(job_id, f"vectors/{i}.json")
            if not await self.exists(vectors_key):
                embeddings = self.embedding_provider(context)
                vectors = await asyncio.to_thread(
                    embeddings.embed_passages, [item["text"] for item in batch]
                )
                await self.put_json(vectors_key, vectors)
            count += len(batch)
            await self.reporter.progress(
                job_id,
                f"vectors-{i}",
                "generando_vectores",
                f"Generados {count} de {chunks['count']} vectores.",
                {"vectores": count},
            )
        return {"job_id": job_id, "artifact_key": self.key(job_id, "chunks.json")}

    async def store(self, job_id: str) -> dict:
        context = await self.context(job_id)
        if context["status"] == Status.COMPLETED:
            return {"job_id": job_id, "status": Status.COMPLETED}
        await self.descriptor(job_id)
        chunks = await self.read_json(self.key(job_id, "chunks.json"))
        embeddings = self.embedding_provider(context)
        profile = await asyncio.to_thread(lambda: embeddings.profile)
        await self.vectors_begin(context, profile, chunks["count"])
        for i, batch_key in enumerate(chunks["batches"]):
            await self.context(job_id)
            batch = [Chunk(**item) for item in await self.read_json(batch_key)]
            vectors = await self.read_json(self.key(job_id, f"vectors/{i}.json"))
            await asyncio.to_thread(self.vectors.upsert_batch, job_id, batch, vectors, profile)
            await self.reporter.progress(
                job_id,
                f"stored-{i}",
                "guardando",
                "Guardando fragmentos y vectores de la nueva versión.",
            )
        extraction = await self.read_json(self.key(job_id, "extraction.json"))
        manifest = {
            "generation_id": job_id,
            "document_id": context["document_id"],
            "version_id": context["version_id"],
            "chunks": chunks["count"],
            "profile": profile.to_dict(),
            "pipeline_version": PIPELINE_VERSION,
            "text_key": extraction["text_key"],
        }
        await asyncio.to_thread(self.vectors.ready, job_id, manifest)
        key = self.key(job_id, "manifest.json")
        await self.put_json(key, manifest)
        return {"job_id": job_id, "artifact_key": key}

    async def vectors_begin(self, context, profile, chunks):
        await asyncio.to_thread(self.vectors.begin, context, profile, chunks)

    async def publish(self, job_id: str) -> dict:
        context = await self.context(job_id)
        if context["status"] == Status.COMPLETED:
            return {"job_id": job_id, "status": Status.COMPLETED}
        await self.descriptor(job_id)
        await self.reporter.progress(
            job_id, "publishing", "publicando", "Publicando la versión completa del documento."
        )
        manifest = await self.read_json(self.key(job_id, "manifest.json"))
        await self.reporter.complete(job_id, manifest)
        return {"job_id": job_id, "status": Status.COMPLETED}
