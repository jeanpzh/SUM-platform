import os
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sum_backend.ai_metrics import MetricsProjector
from sum_backend.ai_repository import AiRunRepository
from sum_backend.ai_tables import metric_buckets, rejection_buckets, runs
from sum_contracts.ai import AuditEvent, CreateRunRequest

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Compose required")


def test_failed_evidence_filter_pagination_and_admission_counter():
    repo = AiRunRepository(os.environ["DATABASE_URL"], event_delay_seconds=3600)
    owner, generation = "audit-test-" + str(uuid4()), str(uuid4())
    projector = MetricsProjector(repo.database)
    try:
        created, _ = repo.create(owner, str(uuid4()), CreateRunRequest(question="Una pregunta sobre una norma",
            provider="ollama", model="fixture"))
        proof = {"generation_ids": [generation], "evidence": [], "profiles": [], "corpus_sha256": "a" * 64}
        repo.apply_event(created["run_id"], AuditEvent(operation_id="retrieval:initial", kind="evidence", payload=proof))
        repo.apply_event(created["run_id"], AuditEvent(operation_id="run:failed", kind="failed", code="AI_PROVIDER_UNAVAILABLE"))
        assert repo.get(created["run_id"], owner)["retrieval_audit"] == proof
        filtered = repo.list(owner, 1, 0, 7, "ollama", "fixture", generation, "failed")
        assert filtered[0]["run_id"] == created["run_id"]
        assert repo.list(owner, 1, 1, 7, "ollama", "fixture", generation, "failed") == []
        assert repo.list(owner, 1, 0, 7, "groq", "fixture", generation, "failed") == []
        projector.project()
        assert projector.get_metrics(owner, generation=generation)["summary"]["count"] == 1
        projector.record_rejection(owner, "ollama", "fixture")
        projector.record_rejection(owner, "ollama", "fixture")
        assert projector.get_metrics(owner)["summary"]["rate_limits"] == 2
        assert projector.get_metrics(owner, provider="groq")["summary"]["rate_limits"] == 0
    finally:
        with repo.database.engine.begin() as conn:
            conn.execute(delete(runs).where(runs.c.owner_id == owner))
            conn.execute(delete(metric_buckets).where(metric_buckets.c.owner_id == owner))
            conn.execute(delete(rejection_buckets).where(rejection_buckets.c.owner_id == owner))
        repo.close()
