import pytest
from sum_ai.config import AiSettings, ModelConfig
from sum_ai.models import ModelRegistry
from sum_contracts.models import ServiceError


def settings():
    return AiSettings(
        database_url="postgresql://sum_retrieval:test@localhost/sum",
        backend_url="http://localhost:8000", service_token="s" * 32,
        redis_url="redis://localhost:6379/0",
        models=(
            ModelConfig(provider="ollama", model="llama3.2", input_usd_per_million=0,
                        output_usd_per_million=0, pricing_date="2026-10-03"),
            ModelConfig(provider="openai", model="gpt-5.1", input_usd_per_million=1,
                        output_usd_per_million=8, pricing_date="2026-10-03"),
            ModelConfig(provider="anthropic", model="claude-sonnet-4-5", input_usd_per_million=3,
                        output_usd_per_million=15, pricing_date="2026-10-03"),
            ModelConfig(provider="google", model="gemini-2.5-pro", input_usd_per_million=1,
                        output_usd_per_million=8, pricing_date="2026-10-03"),
        ),
        openai_api_key="test-key", anthropic_api_key="test-key", google_api_key="test-key",
    )


def test_catalog_has_four_providers_and_no_secrets():
    registry = ModelRegistry.from_settings(settings())
    catalog = registry.list_available()
    assert {item.provider for item in catalog} == {"ollama", "openai", "anthropic", "google"}
    assert all(item.available for item in catalog)
    assert "test-key" not in repr(catalog)


def test_unknown_model_and_missing_credential_rejected_before_call():
    configured = settings().model_copy(update={"openai_api_key": ""})
    registry = ModelRegistry.from_settings(configured)
    assert not next(item for item in registry.list_available() if item.provider == "openai").available
    with pytest.raises(ServiceError) as error:
        registry.resolve("openai", "not-allowlisted")
    assert error.value.status == 422
    with pytest.raises(ServiceError):
        registry.resolve("openai", "gpt-5.1")


def test_model_requires_tool_capability_and_price_date():
    with pytest.raises(ValueError):
        ModelConfig(provider="ollama", model="basic", supports_tools=False,
                    input_usd_per_million=0, output_usd_per_million=0, pricing_date="2026-10-03")
    with pytest.raises(ValueError):
        ModelConfig(provider="ollama", model="basic", input_usd_per_million=0,
                    output_usd_per_million=0, pricing_date="bad-date")


def test_litellm_groq_and_scoped_custom_runtime():
    from sum_contracts.ai_providers import ProviderRuntime
    from uuid import uuid4
    configured = settings().model_copy(update={"groq_api_key": "groq-test-key", "models": (
        ModelConfig(provider="groq", model="openai/gpt-oss-20b", input_usd_per_million=1,
                    output_usd_per_million=2, pricing_date="2026-10-03"),)})
    registry = ModelRegistry(configured)
    model = registry.resolve("groq", "openai/gpt-oss-20b")
    assert type(model).__name__ == "ChatLiteLLM"
    assert model.model == "groq/openai/gpt-oss-20b"
    assert model.max_retries == 0 and model.request_timeout == 30
    runtime = ProviderRuntime(config_id=uuid4(), revision=2, provider="custom", name="Local server",
        base_url="http://localhost:8080/v1", api_key="private-key", models=[dict(model="phi4.gguf",
        input_usd_per_million=0, output_usd_per_million=0, pricing_date="2026-10-03")])
    scoped = registry.with_runtime(runtime)
    model = scoped.resolve("custom", "phi4.gguf")
    assert type(model).__name__ == "ChatLiteLLM"
    assert model.model == "openai/phi4.gguf"
    assert model.api_base == runtime.base_url
    assert model.api_key == "private-key"
    assert registry.runtime is None and registry.settings.groq_api_key == "groq-test-key"


@pytest.mark.parametrize("failure", [None, "auth", "timeout", "tools"])
def test_litellm_connection_probe_is_bounded_and_redacts_errors(monkeypatch, failure):
    import asyncio
    from uuid import uuid4
    from sum_ai.litellm_adapter import litellm, probe_connection
    from sum_contracts.ai_providers import ProviderRuntime

    runtime = ProviderRuntime(config_id=uuid4(), revision=1, provider="custom", name="Probe",
        base_url="http://localhost:8080/v1", api_key="probe-secret",
        models=[dict(model="fixture", input_usd_per_million=0, output_usd_per_million=0,
                     pricing_date="2026-10-03")])
    calls = []

    async def completion(**kwargs):
        calls.append(kwargs)
        assert kwargs["model"] == "openai/fixture"
        assert kwargs["api_key"] == "probe-secret"
        assert kwargs["timeout"] == 8 and kwargs["max_tokens"] == 128
        assert kwargs["num_retries"] == 0
        if failure == "auth":
            error = type("AuthFailure", (Exception,), {"status_code": 401})
            raise error("probe-secret")
        if failure == "timeout":
            raise TimeoutError("probe-secret")
        message = {"role": "assistant", "content": ""}
        if failure != "tools":
            message["tool_calls"] = [{"id": "probe", "type": "function", "function": {
                "name": "connection_probe", "arguments": '{"value":"ok"}'}}]
        return {"model": "fixture", "choices": [{"index": 0, "message": message,
                 "finish_reason": "stop"}], "usage": {"prompt_tokens": 10,
                 "completion_tokens": 5, "total_tokens": 15}}

    monkeypatch.setattr(litellm, "acompletion", completion)
    class Quota:
        settled = []
        async def reserve(self, actor, provider, model, tokens):
            assert tokens == 384
            return "reservation"
        async def settle(self, reservation, tokens):
            self.settled.append(tokens)
    quota = Quota()
    result = asyncio.run(probe_connection(ModelRegistry(settings()), quota, "admin", runtime, "fixture"))
    assert len(calls) == 1
    assert len(quota.settled) == 1
    assert "probe-secret" not in repr(result)
    assert result["success"] is (failure is None)
    assert result["code"] == {None: "AI_CONNECTION_OK", "auth": "AI_PROVIDER_AUTH_FAILED",
                              "timeout": "AI_PROVIDER_TIMEOUT", "tools": "AI_TOOLS_NOT_VERIFIED"}[failure]
    assert quota.settled == ([384] if failure in {"auth", "timeout"} else [15])
