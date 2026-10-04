"""Durable operation spans. UTC for audit; monotonic durations supplied by the worker."""

import math

from sum_contracts.models import STAGES, JobStopped, ServiceError, Status, require_uuid


def read_timings(conn, job: dict) -> dict:
    rows = conn.execute(
        """SELECT *, GREATEST(0, EXTRACT(EPOCH FROM (clock_timestamp()-started_at))*1000)
        AS elapsed_ms FROM application.indexing_stage_attempts
        WHERE job_id=%s ORDER BY started_at,id""",
        (job["id"],),
    ).fetchall()
    clock = conn.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
    finished = job.get("finished_at")
    total = (finished or clock) - job["created_at"]
    terminal_without_end = (
        job["status"] in {Status.COMPLETED, Status.FAILED, Status.CANCELLED} and not finished
    )
    return {
        "total_ms": None if terminal_without_end else max(0, total.total_seconds() * 1000),
        "cola_inicial_ms": max(
            0, (rows[0]["started_at"] - job["created_at"]).total_seconds() * 1000
        )
        if rows
        else None,
        "activo_ms": sum(row["duration_ms"] or 0 for row in rows),
        "intentos": [
            {
                "intento_id": str(row["id"]),
                "etapa": row["stage"],
                "inicio": row["started_at"].isoformat(),
                "fin": row["finished_at"].isoformat() if row["finished_at"] else None,
                "duracion_ms": row["duration_ms"],
                "transcurrido_ms": float(row["elapsed_ms"])
                if row["outcome"] == "en_curso"
                else None,
                "resultado": row["outcome"],
            }
            for row in rows
        ],
    }


def record_timing(conn, job: dict, data: dict) -> bool:
    attempt = require_uuid(data.get("attempt_id", ""))
    stage, action = data.get("stage"), data.get("action")
    if stage not in STAGES or action not in {"start", "end"}:
        raise ServiceError("TIEMPO_INVALIDO", "La etapa o acción de medición no es válida.")
    existing = conn.execute(
        "SELECT * FROM application.indexing_stage_attempts WHERE id=%s", (attempt,)
    ).fetchone()
    if existing and (existing["job_id"] != job["id"] or existing["stage"] != stage):
        raise ServiceError("TIEMPO_INVALIDO", "El intento no corresponde a esta etapa.")
    if action == "start":
        if existing:
            return False  # Lost acknowledgement: the same attempt keeps its original start.
        if job["status"] in {Status.CANCELLED, Status.FAILED}:
            raise JobStopped()
        # A worker crash cannot provide a monotonic duration: keep it unknown.
        conn.execute(
            """UPDATE application.indexing_stage_attempts
            SET outcome='interrumpido',finished_at=clock_timestamp()
            WHERE job_id=%s AND stage=%s AND outcome='en_curso'""",
            (job["id"], stage),
        )
        conn.execute(
            "INSERT INTO application.indexing_stage_attempts(id,job_id,stage) VALUES(%s,%s,%s)",
            (attempt, job["id"], stage),
        )
        return True
    duration, outcome = data.get("duration_ms"), data.get("outcome")
    if (
        type(duration) not in {int, float}
        or not math.isfinite(duration)
        or duration < 0
        or outcome not in {"completado", "fallido", "cancelado", "interrumpido"}
    ):
        raise ServiceError(
            "TIEMPO_INVALIDO", "La duración o resultado de la medición no es válido."
        )
    if not existing:
        raise ServiceError("TIEMPO_INVALIDO", "El intento todavía no tiene un inicio registrado.")
    if existing["outcome"] != "en_curso":
        return False  # Idempotent end, including a late end of an interrupted attempt.
    conn.execute(
        """UPDATE application.indexing_stage_attempts SET finished_at=clock_timestamp(),
        duration_ms=%s,outcome=%s WHERE id=%s""",
        (duration, outcome, attempt),
    )
    return True
