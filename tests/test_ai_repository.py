from uuid import uuid4

import pytest
from pydantic import ValidationError
from sum_backend.ai_repository import AiRunRepository
from sum_contracts.ai import AuditEvent, CreateRunRequest
from sum_contracts.models import ServiceError


class MemoryConnection:
    def __init__(self):
        self.runs = {}
        self.outbox = []
        self.events = []

    def execute(self, sql, args=()):
        raise NotImplementedError("Use PostgreSQL integration for SQL claims")


def request(question="¿Qué indica la norma?"):
    return CreateRunRequest(question=question, provider="ollama", model="llama3.2", top_k=4)


def test_request_bounds_and_unknown_fields():
    with pytest.raises(ValidationError):
        request("x")
    with pytest.raises(ValidationError):
        CreateRunRequest(question="Válida", provider="ollama", model="x", top_k=11)
    with pytest.raises(ValidationError):
        CreateRunRequest(question="Válida", provider="ollama", model="x", extra=True)
    with pytest.raises(ValidationError):
        CreateRunRequest(
            question="Válida", provider="ollama", model="x", document_ids=[str(uuid4())] * 21
        )


def test_fingerprint_is_canonical():
    one = request()
    two = request()
    assert one.fingerprint() == two.fingerprint()
    assert one.fingerprint() != request("Otra pregunta").fingerprint()


def test_audit_event_rejects_unbounded_or_unknown_data():
    with pytest.raises(ValidationError):
        AuditEvent(operation_id="", kind="stage")
    with pytest.raises(ValidationError):
        AuditEvent(operation_id="x", kind="stage", secret="never")


@pytest.mark.skipif(not __import__("os").environ.get("DATABASE_URL"), reason="DATABASE_URL required")
def test_postgres_run_outbox_idempotency_and_event_state():
    import os

    repo = AiRunRepository(os.environ["DATABASE_URL"], event_delay_seconds=3600)
    owner = "ai-test-" + str(uuid4())
    key = str(uuid4())
    try:
        created, fresh = repo.create(owner, key, request())
        assert fresh
        replayed, fresh = repo.create(owner, key, request())
        assert not fresh and replayed["run_id"] == created["run_id"]
        with pytest.raises(ServiceError) as conflict:
            repo.create(owner, key, request("Una pregunta distinta"))
        assert conflict.value.status == 409
        with pytest.raises(ServiceError) as denied:
            repo.get(created["run_id"], "another-owner")
        assert denied.value.status == 404
        with repo.database.connection() as conn:
            rows = conn.execute(
                "SELECT payload FROM application.outbox WHERE run_id=%s", (created["run_id"],)
            ).fetchall()
            assert len(rows) == 1
            assert set(rows[0]["payload"]) == {"contract_version", "run_id"}
        event = AuditEvent(operation_id="start", kind="started", stage="validating")
        first = repo.apply_event(created["run_id"], event)
        duplicate = repo.apply_event(created["run_id"], event)
        assert first["sequence"] == duplicate["sequence"]
        repo.cancel(created["run_id"], owner)
        with pytest.raises(ServiceError) as stopped:
            repo.apply_event(
                created["run_id"], AuditEvent(operation_id="late", kind="completed")
            )
        assert stopped.value.status == 409
    finally:
        with repo.database.connection() as conn:
            conn.execute("DELETE FROM application.outbox WHERE run_id=%s", (created["run_id"],))
            conn.execute("DELETE FROM application.ai_runs WHERE id=%s", (created["run_id"],))
        repo.close()
