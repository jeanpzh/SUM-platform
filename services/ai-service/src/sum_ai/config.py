"""Validated, server-owned AI configuration and model allowlist."""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    provider: Literal["ollama", "openai", "anthropic", "google", "groq", "custom"]
    model: str = Field(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9._:/-]+$")
    supports_tools: bool = True
    supports_structured_output: bool = True
    input_usd_per_million: float = Field(ge=0)
    output_usd_per_million: float = Field(ge=0)
    pricing_date: date

    @model_validator(mode="after")
    def required_capabilities(self):
        if not self.supports_tools or not self.supports_structured_output:
            raise ValueError("Admin RAG models require tools and structured output")
        return self


class AiSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    database_url: str
    backend_url: str
    service_token: str = Field(min_length=24, repr=False)
    redis_url: str
    models: tuple[ModelConfig, ...]
    embedding_url: str = "http://embeddings:80"
    ollama_url: str = "http://host.docker.internal:11434"
    openai_api_key: str = Field(default="", repr=False)
    anthropic_api_key: str = Field(default="", repr=False)
    groq_api_key: str = Field(default="", repr=False)
    custom_api_key: str = Field(default="", repr=False)
    custom_url: str = ""
    google_api_key: str = Field(default="", repr=False)
    embedding_input_usd_per_million: float | None = Field(default=None, ge=0)
    embedding_pricing_date: date = date(2026, 10, 3)
    model_timeout_seconds: int = Field(default=30, ge=1, le=60)
    embedding_timeout_seconds: int = Field(default=10, ge=1, le=30)
    run_timeout_seconds: int = Field(default=120, ge=30, le=120)
    academic_gateway_url: str = ""
    student_rules_file: str = ""
    student_requests_per_minute: int = Field(default=5, ge=1, le=100)
    student_requests_per_day: int = Field(default=50, ge=1, le=1000)
    student_tokens_per_minute: int = Field(default=20000, ge=9000, le=1000000)
    student_tokens_per_day: int = Field(default=100000, ge=9000, le=10000000)

    @field_validator("academic_gateway_url")
    @classmethod
    def gateway_url(cls, value):
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Academic gateway requires a server configured HTTP URL without credentials")
        return value.rstrip("/")

    @field_validator("backend_url", "embedding_url", "ollama_url", "redis_url", "database_url")
    @classmethod
    def valid_url(cls, value: str):
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https", "redis", "rediss", "postgresql", "postgresql+psycopg"} or not parsed.hostname:
            raise ValueError("Service URL is invalid")
        return value.rstrip("/")

    @model_validator(mode="after")
    def distinct_models(self):
        ids = [(item.provider, item.model) for item in self.models]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Configure at least one distinct model")
        return self

    @classmethod
    def from_env(cls):
        raw = os.environ.get("AI_MODELS_JSON", "")
        models = json.loads(raw) if raw else [{
            "provider": "ollama", "model": "llama3.2", "input_usd_per_million": 0,
            "output_usd_per_million": 0, "pricing_date": "2026-10-03",
        }]
        return cls(
            database_url=os.environ["DATABASE_URL"],
            backend_url=os.environ["BACKEND_URL"],
            service_token=os.environ["SERVICE_TOKEN"],
            redis_url=os.environ["REDIS_URL"],
            models=models,
            embedding_url=os.environ.get("EMBEDDING_URL", "http://embeddings:80"),
            ollama_url=os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434"),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            groq_api_key=os.environ.get("GROQ_API_KEY", ""),
            custom_api_key=os.environ.get("CUSTOM_API_KEY", ""),
            custom_url=os.environ.get("CUSTOM_AI_URL", ""),
            google_api_key=os.environ.get("GOOGLE_API_KEY", ""),
            embedding_input_usd_per_million=os.environ.get("AI_EMBEDDING_INPUT_USD_PER_MILLION") or None,
            embedding_pricing_date=os.environ.get("AI_EMBEDDING_PRICING_DATE", "2026-10-03"),
            academic_gateway_url=os.environ.get("ACADEMIC_GATEWAY_URL", ""),
            student_rules_file=os.environ.get("STUDENT_RULES_FILE", ""),
            student_requests_per_minute=os.environ.get("STUDENT_REQUESTS_PER_MINUTE", 5),
            student_requests_per_day=os.environ.get("STUDENT_REQUESTS_PER_DAY", 50),
            student_tokens_per_minute=os.environ.get("STUDENT_TOKENS_PER_MINUTE", 20000),
            student_tokens_per_day=os.environ.get("STUDENT_TOKENS_PER_DAY", 100000),
        )
