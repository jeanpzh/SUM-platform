"""Read the owner's published catalogue, including the previous published version during a replacement."""

from sum_contracts.models import ServiceError, require_uuid


class PublishedLibrary:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def document(row):
        return {
            "documento_id": str(row["document_id"]),
            "version_id": str(row["version_id"]),
            "trabajo_id": str(row["generation_id"]),
            "metadatos": row["metadata"],
            "publicado_en": row["published_at"].isoformat(),
            "tamano_bytes": row["size_bytes"],
            "fragmentos": row["manifest"]["chunks"],
            "perfil": row["manifest"]["profile"],
            "pipeline_version": row["manifest"]["pipeline_version"],
        }

    def list(self, owner: str, query: str = "", limit: int = 25, offset: int = 0):
        # Escape LIKE wildcards: user input is a literal search, not a SQL pattern.
        term = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where = """FROM application.publications p JOIN application.documents d ON d.id=p.document_id
            JOIN application.document_versions v ON v.id=p.version_id
            WHERE d.owner_id=%s AND (%s='' OR v.metadata->>'titulo' ILIKE %s
            OR v.metadata->>'tipo_documento' ILIKE %s OR v.metadata->>'fuente_url' ILIKE %s)"""
        args = (owner, term, "%" + term + "%", "%" + term + "%", "%" + term + "%")
        with self.database.connection() as conn:
            stats = conn.execute(
                "SELECT count(*) AS total,COALESCE(sum((p.manifest->>'chunks')::int),0) AS chunks "
                + where,
                args,
            ).fetchone()
            rows = conn.execute(
                "SELECT p.*,v.metadata,v.size_bytes "
                + where
                + " ORDER BY p.published_at DESC,p.document_id LIMIT %s OFFSET %s",
                (*args, limit, offset),
            ).fetchall()
            return {
                "documentos": [self.document(row) for row in rows],
                "total": stats["total"],
                "fragmentos": stats["chunks"],
                "limite": limit,
                "offset": offset,
            }

    def chunks(
        self,
        document_id: str,
        owner: str,
        limit: int = 20,
        offset: int = 0,
        version_id: str | None = None,
    ):
        document_id = require_uuid(document_id)
        if version_id is not None:
            version_id = require_uuid(version_id)
        with self.database.connection() as conn:
            row = conn.execute(
                """SELECT p.*,v.metadata,v.size_bytes FROM application.publications p
                JOIN application.documents d ON d.id=p.document_id
                JOIN application.document_versions v ON v.id=p.version_id
                WHERE p.document_id=%s AND d.owner_id=%s FOR SHARE OF p""",
                (document_id, owner),
            ).fetchone()
            if not row:
                raise ServiceError(
                    "DOCUMENTO_NO_ENCONTRADO",
                    "El documento publicado no existe o no está autorizado.",
                    404,
                )
            if version_id is not None and str(row["version_id"]) != version_id:
                raise ServiceError(
                    "VERSION_CAMBIADA",
                    "Se publicó una versión nueva. Actualiza la biblioteca.",
                    409,
                )
            chunks = conn.execute(
                """SELECT id,ordinal,page,locator,content,token_count,metadata
                FROM institutional.published_chunks WHERE document_id=%s AND version_id=%s
                ORDER BY ordinal LIMIT %s OFFSET %s""",
                (document_id, row["version_id"], limit, offset),
            ).fetchall()
            return {
                "documento": self.document(row),
                "total": row["manifest"]["chunks"],
                "limite": limit,
                "offset": offset,
                "fragmentos": [
                    {
                        "id": str(c["id"]),
                        "ordinal": c["ordinal"],
                        "pagina": c["page"],
                        "ubicacion": c["locator"],
                        "texto": c["content"],
                        "tokens": c["token_count"],
                        "metadatos": c["metadata"],
                    }
                    for c in chunks
                ],
            }
