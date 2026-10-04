from __future__ import annotations

from uuid import uuid4

from sum_contracts.models import (
    CONTRACT_VERSION,
    INDEX_REQUESTED,
    PRIORITIES,
    STAGES,
    TERMINAL,
    JobStopped,
    Metadata,
    ServiceError,
    Status,
    require_uuid,
    validate_progress,
)
from sum_database import SqlDatabase

from .library import PublishedLibrary
from .timings import read_timings, record_timing

ERROR_MESSAGES = {
    "ARCHIVO_INVALIDO": "El archivo está dañado o no se puede leer.",
    "TEXTO_INSUFICIENTE": "No se encontró texto suficiente para indexar el documento.",
    "LIMITE_PAGINAS": "El documento supera el límite de páginas permitido.",
    "FORMATO_NO_ADMITIDO": "El formato del documento no está admitido.",
    "OCR_NO_DISPONIBLE": "No se pudo ejecutar el reconocimiento de texto en español.",
    "MODELO_INCOMPATIBLE": "La configuración de embeddings no es compatible con el trabajo.",
    "LIMITE_TIEMPO": "El procesamiento superó el tiempo permitido.",
    "CALIDAD_TABLA": "La extracción de una tabla requiere revisión antes de publicar.",
    "REINTENTOS_AGOTADOS": "No se pudo completar la indexación después de los reintentos.",
}


def view(row: dict) -> dict:
    return {
        "documento_id": str(row["document_id"]),
        "version_id": str(row["version_id"]),
        "trabajo_id": str(row["id"]),
        "estado": row["status"],
        "etapa": row["stage"],
        "mensaje": row["message"],
        "progreso": row["counts"],
        "secuencia": row["sequence"],
        "codigo_error": row["error_code"],
        "actualizado_en": row["updated_at"].isoformat(),
        "estado_url": f"/v1/indexing-jobs/{row['id']}",
    }


class PostgresJobs:
    def __init__(self, database_url: str, pool_size: int = 10, max_pending: int = 1000):
        self.database = SqlDatabase(database_url, pool_size, 15000)
        self.max_pending = max_pending
        self.library = PublishedLibrary(self.database)

    def open(self):
        self.database.open()

    def close(self):
        self.database.close()

    @staticmethod
    def json(data):
        return data

    def _job(self, conn, job_id: str, owner: str | None = None, lock: bool = False) -> dict:
        query = "SELECT * FROM application.indexing_jobs WHERE id=%s"
        args = [require_uuid(job_id)]
        if owner is not None:
            query += " AND owner_id=%s"
            args.append(owner)
        if lock:
            query += " FOR UPDATE"
        row = conn.execute(query, args).fetchone()
        if row is None:
            raise ServiceError(
                "TRABAJO_NO_ENCONTRADO", "El trabajo no existe o no está autorizado.", 404
            )
        return row

    def _event(self, conn, job_id: str, operation: str):
        row = conn.execute(
            "UPDATE application.indexing_jobs SET sequence=sequence+1, updated_at=now() WHERE id=%s RETURNING *",
            (job_id,),
        ).fetchone()
        payload = self._view(conn, row)
        conn.execute(
            "INSERT INTO application.indexing_events(job_id,sequence,operation_id,payload) VALUES(%s,%s,%s,%s)",
            (job_id, row["sequence"], operation, self.json(payload)),
        )
        return payload

    def accept(
        self,
        owner: str,
        key: str,
        fingerprint: str,
        source: dict,
        metadata: Metadata,
        document_id: str | None = None,
    ) -> tuple[dict, bool]:
        with self.database.connection() as conn:
            # Serialize the admission count per owner, not the upload itself.
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (owner,))
            existing = conn.execute(
                "SELECT * FROM application.indexing_jobs WHERE owner_id=%s AND idempotency_key=%s",
                (owner, key),
            ).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise ServiceError(
                        "IDEMPOTENCIA_CONFLICTO",
                        "La clave ya fue usada con un documento o metadatos diferentes.",
                        409,
                    )
                return self._view(conn, existing), False
            pending = conn.execute(
                "SELECT count(*) AS n FROM application.indexing_jobs WHERE owner_id=%s AND status IN ('en_cola','procesando')",
                (owner,),
            ).fetchone()["n"]
            if pending >= self.max_pending:
                raise ServiceError(
                    "CAPACIDAD_AGOTADA",
                    "Hay demasiados documentos pendientes. Intente más tarde.",
                    429,
                )
            job_id, version_id = str(uuid4()), str(uuid4())
            profile = self.embedding_profile(conn)
            if document_id:
                document_id = require_uuid(document_id)
                doc = conn.execute(
                    "SELECT * FROM application.documents WHERE id=%s AND owner_id=%s FOR UPDATE",
                    (document_id, owner),
                ).fetchone()
                if not doc:
                    raise ServiceError(
                        "DOCUMENTO_NO_ENCONTRADO",
                        "El documento no existe o no está autorizado.",
                        404,
                    )
                stale = conn.execute(
                    "SELECT id FROM application.indexing_jobs WHERE document_id=%s AND status IN ('en_cola','procesando') FOR UPDATE",
                    (document_id,),
                ).fetchall()
                for item in stale:
                    conn.execute(
                        "UPDATE application.indexing_jobs SET finished_at=clock_timestamp(),status='cancelado', message='El trabajo fue reemplazado por una nueva versión.' WHERE id=%s",
                        (item["id"],),
                    )
                    self._event(conn, str(item["id"]), "superseded")
                conn.execute(
                    "UPDATE application.documents SET current_version_id=%s WHERE id=%s",
                    (version_id, document_id),
                )
            else:
                document_id = str(uuid4())
                conn.execute(
                    "INSERT INTO application.documents(id,owner_id,current_version_id) VALUES(%s,%s,%s)",
                    (document_id, owner, version_id),
                )
            conn.execute(
                "INSERT INTO application.document_versions(id,document_id,metadata,object_key,mime_type,sha256,size_bytes,embedding_profile) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    version_id,
                    document_id,
                    self.json(metadata.to_dict()),
                    source["key"],
                    source["mime"],
                    source["sha256"],
                    source["size"],
                    self.storage_profile(profile),
                ),
            )
            conn.execute(
                "INSERT INTO application.indexing_jobs(id,document_id,version_id,owner_id,idempotency_key,fingerprint,priority) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    job_id,
                    document_id,
                    version_id,
                    owner,
                    key,
                    fingerprint,
                    PRIORITIES[metadata.prioridad],
                ),
            )
            event = {
                "contract_version": CONTRACT_VERSION,
                "job_id": job_id,
                "priority": PRIORITIES[metadata.prioridad],
            }
            conn.execute(
                "INSERT INTO application.outbox(id,job_id,event_name,payload) VALUES(%s,%s,%s,%s)",
                (uuid4(), job_id, INDEX_REQUESTED, self.json(event)),
            )
            return self._event(conn, job_id, "accepted"), True

    def get(self, job_id: str, owner: str | None = None) -> dict:
        with self.database.connection() as conn:
            return self._view(conn, self._job(conn, job_id, owner))

    @staticmethod
    def storage_profile(profile):
        # Pipeline artifacts already use EmbeddingProfile's canonical field names.
        provider = profile["provider"]
        model = profile["model"] if provider == "tei" else f"{provider}:{profile['model']}"
        return {
            "model": model,
            "revision": profile["revision"],
            "dimension": profile["dimension"],
            "max_tokens": profile["max_tokens"],
            "passage_prefix": "passage: " if provider == "tei" else "",
            "query_prefix": "query: " if provider == "tei" else "",
            "normalized": True,
        }

    @staticmethod
    def input_profile(profile):
        if not isinstance(profile, dict) or set(profile) != {
            "provider",
            "model",
            "revision",
            "dimension",
            "max_tokens",
        }:
            raise ServiceError("PERFIL_INVALIDO", "El perfil de embeddings no es válido.")
        if (
            not isinstance(profile["provider"], str)
            or profile["provider"] not in {"tei", "ollama", "openai"}
            or not isinstance(profile["model"], str)
            or not 1 <= len(profile["model"]) <= 200
        ):
            raise ServiceError("PERFIL_INVALIDO", "El proveedor o modelo no es válido.")
        if not isinstance(profile["revision"], str) or not 1 <= len(profile["revision"]) <= 200:
            raise ServiceError(
                "PERFIL_INVALIDO", "La revisión es obligatoria y no puede exceder 200 caracteres."
            )
        if type(profile["dimension"]) is not int or profile["dimension"] != 768:
            raise ServiceError(
                "PERFIL_INVALIDO", "El índice pgvector actual requiere exactamente 768 dimensiones."
            )
        if type(profile["max_tokens"]) is not int or not 64 <= profile["max_tokens"] <= 8192:
            raise ServiceError("PERFIL_INVALIDO", "El límite debe estar entre 64 y 8192 tokens.")
        if profile["provider"] == "openai" and not profile["model"].startswith("text-embedding-3-"):
            raise ServiceError(
                "PERFIL_INVALIDO", "Usa un modelo text-embedding-3 para configurar sus dimensiones."
            )
        return profile

    def embedding_profile(self, conn=None):
        if conn is not None:
            row = conn.execute(
                "SELECT profile FROM application.embedding_configuration WHERE singleton=true"
            ).fetchone()
            return row["profile"]
        with self.database.connection() as connection:
            return self.embedding_profile(connection)

    def set_embedding_profile(self, profile):
        profile = self.input_profile(profile)
        with self.database.connection() as conn:
            conn.execute(
                "INSERT INTO application.embedding_configuration(singleton,profile) VALUES(true,%s) ON CONFLICT(singleton) DO UPDATE SET profile=EXCLUDED.profile,updated_at=now()",
                (self.json(profile),),
            )
            return profile

    @staticmethod
    def public_job(row):
        payload = view(row)
        metadata = row["metadata"]
        title = metadata.get("titulo", "Documento")
        return {**payload, "titulo": title, "archivo": title + ".pdf", "metadatos": metadata}

    def list_jobs(self, owner, status=None, limit=25, offset=0):
        statuses = {
            "queued": "en_cola",
            "processing": "procesando",
            "published": "completado",
            "failed": "fallido",
            "cancelled": "cancelado",
        }
        if status is not None and status not in {*statuses, "active"}:
            raise ServiceError("FILTRO_INVALIDO", "El estado solicitado no es válido.")
        params = [owner]
        clause = "j.owner_id=%s"
        if status == "active":
            clause += " AND j.status IN ('en_cola','procesando')"
        elif status:
            clause += " AND j.status=%s"
            params.append(statuses[status])
        with self.database.connection() as conn:
            stats = conn.execute(
                "SELECT status,count(*) AS total FROM application.indexing_jobs WHERE owner_id=%s GROUP BY status",
                (owner,),
            ).fetchall()
            state_counts = {row["status"]: row["total"] for row in stats}
            total = sum(state_counts.values())
            if status == "active":
                total = state_counts.get("en_cola", 0) + state_counts.get("procesando", 0)
            elif status:
                total = state_counts.get(statuses[status], 0)
            rows = conn.execute(
                "SELECT j.*,v.metadata FROM application.indexing_jobs j JOIN application.document_versions v ON v.id=j.version_id WHERE "
                + clause
                + " ORDER BY j.created_at DESC,j.id DESC LIMIT %s OFFSET %s",
                (*params, limit, offset),
            ).fetchall()
            return {
                "trabajos": [
                    {
                        **self._view(conn, row),
                        "titulo": row["metadata"].get("titulo", "Documento"),
                        "archivo": row["metadata"].get("titulo", "Documento") + ".pdf",
                        "metadatos": row["metadata"],
                    }
                    for row in rows
                ],
                "total": total,
                "limite": limit,
                "offset": offset,
                "estados": {
                    "queued": state_counts.get("en_cola", 0),
                    "processing": state_counts.get("procesando", 0),
                    "published": state_counts.get("completado", 0),
                    "failed": state_counts.get("fallido", 0),
                    "cancelled": state_counts.get("cancelado", 0),
                },
            }

    def reindex(self, owner, document_id):
        document_id = require_uuid(document_id)
        with self.database.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (owner,))
            doc = conn.execute(
                "SELECT * FROM application.documents WHERE id=%s AND owner_id=%s FOR UPDATE",
                (document_id, owner),
            ).fetchone()
            if not doc:
                raise ServiceError(
                    "DOCUMENTO_NO_ENCONTRADO", "El documento no existe o no está autorizado.", 404
                )
            publication = conn.execute(
                "SELECT p.*,v.metadata,v.object_key,v.mime_type,v.sha256,v.size_bytes FROM application.publications p JOIN application.document_versions v ON v.id=p.version_id WHERE p.document_id=%s FOR UPDATE OF p",
                (document_id,),
            ).fetchone()
            if not publication:
                raise ServiceError(
                    "DOCUMENTO_NO_PUBLICADO", "El documento todavía no está publicado.", 409
                )
            active = conn.execute(
                "SELECT id FROM application.indexing_jobs WHERE document_id=%s AND status IN ('en_cola','procesando') FOR UPDATE",
                (document_id,),
            ).fetchone()
            if active:
                raise ServiceError(
                    "REINDEXACION_EN_CURSO", "El documento ya tiene una versión en indexación.", 409
                )
            profile = self.embedding_profile(conn)
            pending = conn.execute(
                "SELECT count(*) AS n FROM application.indexing_jobs WHERE owner_id=%s AND status IN ('en_cola','procesando')",
                (owner,),
            ).fetchone()["n"]
            if pending >= self.max_pending:
                raise ServiceError(
                    "CAPACIDAD_AGOTADA",
                    "Hay demasiados documentos pendientes. Intente más tarde.",
                    429,
                )
            job, version = str(uuid4()), str(uuid4())
            conn.execute(
                "INSERT INTO application.document_versions(id,document_id,metadata,object_key,mime_type,sha256,size_bytes,embedding_profile) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    version,
                    document_id,
                    publication["metadata"],
                    publication["object_key"],
                    publication["mime_type"],
                    publication["sha256"],
                    publication["size_bytes"],
                    self.storage_profile(profile),
                ),
            )
            conn.execute(
                "UPDATE application.documents SET current_version_id=%s WHERE id=%s",
                (version, document_id),
            )
            conn.execute(
                "INSERT INTO application.indexing_jobs(id,document_id,version_id,owner_id,idempotency_key,fingerprint,priority) VALUES(%s,%s,%s,%s,%s,%s,0)",
                (job, document_id, version, owner, str(uuid4()), publication["sha256"]),
            )
            conn.execute(
                "INSERT INTO application.outbox(id,job_id,event_name,payload) VALUES(%s,%s,%s,%s)",
                (
                    uuid4(),
                    job,
                    INDEX_REQUESTED,
                    {"contract_version": CONTRACT_VERSION, "job_id": job, "priority": 0},
                ),
            )
            return self._event(conn, job, "reindex-accepted")

    def stale_profile_count(self, owner):
        with self.database.connection() as conn:
            target = self.storage_profile(self.embedding_profile(conn))
            row = conn.execute(
                """SELECT count(*) AS total FROM application.publications p
                JOIN application.documents d ON d.id=p.document_id
                JOIN application.document_versions v ON v.id=p.version_id
                WHERE d.owner_id=%s AND v.embedding_profile IS DISTINCT FROM %s
                AND NOT EXISTS (SELECT 1 FROM application.indexing_jobs j
                    WHERE j.document_id=d.id AND j.status IN ('en_cola','procesando'))""",
                (owner, self.json(target)),
            ).fetchone()
            return row["total"]

    def reindex_stale(self, owner, limit=100):
        with self.database.connection() as conn:
            profile = self.storage_profile(self.embedding_profile(conn))
            docs = conn.execute(
                """SELECT p.document_id FROM application.publications p
                JOIN application.documents d ON d.id=p.document_id
                JOIN application.document_versions v ON v.id=p.version_id
                WHERE d.owner_id=%s AND v.embedding_profile IS DISTINCT FROM %s
                AND NOT EXISTS (SELECT 1 FROM application.indexing_jobs j
                    WHERE j.document_id=d.id AND j.status IN ('en_cola','procesando'))
                ORDER BY p.published_at LIMIT %s""",
                (owner, self.json(profile), limit),
            ).fetchall()
        accepted = []
        for row in docs:
            try:
                accepted.append(self.reindex(owner, str(row["document_id"])))
            except ServiceError as exc:
                if exc.code not in {"REINDEXACION_EN_CURSO", "CAPACIDAD_AGOTADA"}:
                    raise
                if exc.code == "CAPACIDAD_AGOTADA":
                    break
        return {"trabajos": accepted, "total": len(accepted)}

    def delete_test_document(self, owner, document_id, confirmation, mode):
        if mode != "DEVELOPMENT":
            raise ServiceError(
                "MODO_NO_ADMITIDO",
                "Eliminar registros de prueba solo está permitido en DEVELOPMENT.",
                403,
            )
        document_id = require_uuid(document_id)
        with self.database.connection() as conn:
            doc = conn.execute(
                "SELECT * FROM application.documents WHERE id=%s AND owner_id=%s FOR UPDATE",
                (document_id, owner),
            ).fetchone()
            if not doc:
                raise ServiceError(
                    "DOCUMENTO_NO_ENCONTRADO", "El documento no existe o no está autorizado.", 404
                )
            version = conn.execute(
                "SELECT metadata,object_key FROM application.document_versions WHERE id=%s",
                (doc["current_version_id"],),
            ).fetchone()
            if not version:
                raise ServiceError(
                    "DOCUMENTO_NO_ENCONTRADO", "La versión del documento no existe.", 404
                )
            title = version["metadata"].get("titulo", "")
            if not isinstance(confirmation, str) or confirmation != title:
                raise ServiceError(
                    "CONFIRMACION_REQUERIDA",
                    "Escribe el título exacto para confirmar la eliminación.",
                    409,
                )
            if conn.execute(
                "SELECT 1 FROM application.indexing_jobs WHERE document_id=%s AND status IN ('en_cola','procesando') FOR UPDATE",
                (document_id,),
            ).fetchone():
                raise ServiceError(
                    "TRABAJO_ACTIVO",
                    "Cancela o espera la indexación antes de eliminar este registro.",
                    409,
                )
            keys = conn.execute(
                "SELECT object_key FROM application.document_versions WHERE document_id=%s",
                (document_id,),
            ).fetchall()
            generations = conn.execute(
                "SELECT institutional.delete_document_generations(%s) AS id", (document_id,)
            ).fetchall()
            for key in {row["object_key"] for row in keys}:
                conn.execute(
                    "INSERT INTO application.object_deletions(object_key,document_id,kind) VALUES(%s,%s,'object') ON CONFLICT DO NOTHING",
                    (key, document_id),
                )
            for generation in generations:
                conn.execute(
                    "INSERT INTO application.object_deletions(object_key,document_id,kind) VALUES(%s,%s,'prefix') ON CONFLICT DO NOTHING",
                    (f"derived/{generation['id']}", document_id),
                )
            conn.execute(
                "DELETE FROM application.publications WHERE document_id=%s", (document_id,)
            )
            conn.execute(
                "DELETE FROM application.indexing_events WHERE job_id IN (SELECT id FROM application.indexing_jobs WHERE document_id=%s)",
                (document_id,),
            )
            conn.execute(
                "DELETE FROM application.outbox WHERE job_id IN (SELECT id FROM application.indexing_jobs WHERE document_id=%s)",
                (document_id,),
            )
            conn.execute(
                "DELETE FROM application.indexing_jobs WHERE document_id=%s", (document_id,)
            )
            conn.execute(
                "DELETE FROM application.document_versions WHERE document_id=%s", (document_id,)
            )
            conn.execute("DELETE FROM application.documents WHERE id=%s", (document_id,))
            return {
                "documento_id": document_id,
                "titulo": title,
            }

    def pending_object_deletions(self, document_id=None):
        with self.database.connection() as conn:
            return conn.execute(
                "SELECT * FROM application.object_deletions"
                + (" WHERE document_id=%s" if document_id else "")
                + " ORDER BY created_at LIMIT 100",
                (document_id,) if document_id else (),
            ).fetchall()

    def acknowledge_object_deletion(self, key):
        with self.database.connection() as conn:
            conn.execute("DELETE FROM application.object_deletions WHERE object_key=%s", (key,))

    def _view(self, conn, row):
        return {**view(row), "tiempos": read_timings(conn, row)}

    def set_job_embedding_profile(self, job_id, profile):
        if (
            not isinstance(profile, dict)
            or set(profile)
            != {
                "model",
                "revision",
                "dimension",
                "max_tokens",
                "passage_prefix",
                "query_prefix",
                "normalized",
            }
            or not isinstance(profile["model"], str)
            or type(profile["dimension"]) is not int
            or profile["dimension"] != 768
        ):
            raise ServiceError(
                "PERFIL_INVALIDO", "El modelo no devolvió un perfil compatible con este índice."
            )
        with self.database.connection() as conn:
            job = self._job(conn, job_id, lock=True)
            if job["status"] in {Status.CANCELLED, Status.FAILED}:
                raise JobStopped()
            expected = conn.execute(
                "SELECT embedding_profile FROM application.document_versions WHERE id=%s FOR UPDATE",
                (job["version_id"],),
            ).fetchone()["embedding_profile"]
            resolved = {**expected}
            if expected["revision"] == "auto" and expected["model"].startswith("ollama:"):
                resolved["revision"] = profile["revision"]
            if resolved != profile:
                raise ServiceError(
                    "MODELO_INCOMPATIBLE",
                    "El perfil del proveedor no coincide con el perfil del trabajo.",
                )
            conn.execute(
                "UPDATE application.document_versions SET embedding_profile=%s WHERE id=%s",
                (self.json(profile), job["version_id"]),
            )
            active = self.embedding_profile(conn)
            active_model = (
                active["model"]
                if active["provider"] == "tei"
                else f"{active['provider']}:{active['model']}"
            )
            if (
                active["revision"] == "auto"
                and active_model == profile["model"]
                and active["dimension"] == profile["dimension"]
            ):
                active["revision"] = profile["revision"]
                conn.execute(
                    "UPDATE application.embedding_configuration SET profile=%s,updated_at=now() WHERE singleton=true",
                    (self.json(active),),
                )
            return self._view(conn, job)

    def timing(self, job_id: str, data: dict) -> dict:
        with self.database.connection() as conn:
            job = self._job(conn, job_id, lock=True)
            if record_timing(conn, job, data):
                return self._event(conn, job_id, f"timing-{data['attempt_id']}-{data['action']}")
            return self._view(conn, job)

    def context(self, job_id: str) -> dict:
        with self.database.connection() as conn:
            job = self._job(conn, job_id)
            version = conn.execute(
                "SELECT v.*,d.current_version_id FROM application.document_versions v JOIN application.documents d ON d.id=v.document_id WHERE v.id=%s",
                (job["version_id"],),
            ).fetchone()
            if (
                job["status"] in {Status.CANCELLED, Status.FAILED}
                or version["id"] != version["current_version_id"]
            ):
                raise JobStopped()
            return {
                "contract_version": CONTRACT_VERSION,
                "job_id": str(job["id"]),
                "document_id": str(job["document_id"]),
                "version_id": str(job["version_id"]),
                "status": job["status"],
                "metadata": version["metadata"],
                "embedding_profile": version["embedding_profile"],
                "source": {
                    "key": version["object_key"],
                    "mime": version["mime_type"],
                    "sha256": version["sha256"],
                    "size": version["size_bytes"],
                },
            }

    def progress(self, job_id: str, update: dict) -> dict:
        validate_progress(update)
        with self.database.connection() as conn:
            job = self._job(conn, job_id, lock=True)
            if job["status"] in {Status.CANCELLED, Status.FAILED}:
                raise JobStopped()
            if job["status"] == Status.COMPLETED:
                return self._view(conn, job)
            duplicate = conn.execute(
                "SELECT 1 FROM application.indexing_events WHERE job_id=%s AND operation_id=%s",
                (job_id, update["operation_id"]),
            ).fetchone()
            if duplicate or (
                job["stage"] and STAGES.index(update["stage"]) < STAGES.index(job["stage"])
            ):
                conn.execute(
                    "UPDATE application.indexing_jobs SET heartbeat_at=now() WHERE id=%s", (job_id,)
                )
                return self._view(conn, job)
            counts = dict(job["counts"])
            for name, count in update.get("counts", {}).items():
                counts[name] = max(counts.get(name, 0), count)
            conn.execute(
                "UPDATE application.indexing_jobs SET status='procesando',stage=%s,message=%s,counts=%s,heartbeat_at=now() WHERE id=%s",
                (update["stage"], update["message"], self.json(counts), job_id),
            )
            return self._event(conn, job_id, update["operation_id"])

    def complete(self, job_id: str, manifest: dict) -> dict:
        required = {
            "generation_id",
            "document_id",
            "version_id",
            "chunks",
            "profile",
            "pipeline_version",
            "text_key",
        }
        if not isinstance(manifest, dict) or set(manifest) != required:
            raise ServiceError("MANIFIESTO_INVALIDO", "El manifiesto de publicación no es válido.")
        if type(manifest["chunks"]) is not int or manifest["chunks"] <= 0:
            raise ServiceError(
                "MANIFIESTO_INVALIDO", "El manifiesto no contiene fragmentos válidos."
            )
        with self.database.connection() as conn:
            initial = self._job(conn, job_id)
            doc = conn.execute(
                "SELECT * FROM application.documents WHERE id=%s FOR UPDATE",
                (initial["document_id"],),
            ).fetchone()
            job = self._job(conn, job_id, lock=True)
            if any(
                str(job[field]) != require_uuid(manifest[name])
                for field, name in [
                    ("id", "generation_id"),
                    ("document_id", "document_id"),
                    ("version_id", "version_id"),
                ]
            ):
                raise ServiceError(
                    "MANIFIESTO_INVALIDO", "El manifiesto no corresponde al trabajo."
                )
            if job["status"] == Status.COMPLETED:
                return self._view(conn, job)
            if job["status"] in TERMINAL or doc["current_version_id"] != job["version_id"]:
                raise JobStopped()
            conn.execute(
                "INSERT INTO application.publications(document_id,version_id,generation_id,manifest) VALUES(%s,%s,%s,%s) ON CONFLICT(document_id) DO UPDATE SET version_id=EXCLUDED.version_id,generation_id=EXCLUDED.generation_id,manifest=EXCLUDED.manifest,published_at=now()",
                (job["document_id"], job["version_id"], job_id, self.json(manifest)),
            )
            conn.execute(
                "UPDATE application.indexing_jobs SET finished_at=clock_timestamp(),status='completado',stage='publicando',message='Documento indexado y disponible para consultas.',counts=counts || %s,heartbeat_at=now() WHERE id=%s",
                (
                    self.json({"fragmentos": manifest["chunks"], "vectores": manifest["chunks"]}),
                    job_id,
                ),
            )
            return self._event(conn, job_id, "completed")

    def fail(self, job_id: str, code: str) -> dict:
        if code not in ERROR_MESSAGES:
            code = "REINTENTOS_AGOTADOS"
        with self.database.connection() as conn:
            job = self._job(conn, job_id, lock=True)
            if job["status"] in TERMINAL:
                return self._view(conn, job)
            conn.execute(
                "UPDATE application.indexing_jobs SET finished_at=clock_timestamp(),status='fallido',error_code=%s,message=%s WHERE id=%s",
                (code, ERROR_MESSAGES[code], job_id),
            )
            return self._event(conn, job_id, "failed")

    def cancel(self, job_id: str, owner: str) -> dict:
        with self.database.connection() as conn:
            initial = self._job(conn, job_id, owner)
            conn.execute(
                "SELECT id FROM application.documents WHERE id=%s FOR UPDATE",
                (initial["document_id"],),
            )
            job = self._job(conn, job_id, owner, lock=True)
            if job["status"] == Status.CANCELLED:
                return self._view(conn, job)
            if job["status"] in TERMINAL:
                raise ServiceError(
                    "TRABAJO_TERMINADO", "El trabajo ya terminó y no se puede cancelar.", 409
                )
            conn.execute(
                "UPDATE application.indexing_jobs SET finished_at=clock_timestamp(),status='cancelado',message='La indexación fue cancelada.' WHERE id=%s",
                (job_id,),
            )
            return self._event(conn, job_id, "cancelled")

    def events(self, job_id: str, after: int, owner: str) -> list[dict]:
        with self.database.connection() as conn:
            self._job(conn, job_id, owner)
            rows = conn.execute(
                "SELECT payload FROM application.indexing_events WHERE job_id=%s AND sequence>%s ORDER BY sequence LIMIT 100",
                (job_id, after),
            ).fetchall()
            return [row["payload"] for row in rows]

    def claim_outbox(self, limit: int = 20) -> list[dict]:
        with self.database.connection() as conn:
            return conn.execute(
                """WITH pending AS (
                SELECT id FROM application.outbox WHERE delivered_at IS NULL
                AND available_at<=now() AND (claimed_until IS NULL OR claimed_until<now())
                ORDER BY available_at FOR UPDATE SKIP LOCKED LIMIT %s
            ) UPDATE application.outbox o SET claim_token=%s,claimed_until=now()+interval '120 seconds',attempts=attempts+1
              FROM pending p WHERE o.id=p.id RETURNING o.*""",
                (limit, uuid4()),
            ).fetchall()

    def ack_outbox(self, row: dict):
        with self.database.connection() as conn:
            conn.execute(
                "UPDATE application.outbox SET delivered_at=now(),claimed_until=NULL WHERE id=%s AND claim_token=%s",
                (row["id"], row["claim_token"]),
            )

    def retry_outbox(self, row: dict):
        with self.database.connection() as conn:
            conn.execute(
                "UPDATE application.outbox SET claimed_until=NULL,available_at=now()+make_interval(secs=>%s) WHERE id=%s AND claim_token=%s",
                (min(300, 2 ** min(row["attempts"], 8)), row["id"], row["claim_token"]),
            )
