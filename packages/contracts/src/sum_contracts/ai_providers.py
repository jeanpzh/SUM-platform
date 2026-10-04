"""Bounded provider configuration; public views never contain credentials."""
from datetime import date
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

ProviderKind = Literal["ollama", "openai", "anthropic", "google", "groq", "custom"]


class ProviderModel(StrictModel):
    model: str = Field(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9._:/-]+$")
    input_usd_per_million: float = Field(ge=0, le=10000)
    output_usd_per_million: float = Field(ge=0, le=10000)
    pricing_date: date


class ProviderInput(StrictModel):
    provider: ProviderKind
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(max_length=500)
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    priority: Literal["high", "normal", "low"] = "normal"
    enabled: bool = True
    models: tuple[ProviderModel, ...] = Field(min_length=1, max_length=20)
    expected_revision: int | None = Field(default=None, ge=1)

    @field_validator("api_key")
    @classmethod
    def bounded_key(cls, value):
        if len(value.get_secret_value()) > 4096:
            raise ValueError("API key exceeds limit")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Use an HTTP(S) base URL without credentials, query or fragment")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("Invalid port") from exc
        path = parsed.path.rstrip("/")
        if path.endswith("/chat/completions"):
            path = path[:-len("/chat/completions")]
        return urlunsplit((parsed.scheme, parsed.netloc.lower(), path, "", ""))

    @field_validator("models")
    @classmethod
    def distinct_models(cls, values):
        if len({item.model for item in values}) != len(values):
            raise ValueError("Models must be distinct")
        return values


class ProviderRuntime(StrictModel):
    config_id: UUID
    revision: int = Field(ge=1)
    provider: ProviderKind
    name: str
    base_url: str
    api_key: SecretStr
    models: tuple[ProviderModel, ...]


class ConnectionProbe(StrictModel):
    provider: ProviderKind
    base_url: str = Field(max_length=500)
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    model: str = Field(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9._:/-]+$")
    config_id: UUID | None = None
    expected_revision: int | None = Field(default=None, ge=1)

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, value):
        return ProviderInput.validate_url(value)

    @field_validator("api_key")
    @classmethod
    def bounded_key(cls, value):
        return ProviderInput.bounded_key(value)

    @model_validator(mode="after")
    def paired_revision(self):
        if (self.config_id is None) != (self.expected_revision is None):
            raise ValueError("A saved connection requires its expected revision")
        return self


class InternalConnectionProbe(StrictModel):
    actor_id: str = Field(min_length=1, max_length=200)
    runtime: ProviderRuntime = Field(repr=False)
    model: str = Field(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9._:/-]+$")

    @model_validator(mode="after")
    def configured_model(self):
        if not any(item.model == self.model for item in self.runtime.models):
            raise ValueError("The probe model must belong to the supplied connection")
        return self


class ConnectionProbeResult(StrictModel):
    success: bool
    code: str = Field(min_length=1, max_length=64)
    latency_ms: float = Field(ge=0)
    tools_supported: bool
    input_tokens: int = Field(ge=0, le=9000)
    output_tokens: int = Field(ge=0, le=9000)
