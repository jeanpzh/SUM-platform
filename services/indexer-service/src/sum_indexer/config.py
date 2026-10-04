import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    backend_url: str
    service_token: str
    cpu_processes: int = 2
    extraction_concurrency: int = 2
    embedding_concurrency: int = 2
    writing_concurrency: int = 2
    page_batch_size: int = 10
    max_pages: int = 2000
    embedding_batch_size: int = 32
    chunk_tokens: int = 380
    chunk_overlap: int = 40
    stage_timeout: int = 900
    model: str = "intfloat/multilingual-e5-base"
    revision: str = "d13f1b27baf31030b7fd040960d60d909913633f"
    dimension: int = 768
    max_tokens: int = 512
    embedding_driver: str = "tei"
    embedding_url: str = "http://localhost:8080"
    ollama_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    openai_url: str = "https://api.openai.com/v1"
    tokenizer_model: str = "intfloat/multilingual-e5-base"
    tokenizer_revision: str = "d13f1b27baf31030b7fd040960d60d909913633f"

    @classmethod
    def from_env(cls):
        token = os.environ["SERVICE_TOKEN"]
        if len(token) < 24:
            raise ValueError("SERVICE_TOKEN requiere al menos 24 caracteres.")
        names = {
            "cpu_processes": "CPU_PROCESSES",
            "extraction_concurrency": "EXTRACTION_CONCURRENCY",
            "embedding_concurrency": "EMBEDDING_CONCURRENCY",
            "writing_concurrency": "WRITING_CONCURRENCY",
            "page_batch_size": "PAGE_BATCH_SIZE",
            "max_pages": "MAX_PAGES",
            "embedding_batch_size": "EMBEDDING_BATCH_SIZE",
            "chunk_tokens": "CHUNK_TOKENS",
            "chunk_overlap": "CHUNK_OVERLAP",
            "stage_timeout": "STAGE_TIMEOUT_SECONDS",
            "dimension": "EMBEDDING_DIMENSION",
            "max_tokens": "EMBEDDING_MAX_TOKENS",
        }
        defaults = cls.__dataclass_fields__
        values = {
            key: int(os.environ.get(env, str(defaults[key].default))) for key, env in names.items()
        }
        if (
            any(v <= 0 for k, v in values.items() if k != "chunk_overlap")
            or not 0 <= values["chunk_overlap"] < values["chunk_tokens"]
            or values["chunk_tokens"] >= values["max_tokens"]
        ):
            raise ValueError("Los límites de procesamiento o fragmentación no son válidos.")
        return cls(
            os.environ["DATABASE_URL"],
            os.environ["BACKEND_URL"].rstrip("/"),
            token,
            **values,
            model=os.environ.get("EMBEDDING_MODEL", defaults["model"].default),
            revision=os.environ.get("EMBEDDING_REVISION", defaults["revision"].default),
            embedding_driver=os.environ.get("EMBEDDING_DRIVER", "tei"),
            embedding_url=os.environ.get("EMBEDDING_URL", "http://localhost:8080").rstrip("/"),
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            tokenizer_model=os.environ.get(
                "EMBEDDING_TOKENIZER_MODEL",
                os.environ.get("EMBEDDING_MODEL", defaults["model"].default),
            ),
            tokenizer_revision=os.environ.get(
                "EMBEDDING_TOKENIZER_REVISION",
                os.environ.get("EMBEDDING_REVISION", defaults["revision"].default),
            ),
        )
