"""SQLAlchemy Core persistence for versioned provider connections."""
from datetime import date
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Uuid,
    func,
    insert,
    select,
    update,
)
from sum_contracts.ai_providers import ConnectionProbe, ProviderInput, ProviderRuntime
from sum_contracts.models import ServiceError

metadata = MetaData(schema="application")
connections = Table("ai_provider_connections", metadata,
    Column("id", Uuid, primary_key=True), Column("owner_id", String), Column("revision", Integer),
    Column("created_at", DateTime(timezone=True), server_default=func.now()))
revisions = Table("ai_provider_revisions", metadata,
    Column("config_id", Uuid, primary_key=True), Column("revision", Integer, primary_key=True),
    Column("config", JSON), Column("encrypted_key", String),
    Column("created_at", DateTime(timezone=True), server_default=func.now()))

ENDPOINTS = {
    "openai": "https://api.openai.com/v1", "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com", "groq": "https://api.groq.com/openai/v1",
}


class ProviderRepository:
    def __init__(self, database, encryption_key: str, allowed_hosts: tuple[str, ...] = ()):
        self.database = database
        self.cipher = Fernet(encryption_key.encode()) if encryption_key else None
        self.allowed_hosts = set(allowed_hosts)

    def _configured(self):
        if not self.cipher:
            raise ServiceError("AI_PROVIDER_KEY_MISSING", "Configura el cifrado de proveedores en el servidor.", 503)

    def _endpoint(self, data: ProviderInput | ConnectionProbe):
        fixed = ENDPOINTS.get(data.provider)
        if fixed and data.base_url != fixed:
            raise ServiceError("AI_PROVIDER_URL_INVALID", "Usa la URL oficial del proveedor.", 422)
        if not fixed and urlsplit(data.base_url).hostname not in self.allowed_hosts:
            raise ServiceError("AI_PROVIDER_HOST_DENIED", "Autoriza este host en AI_PROVIDER_ALLOWED_HOSTS del servidor.", 422)

    @staticmethod
    def _view(row):
        return {**row["config"], "id": str(row["config_id"]), "revision": row["revision"],
                "has_api_key": bool(row["encrypted_key"]), "created_at": row["created_at"].isoformat()}

    def list(self, owner):
        self._configured()
        query = select(revisions).join(connections,
            (connections.c.id == revisions.c.config_id) & (connections.c.revision == revisions.c.revision)
        ).where(connections.c.owner_id == owner).order_by(connections.c.created_at, connections.c.id).limit(50)
        with self.database.engine.begin() as conn:
            return [self._view(row) for row in conn.execute(query).mappings()]

    def save(self, owner, data: ProviderInput, config_id: str | None = None):
        self._configured()
        self._endpoint(data)
        identifier = UUID(config_id) if config_id else uuid4()
        with self.database.engine.begin() as conn:
            # Lock the same owner row used for run admission; prevents concurrent configuration cap races.
            conn.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(owner, 0))))
            previous_key = ""
            revision = 1
            if config_id:
                current = conn.execute(select(connections).where(connections.c.id == identifier,
                    connections.c.owner_id == owner).with_for_update()).mappings().first()
                if not current:
                    raise ServiceError("AI_PROVIDER_NOT_FOUND", "La conexión no existe.", 404)
                if data.expected_revision != current["revision"]:
                    raise ServiceError("AI_PROVIDER_CONFLICT", "La conexión cambió. Recarga Settings.", 409)
                previous = conn.execute(select(revisions).where(revisions.c.config_id == identifier,
                    revisions.c.revision == current["revision"])).mappings().one()
                if data.provider == previous["config"]["provider"] and data.base_url == previous["config"]["base_url"]:
                    previous_key = previous["encrypted_key"]
                revision = current["revision"] + 1
                conn.execute(update(connections).where(connections.c.id == identifier).values(revision=revision))
            else:
                if data.expected_revision is not None:
                    raise ServiceError("AI_PROVIDER_CONFLICT", "Una conexión nueva no lleva revisión anterior.", 422)
                count = conn.scalar(select(func.count()).select_from(connections).where(connections.c.owner_id == owner))
                if count >= 50:
                    raise ServiceError("AI_PROVIDER_LIMIT", "Máximo 50 conexiones por administrador.", 422)
                conn.execute(insert(connections).values(id=identifier, owner_id=owner, revision=revision))
            raw_key = data.api_key.get_secret_value()
            encrypted = self.cipher.encrypt(raw_key.encode()).decode() if raw_key else previous_key
            if data.provider in ENDPOINTS and not encrypted:
                raise ServiceError("AI_PROVIDER_KEY_REQUIRED", "Este proveedor requiere una API key.", 422)
            config = data.model_dump(mode="json", exclude={"api_key", "expected_revision"})
            row = conn.execute(insert(revisions).values(config_id=identifier, revision=revision,
                config=config, encrypted_key=encrypted).returning(revisions)).mappings().one()
            return self._view(row)

    def public_revision(self, owner, config_id, revision):
        query = select(revisions).join(connections, connections.c.id == revisions.c.config_id).where(
            connections.c.owner_id == owner, revisions.c.config_id == UUID(str(config_id)),
            revisions.c.revision == revision)
        with self.database.engine.begin() as conn:
            row = conn.execute(query).mappings().first()
        if not row:
            raise ServiceError("AI_PROVIDER_NOT_FOUND", "La conexión no existe.", 404)
        return self._view(row)

    def probe_runtime(self, owner: str, probe: ConnectionProbe):
        """Validate a draft and resolve a retained key without saving or mutating it."""
        self._configured()
        self._endpoint(probe)
        key = probe.api_key.get_secret_value()
        if probe.config_id:
            query = select(revisions, connections.c.revision.label("current_revision")).join(
                connections, (connections.c.id == revisions.c.config_id) &
                (connections.c.revision == revisions.c.revision)).where(
                connections.c.id == probe.config_id, connections.c.owner_id == owner)
            with self.database.engine.begin() as conn:
                previous = conn.execute(query).mappings().first()
            if not previous:
                raise ServiceError("AI_PROVIDER_NOT_FOUND", "La conexión no existe.", 404)
            if probe.expected_revision != previous["current_revision"]:
                raise ServiceError("AI_PROVIDER_CONFLICT", "La conexión cambió. Recarga Settings.", 409)
            if not key and probe.provider == previous["config"]["provider"] and probe.base_url == previous["config"]["base_url"]:
                try:
                    key = self.cipher.decrypt(previous["encrypted_key"].encode()).decode() if previous["encrypted_key"] else ""
                except InvalidToken as exc:
                    raise ServiceError("AI_PROVIDER_KEY_INVALID", "No se puede descifrar la conexión.", 503) from exc
        if probe.provider in ENDPOINTS and not key:
            raise ServiceError("AI_PROVIDER_KEY_REQUIRED", "Este proveedor requiere una API key.", 422)
        return ProviderRuntime(config_id=probe.config_id or uuid4(), revision=probe.expected_revision or 1,
            provider=probe.provider, name="Connection probe", base_url=probe.base_url, api_key=key,
            models=[{"model": probe.model, "input_usd_per_million": 0,
                     "output_usd_per_million": 0, "pricing_date": date.today()}])

    def runtime(self, owner, config_id, revision, *, current=False):
        self._configured()
        query = select(revisions, connections.c.revision.label("current_revision")).join(connections,
            connections.c.id == revisions.c.config_id).where(connections.c.owner_id == owner,
            revisions.c.config_id == UUID(str(config_id)), revisions.c.revision == revision)
        with self.database.engine.begin() as conn:
            row = conn.execute(query).mappings().first()
        if not row:
            raise ServiceError("AI_PROVIDER_NOT_FOUND", "La conexión no existe.", 404)
        if current and (row["current_revision"] != revision or not row["config"]["enabled"]):
            raise ServiceError("AI_PROVIDER_CONFLICT", "La conexión cambió o está deshabilitada. Recarga los modelos.", 409)
        try:
            key = self.cipher.decrypt(row["encrypted_key"].encode()).decode() if row["encrypted_key"] else ""
        except InvalidToken as exc:
            raise ServiceError("AI_PROVIDER_KEY_INVALID", "No se puede descifrar la conexión.", 503) from exc
        data = row["config"]
        self._endpoint(ProviderInput(**data))
        return ProviderRuntime(config_id=config_id, revision=revision, api_key=key,
            **{field: data[field] for field in ("provider", "name", "base_url", "models")})

    def catalog(self, owner):
        priority = {"high": 0, "normal": 1, "low": 2}
        result = []
        for connection in sorted(self.list(owner), key=lambda item: (priority[item["priority"]], item["name"])):
            for model in connection["models"]:
                result.append({**model, "provider": connection["provider"], "available": connection["enabled"],
                    "supports_tools": True, "supports_structured_output": True,
                    "provider_config_id": connection["id"], "provider_revision": connection["revision"],
                    "connection_name": connection["name"]})
        return result
