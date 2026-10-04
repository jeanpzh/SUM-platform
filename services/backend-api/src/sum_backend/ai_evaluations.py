"""Install-only labeled datasets and atomic evaluation admission."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Float, Uuid, cast, column, func, select, table
from sum_contracts.ai import (
    AI_CONTRACT_VERSION,
    AI_EVALUATION_REQUESTED,
    CreateRunRequest,
    EvaluationContext,
    EvaluationDataset,
)
from sum_contracts.models import ServiceError

from .ai_tables import evaluations, outbox, runs


class EvaluationRepository:
    def __init__(self, database, directory: str):
        self.database = database
        self.datasets = {}
        for path in Path(directory).glob("*.json"):
            dataset = EvaluationDataset.model_validate_json(path.read_text())
            if dataset.dataset_id in self.datasets:
                raise ValueError("Duplicate AI evaluation dataset")
            self.datasets[dataset.dataset_id] = dataset

    def available(self, dataset):
        chunks = table("published_chunks", column("id", Uuid), column("generation_id", Uuid),
            column("document_id", Uuid), schema="institutional")
        with self.database.engine.begin() as conn:
            for case in dataset.cases:
                rows = conn.execute(select(chunks).where(chunks.c.id.in_(case.relevant_ids))).mappings().all()
                if {row["id"] for row in rows} != set(case.relevant_ids):
                    return False
                if any(row["generation_id"] not in case.generation_ids or row["document_id"] not in case.document_ids for row in rows):
                    return False
        return True

    def catalog(self) -> list[dict]:
        return [{"dataset_id": item.dataset_id, "version": item.version,
                 "cases": len(item.cases), "available": self.available(item)}
                for item in self.datasets.values()]

    def create(self, owner: str, key: str, dataset_id: str, provider: str, model: str,
               provider_config_id=None, provider_revision=None) -> dict:
        from uuid import UUID

        from sqlalchemy import insert
        dataset = self.datasets.get(dataset_id)
        if dataset is None:
            raise ServiceError("AI_DATASET_UNKNOWN", "El conjunto de evaluación no existe.", 422)
        if not 1 <= len(key) <= 200:
            raise ServiceError("AI_IDEMPOTENCY_KEY_INVALID", "Se requiere Idempotency-Key.")
        fingerprint = hashlib.sha256(json.dumps([dataset.dataset_id, dataset.version, provider, model,
            str(provider_config_id) if provider_config_id else None, provider_revision]).encode()).hexdigest()
        with self.database.engine.begin() as conn:
            conn.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(owner, 0))))
            existing = conn.execute(select(evaluations).where(evaluations.c.owner_id == owner,
                evaluations.c.idempotency_key == key)).mappings().first()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise ServiceError("AI_IDEMPOTENCY_CONFLICT", "La clave ya se usó con otra evaluación.", 409)
                ids = conn.scalars(select(runs.c.id).where(runs.c.evaluation_id == existing["id"])).all()
                return {"evaluation_id": str(existing["id"]), "run_ids": [str(value) for value in ids]}
            if not self.available(dataset):
                raise ServiceError("AI_LABELS_STALE", "Las etiquetas no coinciden con el corpus publicado.", 409)
            evaluation_id = uuid4()
            conn.execute(insert(evaluations).values(id=evaluation_id, owner_id=owner, idempotency_key=key,
                fingerprint=fingerprint, dataset_id=dataset.dataset_id, dataset_version=dataset.version,
                provider=provider, model=model))
            ids = []
            for case in dataset.cases:
                run_id = uuid4()
                request = CreateRunRequest(question=case.question, provider=provider, model=model,
                    document_ids=case.document_ids, top_k=4,
                    provider_config_id=UUID(str(provider_config_id)) if provider_config_id else None,
                    provider_revision=provider_revision)
                evaluation = EvaluationContext(dataset_id=dataset.dataset_id, dataset_version=dataset.version, case=case)
                conn.execute(insert(runs).values(id=run_id, owner_id=owner,
                    idempotency_key=f"eval:{evaluation_id}:{case.case_id}", fingerprint=request.fingerprint(),
                    request=request.model_dump(mode="json"), evaluation_id=evaluation_id,
                    evaluation_context=evaluation.model_dump(mode="json")))
                conn.execute(insert(outbox).values(id=uuid4(), run_id=run_id, event_name=AI_EVALUATION_REQUESTED,
                    payload={"contract_version": AI_CONTRACT_VERSION, "run_id": str(run_id)}))
                ids.append(str(run_id))
            return {"evaluation_id": str(evaluation_id), "run_ids": ids}

    def list(self, owner):
        quality = runs.c.result["evaluation"]
        fields = [evaluations.c[name] for name in ("id", "dataset_id", "dataset_version", "provider", "model", "created_at")]
        query = select(*fields, func.count(runs.c.id).label("cases"),
            func.count(runs.c.id).filter(runs.c.status == "completed").label("completed"),
            func.count(runs.c.id).filter(runs.c.status.in_(["failed", "cancelled"])).label("failed"),
            *(func.avg(cast(quality[name].astext, Float)).label(name) for name in ("recall_at_k", "precision_at_k", "mrr"))
        ).select_from(evaluations.outerjoin(runs, runs.c.evaluation_id == evaluations.c.id)).where(
            evaluations.c.owner_id == owner).group_by(*fields).order_by(evaluations.c.created_at.desc()).limit(50)
        with self.database.engine.begin() as conn:
            rows = conn.execute(query).mappings().all()
        return [{**dict(row), "id": str(row["id"]), "created_at": row["created_at"].isoformat()} for row in rows]
