import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    admin_token: str
    internal_token: str
    admin_identity: str = "administracion"
    max_upload_bytes: int = 32 * 1024 * 1024
    max_pending_jobs: int = 1000
    pool_size: int = 10
    allowed_origins: tuple[str, ...] = ()
    env_mode: str = "PRODUCTION"
    ai_identity_secret: str = ""
    ai_service_url: str = "http://ai:8002"
    ai_evaluation_dir: str = "data/ai-evaluation"

    ai_provider_encryption_key: str = ""
    ai_provider_allowed_hosts: tuple[str, ...] = ()
    student_ai_provider: str = "ollama"
    student_ai_model: str = "llama3.2"

    @classmethod
    def from_env(cls):
        admin = os.environ["API_ADMIN_TOKEN"]
        internal = os.environ["SERVICE_TOKEN"]
        if min(len(admin), len(internal)) < 24 or admin == internal:
            raise ValueError("Configure tokens diferentes de al menos 24 caracteres.")
        upload = int(os.environ.get("MAX_UPLOAD_BYTES", str(32 * 1024 * 1024)))
        pending = int(os.environ.get("MAX_PENDING_JOBS", "1000"))
        pool = int(os.environ.get("DB_POOL_SIZE", "10"))
        if min(upload, pending, pool) <= 0:
            raise ValueError("Los límites deben ser positivos.")
        env_mode = os.environ.get("ENV_MODE", "PRODUCTION").upper()
        if env_mode not in {"DEVELOPMENT", "PRODUCTION"}:
            raise ValueError("ENV_MODE debe ser DEVELOPMENT o PRODUCTION.")
        ai_secret = os.environ.get("AI_IDENTITY_SECRET", "")
        if len(ai_secret) < 24:
            raise ValueError("AI_IDENTITY_SECRET requiere al menos 24 caracteres.")
        return cls(
            os.environ["DATABASE_URL"],
            admin,
            internal,
            os.environ.get("ADMIN_IDENTITY", "administracion"),
            upload,
            pending,
            pool,
            tuple(x.strip() for x in os.environ.get("ALLOWED_ORIGINS", "").split(",") if x.strip()),
            env_mode,
            ai_secret,
            os.environ.get("AI_SERVICE_URL", "http://ai:8002"),
            os.environ.get("AI_EVALUATION_DIR", "data/ai-evaluation"),
            os.environ.get("AI_PROVIDER_ENCRYPTION_KEY", ""),
            tuple(x.strip().lower() for x in os.environ.get("AI_PROVIDER_ALLOWED_HOSTS", "localhost,127.0.0.1,host.docker.internal,ollama").split(",") if x.strip()),
            os.environ.get("STUDENT_AI_PROVIDER", "ollama"),
            os.environ.get("STUDENT_AI_MODEL", "llama3.2"),
        )
