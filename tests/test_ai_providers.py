import pytest
from pydantic import ValidationError
from sum_contracts.ai import CreateRunRequest
from sum_contracts.ai_providers import ProviderInput


def sample(**changes):
    return dict(provider="groq", name="Groq research", base_url="https://api.groq.com/openai/v1",
                api_key="test-secret", models=[dict(model="openai/gpt-oss-20b", input_usd_per_million=1,
                output_usd_per_million=2, pricing_date="2026-10-03")], **changes)


def test_provider_inputs_are_bounded_and_redact_key():
    value = ProviderInput.model_validate(sample())
    assert "test-secret" not in repr(value)
    with pytest.raises(ValidationError):
        ProviderInput.model_validate({**sample(), "models": []})
    with pytest.raises(ValidationError):
        ProviderInput.model_validate({**sample(), "models": sample()["models"] * 2})
    with pytest.raises(ValidationError):
        ProviderInput.model_validate({**sample(), "base_url": "https://user:password@example.test/v1"})


def test_custom_completion_url_normalized_and_version_required():
    value = ProviderInput.model_validate({**sample(), "provider": "custom",
        "base_url": "http://localhost:8080/v1/chat/completions"})
    assert value.base_url == "http://localhost:8080/v1"
    with pytest.raises(ValidationError):
        CreateRunRequest(question="Una pregunta", provider="groq", model="test",
                         provider_config_id="00000000-0000-0000-0000-000000000001")
