"""Correlate admin agent attempts with optional LangSmith traces."""
from contextlib import asynccontextmanager, nullcontext
from functools import lru_cache
import os
from uuid import uuid4

from langsmith import Client, trace, tracing_context
from sum_contracts.ai import AuditEvent


@lru_cache(maxsize=2)
def _client(capture_content: bool):
    return Client(hide_inputs=not capture_content, hide_outputs=not capture_content, timeout_ms=2000)


@asynccontextmanager
async def admin_trace_scope(run, recorder):
    # The student orchestrator owns its separate, always masked tracing scope.
    if run.request.audience != "admin":
        yield
        return
    enabled = os.environ.get("LANGSMITH_TRACING", "false").lower() == "true" and bool(
        os.environ.get("LANGSMITH_API_KEY"))
    capture = os.environ.get("LANGSMITH_ADMIN_CAPTURE_CONTENT", "false").lower() == "true"
    project = os.environ.get("LANGSMITH_ADMIN_PROJECT", "sum-admin-rag")
    trace_id = uuid4()
    metadata = {"sum_run_id": str(run.run_id), "audience": "admin",
                "provider": run.request.provider, "model": run.request.model,
                "attempt_id": getattr(recorder, "attempt_id", str(trace_id))}
    client = _client(capture) if enabled else None
    with tracing_context(enabled=enabled, client=client, project_name=project, metadata=metadata):
        scope = trace("AdminRAG", run_id=trace_id, inputs={}, client=client) if enabled else nullcontext()
        with scope:
            await recorder.record(AuditEvent(operation_id="admin:trace", kind="stage",
                payload={"trace_id": str(trace_id), "observability": enabled,
                         "project": project, "capture_content": enabled and capture}))
            yield
