"""Core transaction boundary for auditable admin AI executions."""
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sum_contracts.ai import (
    AI_CONTRACT_VERSION,
    AI_RUN_REQUESTED,
    AI_STUDENT_REQUESTED,
    CreateRunRequest,
    RunContext,
    RunUsage,
)
from sum_contracts.models import ServiceError, require_uuid
from sum_database import SqlDatabase

from .ai_tables import artifacts, events, outbox, runs, usage

TERMINAL = {"completed", "failed", "cancelled"}


class AiRunRepository:
    def __init__(self, database_url: str, pool_size: int = 10, event_delay_seconds: int = 0):
        self.database = SqlDatabase(database_url, pool_size, 3000)
        self.event_delay_seconds = event_delay_seconds

    def open(self):
        self.database.open()

    def close(self):
        self.database.close()

    @staticmethod
    def _view(row: dict) -> dict:
        return {
            "run_id": str(row["id"]),
            "status": row["status"],
            "stage": row["stage"],
            "sequence": row["sequence"],
            "provider": row["request"]["provider"],
            "model": row["request"]["model"],
            "question": row["request"]["question"],
            "provider_config_id": row["request"].get("provider_config_id"),
            "provider_revision": row["request"].get("provider_revision"),
            "result": row["result"],
            "error_code": row["error_code"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            "audience": row["request"].get("audience", "admin"),
            "student_options": row["request"].get("student_options"),
        }

    def _row(self, conn, run_id, owner=None, lock=False):
        query = select(runs).where(runs.c.id == UUID(require_uuid(run_id)))
        if owner is not None:
            query = query.where(runs.c.owner_id == owner)
        if lock:
            query = query.with_for_update()
        row = conn.execute(query).mappings().first()
        if not row:
            raise ServiceError("AI_RUN_NOT_FOUND", "La ejecución no existe o no está autorizada.", 404)
        return row

    def create(self, owner, key, request):
        if not owner or len(owner) > 200 or not 1 <= len(key) <= 200:
            raise ServiceError("AI_INPUT_INVALID", "La identidad o clave no es válida.")
        fingerprint = request.fingerprint()
        with self.database.engine.begin() as conn:
            conn.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(owner, 0))))
            existing = conn.execute(select(runs).where(runs.c.owner_id == owner,
                runs.c.idempotency_key == key)).mappings().first()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise ServiceError("AI_IDEMPOTENCY_CONFLICT", "La clave ya se usó con otra solicitud.", 409)
                return self._view(existing), False
            run_id = uuid4()
            row = conn.execute(insert(runs).values(id=run_id, owner_id=owner, idempotency_key=key,
                fingerprint=fingerprint, request=request.model_dump(mode="json")).returning(runs)).mappings().one()
            conn.execute(insert(outbox).values(id=uuid4(), run_id=run_id,
                event_name=AI_STUDENT_REQUESTED if request.audience == "student" else AI_RUN_REQUESTED,
                payload={"contract_version": AI_CONTRACT_VERSION, "run_id": str(run_id)},
                available_at=func.now() + timedelta(seconds=self.event_delay_seconds)))
            return self._view(row), True

    def get(self, run_id, owner):
        with self.database.engine.begin() as conn:
            row = self._row(conn, run_id, owner)
            view = self._view(row)
            proof = conn.execute(select(artifacts.c.data).where(artifacts.c.run_id == row["id"],
                artifacts.c.kind == "retrieval")).scalar_one_or_none()
            if proof is not None:
                view["retrieval_audit"] = proof
            return view

    def replay(self, owner, key, request):
        with self.database.engine.begin() as conn:
            row = conn.execute(select(runs).where(runs.c.owner_id == owner,
                runs.c.idempotency_key == key)).mappings().first()
        if not row:
            return None
        if row["fingerprint"] != request.fingerprint():
            raise ServiceError("AI_IDEMPOTENCY_CONFLICT", "La clave ya se usó con otra solicitud.", 409)
        return self._view(row)

    def list(self, owner, limit=25, offset=0, days=None, provider="", model="", generation="", status=""):
        conditions = [runs.c.owner_id == owner]
        if days:
            conditions.extend([runs.c.created_at >= func.now() - timedelta(days=days), runs.c.evaluation_id.is_(None), runs.c.status.in_(sorted(TERMINAL))])
        if provider:
            conditions.append(runs.c.request["provider"].astext == provider)
        if model:
            conditions.append(runs.c.request["model"].astext == model)
        if status:
            conditions.append(runs.c.status == status)
        if generation:
            proof = select(artifacts.c.run_id).where(artifacts.c.run_id == runs.c.id,
                artifacts.c.kind == "retrieval", artifacts.c.data["generation_ids"].has_key(generation)).exists()
            completed = runs.c.result["evidence"].contains([{"generation_id": generation}])
            conditions.append(proof | completed)
        query = select(runs).where(*conditions).order_by(runs.c.created_at.desc(), runs.c.id.desc()).limit(limit).offset(offset)
        with self.database.engine.begin() as conn:
            return [self._view(row) for row in conn.execute(query).mappings()]

    def context(self, run_id):
        with self.database.engine.begin() as conn:
            row = self._row(conn, run_id)
            calls = conn.scalar(select(func.count()).select_from(events).where(events.c.run_id == row["id"], events.c.operation_id.like("%:model:%:start")))
            consumed = conn.execute(select(
                func.coalesce(func.sum(usage.c.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(usage.c.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(usage.c.estimated_cost_usd), 0).label("estimated_cost_usd"))
                .where(usage.c.run_id == row["id"], usage.c.operation_id.like("%:model:%"))).mappings().one()
            proof = conn.scalar(select(artifacts.c.data).where(artifacts.c.run_id == row["id"], artifacts.c.kind == "retrieval")) or {}
        if row["status"] in TERMINAL:
            raise ServiceError("AI_RUN_TERMINAL", "La ejecución ya terminó.", 409)
        return RunContext(run_id=row["id"], owner_id=row["owner_id"], request=row["request"],
            status=row["status"], created_at=row["created_at"], evaluation=row["evaluation_context"], model_calls=calls,
            model_usage=RunUsage(**{key: consumed[key] for key in ("input_tokens", "output_tokens", "estimated_cost_usd")}),
            corpus_sha256=proof.get("corpus_sha256"))

    def apply_event(self, run_id, event):
        with self.database.engine.begin() as conn:
            row = self._row(conn, run_id, lock=True)
            duplicate = conn.scalar(select(events.c.sequence).where(events.c.run_id == row["id"],
                events.c.operation_id == event.operation_id))
            if duplicate is not None:
                return self._view(row)
            if row["status"] in TERMINAL and not (row["status"] == "cancelled" and event.kind == "usage"):
                raise ServiceError("AI_RUN_TERMINAL", "La ejecución ya terminó.", 409)
            status = {"started": "running", "completed": "completed", "failed": "failed", "cancelled": "cancelled"}.get(event.kind, row["status"])
            if status == "completed" and event.result is None:
                raise ServiceError("AI_RESULT_MISSING", "Falta el resultado de la ejecución.")
            result = event.result.model_dump(mode="json") if event.result else None
            if result:
                request = CreateRunRequest.model_validate(row["request"])
                supplied = {item.chunk_id: item for item in event.result.evidence}
                analysis = event.result.student_analysis
                if request.audience == "student" and analysis is None:
                    raise ServiceError("AI_RESULT_INVALID", "Falta el análisis estudiantil.", 422)
                if analysis and (request.audience != "student" or any(
                    citation_id not in supplied for citation_id in (
                        *(cid for check in analysis.checks for cid in check.citation_ids),
                        *(cid for item in analysis.deterministic_results for cid in item.result.citationIds)))):
                    raise ServiceError("AI_RESULT_INVALID", "Las comprobaciones carecen de evidencia autorizada.", 422)
                if event.result.provider != request.provider or event.result.model != request.model:
                    raise ServiceError("AI_RESULT_INVALID", "El resultado no corresponde a la solicitud.", 422)
                if request.document_ids and any(item.document_id not in request.document_ids for item in supplied.values()):
                    raise ServiceError("AI_RESULT_INVALID", "La evidencia está fuera del alcance.", 422)
                from .student_result import is_sum_projection_answer
                if (not event.result.abstained and not event.result.citations and
                    not is_sum_projection_answer(request, event.result)) or any(
                    citation.chunk_id not in supplied or
                    any(getattr(citation, key) != getattr(supplied[citation.chunk_id], key)
                        for key in ("document_id", "version_id", "generation_id", "page", "locator"))
                    for citation in event.result.citations):
                    raise ServiceError("AI_RESULT_INVALID", "Las citas no corresponden a la evidencia.", 422)
            if result:
                consumed = conn.execute(select(func.coalesce(func.sum(usage.c.input_tokens), 0).label("input_tokens"),
                    func.coalesce(func.sum(usage.c.output_tokens), 0).label("output_tokens"),
                    func.coalesce(func.sum(usage.c.estimated_cost_usd), 0).label("estimated_cost_usd"))
                    .where(usage.c.run_id == row["id"])).mappings().one()
                result["usage"].update({**consumed, "estimated_cost_usd": float(consumed["estimated_cost_usd"])})
            changes = dict(status=status, sequence=runs.c.sequence + 1, updated_at=func.now())
            if event.stage is not None:
                changes["stage"] = event.stage
            if result is not None:
                changes["result"] = result
            if event.kind in {"failed", "cancelled"}:
                changes["error_code"] = event.code
            elif event.kind == "completed":
                changes["error_code"] = None
            if status in TERMINAL and row["status"] not in TERMINAL:
                changes["finished_at"] = func.now()
            row = conn.execute(update(runs).where(runs.c.id == row["id"]).values(**changes).returning(runs)).mappings().one()
            conn.execute(insert(events).values(run_id=row["id"], sequence=row["sequence"],
                operation_id=event.operation_id, kind=event.kind, stage=event.stage,
                duration_ms=event.duration_ms, code=event.code, payload=event.payload))
            if result:
                conn.execute(pg_insert(artifacts).values(run_id=row["id"], kind="result", data=result).on_conflict_do_nothing())
            if event.kind == "evidence" and "generation_ids" in event.payload:
                conn.execute(pg_insert(artifacts).values(run_id=row["id"], kind="retrieval",
                    data=event.payload).on_conflict_do_nothing())
            if event.kind == "usage":
                data = event.payload
                conn.execute(pg_insert(usage).values(run_id=row["id"], operation_id=event.operation_id,
                    input_tokens=data.get("input_tokens", 0), output_tokens=data.get("output_tokens", 0),
                    estimated_cost_usd=data.get("estimated_cost_usd", 0),
                    pricing_date=date.fromisoformat(data["pricing_date"]) if data.get("pricing_date") else None).on_conflict_do_nothing())
            return self._view(row)

    def events(self, run_id, after, owner):
        if after < 0:
            raise ServiceError("AI_CURSOR_INVALID", "La secuencia no es válida.")
        fields = [events.c[name] for name in ("sequence", "operation_id", "kind", "stage", "duration_ms", "code", "payload", "created_at")]
        with self.database.engine.begin() as conn:
            row = self._row(conn, run_id, owner)
            values = conn.execute(select(*fields).where(events.c.run_id == row["id"],
                events.c.sequence > after).order_by(events.c.sequence).limit(200)).mappings().all()
        return [{**value, "created_at": value["created_at"].isoformat()} for value in values]

    def cancel(self, run_id, owner):
        with self.database.engine.begin() as conn:
            row = self._row(conn, run_id, owner, lock=True)
            if row["status"] == "cancelled":
                return self._view(row)
            if row["status"] in TERMINAL:
                raise ServiceError("AI_RUN_TERMINAL", "La ejecución ya terminó.", 409)
            row = conn.execute(update(runs).where(runs.c.id == row["id"]).values(status="cancelled",
                sequence=runs.c.sequence + 1, updated_at=func.now(), finished_at=func.now()).returning(runs)).mappings().one()
            conn.execute(insert(events).values(run_id=row["id"], sequence=row["sequence"],
                operation_id=f"cancel:{row['sequence']}", kind="cancelled", payload={}))
            return self._view(row)
