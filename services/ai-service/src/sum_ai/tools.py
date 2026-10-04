"""Deterministic, scoped tools available to the research agent."""

from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sum_contracts.ai import AuditEvent, RunContext
from sum_contracts.models import ServiceError

from .retrieval import PublishedRetriever


UUID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchInput(ToolInput):
    query: str = Field(min_length=3, max_length=500, description="Search text, 3 to 500 characters.")
    top_k: int = Field(default=4, ge=1, le=8, strict=True, description="Retrieve 1 to 8 chunks; never exceed 8.")


class ContextInput(ToolInput):
    chunk_id: str = Field(pattern=UUID_PATTERN, description="Exact UUID of an observed published chunk.")
    radius: int = Field(default=1, ge=0, le=2, strict=True, description="Read up to 2 adjacent chunks on each side (0 to 2).")


class MetadataInput(ToolInput):
    document_id: str = Field(pattern=UUID_PATTERN, description="Exact published document UUID from this run's evidence.")


class SelectionInput(ToolInput):
    chunk_ids: list[str] = Field(min_length=1, max_length=8,
        description="1 to 8 distinct exact observed chunk UUIDs, in relevance order. Never return an empty list.")

    @field_validator("chunk_ids")
    @classmethod
    def observed_identifiers(cls, values):
        ids = [str(UUID(value)) for value in values]
        if len(set(ids)) != len(ids):
            raise ValueError("Chunk IDs must be distinct; select between 1 and 8 observed UUIDs.")
        return ids


class RelationshipsInput(ToolInput):
    document_ids: list[str] = Field(min_length=1, max_length=8,
        description="1 to 8 distinct published document UUIDs in the pinned scope.")

    @field_validator("document_ids")
    @classmethod
    def published_identifiers(cls, values):
        ids = [str(UUID(value)) for value in values]
        if len(set(ids)) != len(ids):
            raise ValueError("Document IDs must be distinct; supply between 1 and 8 published UUIDs.")
        return ids


RESEARCH_TOOL_SCHEMAS = {
    "search_published_chunks": SearchInput,
    "get_published_chunk_context": ContextInput,
    "get_publication_metadata": MetadataInput,
    "inspect_document_relationships": RelationshipsInput,
    "select_answer_evidence": SelectionInput,
}


def model_evidence(chunks):
    """Keep full records internally; expose only bounded text and IDs needed by tools."""
    return json.dumps([{"chunk_id": str(item.chunk_id), "document_id": str(item.document_id),
        "page": item.page, "text": item.text[:800], "truncated": len(item.text) > 800}
        for item in chunks], ensure_ascii=False)


def build_research_tools(retriever: PublishedRetriever, run: RunContext,
                         trace: list[dict] | None = None, evidence: list | None = None,
                         max_calls: int = 6, recorder=None):
    trace = trace if trace is not None else []
    evidence = evidence if evidence is not None else []
    calls = 0

    def count(name: str, arguments: dict):
        nonlocal calls
        calls += 1
        if len(trace) >= max_calls:
            raise ServiceError("AI_TOOL_LIMIT", "Se alcanzó el límite de herramientas.", 429)
        item = {"tool": name, "arguments": arguments}
        trace.append(item)
        return calls, item

    async def before(number, item):
        if recorder:
            if hasattr(recorder, "context"):
                await recorder.context()
            await recorder.record(AuditEvent(operation_id=f"tool:{number}:start", kind="tool", payload=item))

    async def after(number, item, chunks, started):
        item["chunk_ids"] = [str(chunk.chunk_id) for chunk in chunks]
        item["duration_ms"] = (time.monotonic() - started) * 1000
        if recorder:
            await recorder.record(AuditEvent(operation_id=f"tool:{number}:end", kind="tool", duration_ms=item["duration_ms"], payload=item))

    @tool(args_schema=SearchInput)
    async def search_published_chunks(query: str, top_k: int = 4) -> str:
        """Search the currently published institutional corpus for additional evidence."""
        query = query.strip()
        if not 3 <= len(query) <= 500 or not 1 <= top_k <= 8:
            raise ServiceError("AI_TOOL_INPUT_INVALID", "La búsqueda no es válida.")
        number, item = count("search_published_chunks", {"query": query[:200], "top_k": top_k})
        await before(number, item)
        started = time.monotonic()
        batch = await retriever.more(run, query, top_k)
        evidence.extend(batch.evidence)
        await after(number, item, batch.evidence, started)
        return model_evidence(batch.evidence)

    @tool(args_schema=ContextInput)
    async def get_published_chunk_context(chunk_id: str, radius: int = 1) -> str:
        """Read a small adjacent window around an already published chunk."""
        chunk_id = str(UUID(chunk_id))
        if not 0 <= radius <= 2:
            raise ServiceError("AI_TOOL_INPUT_INVALID", "El contexto no es válido.")
        number, item = count("get_published_chunk_context", {"chunk_id": chunk_id, "radius": radius})
        await before(number, item)
        started = time.monotonic()
        chunks = await retriever.context(run, chunk_id, radius)
        evidence.extend(chunks)
        await after(number, item, chunks, started)
        return model_evidence(chunks)

    @tool(args_schema=MetadataInput)
    async def get_publication_metadata(document_id: str) -> str:
        """Read metadata for a document fixed to this run's published generation."""
        document_id = str(UUID(document_id))
        pinned = retriever._pins.get(str(run.run_id), {})
        if document_id not in pinned:
            raise ServiceError("AI_TOOL_SCOPE", "El documento no pertenece a la evidencia fijada.", 403)
        number, item = count("get_publication_metadata", {"document_id": document_id})
        await before(number, item)
        started = time.monotonic()
        metadata = await asyncio.to_thread(retriever.store.metadata, document_id, pinned[document_id])
        await after(number, item, (), started)
        return json.dumps(metadata, ensure_ascii=False, default=str)[:4000]

    @tool(args_schema=RelationshipsInput)
    async def inspect_document_relationships(document_ids: list[str]) -> str:
        """Read declared relationships in one batch. Missing declarations do not prove legal validity."""
        if not 1 <= len(document_ids) <= 8 or len(set(document_ids)) != len(document_ids):
            raise ServiceError("AI_TOOL_INPUT_INVALID", "Selecciona entre uno y ocho documentos distintos.")
        ids = [str(UUID(value)) for value in document_ids]
        pinned = retriever._pins.get(str(run.run_id), {})
        if any(value not in pinned for value in ids):
            raise ServiceError("AI_TOOL_SCOPE", "Los documentos están fuera del alcance publicado.", 403)
        number, item = count("inspect_document_relationships", {"document_ids": ids})
        await before(number, item)
        started = time.monotonic()
        rows = await asyncio.to_thread(retriever.store.metadata_batch, {value: pinned[value] for value in ids})
        values = []
        for row in rows:
            declarations = row["metadata"].get("relationships", [])
            declarations = declarations if isinstance(declarations, list) else []
            bounded = []
            for declaration in declarations[:4]:
                serialized = json.dumps(declaration, ensure_ascii=False, default=str)
                bounded.append({"declaration": serialized[:200], "truncated": len(serialized) > 200})
            values.append({"document_id": row["document_id"], "generation_id": row["generation_id"],
                           "declared_relationships": bounded, "applicability_verified": False})
        await after(number, item, (), started)
        return json.dumps(values, ensure_ascii=False, default=str)

    @tool(args_schema=SelectionInput)
    async def select_answer_evidence(chunk_ids: list[str]) -> str:
        """Select 1 to 8 observed chunk IDs, in relevance order, for the answer context."""
        if not 1 <= len(chunk_ids) <= 8 or len(set(chunk_ids)) != len(chunk_ids):
            raise ServiceError("AI_TOOL_INPUT_INVALID", "Selecciona entre 1 y 8 fragmentos distintos.")
        ids = [str(UUID(value)) for value in chunk_ids]
        indexed = {str(chunk.chunk_id): chunk for chunk in evidence}
        if any(value not in indexed for value in ids):
            raise ServiceError("AI_TOOL_SCOPE", "Selecciona solo fragmentos observados.", 422)
        number, item = count("select_answer_evidence", {"chunk_ids": ids})
        await before(number, item)
        selected = [indexed[value] for value in ids]
        await after(number, item, selected, time.monotonic())
        return json.dumps({"selected_chunk_ids": ids})

    return [search_published_chunks, get_published_chunk_context, get_publication_metadata,
            inspect_document_relationships, select_answer_evidence]
