"""Server-controlled model allowlist with one LiteLLM transport."""

from __future__ import annotations

from pydantic import BaseModel
from sum_contracts.ai_providers import ProviderRuntime
from sum_contracts.models import ServiceError

from .config import AiSettings, ModelConfig


class ModelChoice(BaseModel):
    provider: str
    model: str
    available: bool
    supports_tools: bool
    supports_structured_output: bool
    pricing_date: str
    input_usd_per_million: float
    output_usd_per_million: float


class ModelRegistry:
    def __init__(self, settings: AiSettings):
        self.settings = settings
        self.runtime = None
        self.configured = {(item.provider, item.model): item for item in settings.models}

    @classmethod
    def from_settings(cls, settings: AiSettings):
        return cls(settings)

    def with_runtime(self, runtime: ProviderRuntime):
        settings = self.settings.model_copy(update={
            "models": tuple(ModelConfig(provider=runtime.provider, **item.model_dump()) for item in runtime.models),
            f"{runtime.provider}_api_key": runtime.api_key.get_secret_value(),
        })
        scoped = ModelRegistry(settings)
        scoped.runtime = runtime
        return scoped

    def _available(self, config: ModelConfig) -> bool:
        if self.runtime and self.runtime.provider == config.provider:
            return True
        if config.provider == "custom":
            return bool(self.settings.custom_url)
        if config.provider == "ollama":
            return True
        return bool(getattr(self.settings, f"{config.provider}_api_key"))

    def list_available(self) -> list[ModelChoice]:
        return [ModelChoice(
            provider=item.provider, model=item.model, available=self._available(item),
            supports_tools=item.supports_tools,
            supports_structured_output=item.supports_structured_output,
            pricing_date=item.pricing_date.isoformat(),
            input_usd_per_million=item.input_usd_per_million,
            output_usd_per_million=item.output_usd_per_million,
        ) for item in self.settings.models]

    def config(self, provider: str, model: str) -> ModelConfig:
        item = self.configured.get((provider, model))
        if item is None:
            raise ServiceError("AI_MODEL_UNKNOWN", "El modelo no está permitido.", 422)
        if not self._available(item):
            raise ServiceError("AI_MODEL_UNAVAILABLE", "El modelo no está disponible.", 503)
        return item

    def resolve(self, provider: str, model: str):
        from .litellm_adapter import chat_model

        self.config(provider, model)
        key = self.runtime.api_key.get_secret_value() if self.runtime else getattr(self.settings, f"{provider}_api_key", "")
        base_url = None
        if provider in {"ollama", "custom"}:
            base_url = self.runtime.base_url if self.runtime else getattr(self.settings, f"{provider}_url")
        return chat_model(provider, model, key, base_url, self.settings.model_timeout_seconds)
