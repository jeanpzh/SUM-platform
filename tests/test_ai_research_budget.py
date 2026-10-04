import asyncio
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from sum_ai.config import ModelConfig
from sum_ai.runner import AgentLimits, BudgetMiddleware, ResearchCompletionMiddleware
from sum_ai.tools import model_evidence
from sum_contracts.models import ServiceError


class Registry:
    def config(self, *_):
        return ModelConfig(provider="ollama", model="fixture", input_usd_per_million=0,
            output_usd_per_million=0, pricing_date="2026-10-03")


class Recorder:
    def __init__(self):
        self.events = []

    async def record(self, event):
        self.events.append(event)


def budget():
    run = SimpleNamespace(model_calls=0, model_usage=SimpleNamespace(
        input_tokens=0, output_tokens=0, estimated_cost_usd=0), request=SimpleNamespace(provider="ollama", model="fixture"))
    recorder = Recorder()
    return BudgetMiddleware(run, Registry(), object(), AgentLimits(), recorder), recorder


@pytest.mark.parametrize("reason", ["input_tokens", "output_tokens", "model_calls"])
def test_research_stop_preserves_answer_reserves_without_provider_call(reason, monkeypatch):
    trace = SimpleNamespace(metadata={})
    monkeypatch.setattr("sum_ai.runner.get_current_run_tree", lambda: trace)
    shared, recorder = budget()
    if reason == "input_tokens":
        shared.input_tokens = 5000
    elif reason == "output_tokens":
        shared.output_tokens = 600
    else:
        shared.calls = 4
    request = SimpleNamespace(messages=[AIMessage(content="x" * 1200)], system_message="", tools=[])

    async def never_call(_):
        pytest.fail("Reserved answer budget must prevent a provider call")

    async def handler(value):
        return await shared.awrap_model_call(value, never_call)

    response = asyncio.run(ResearchCompletionMiddleware(shared).awrap_model_call(request, handler))
    assert response.result[0].content and not response.result[0].tool_calls
    assert not shared.researching
    assert recorder.events[-1].code == "AI_RESEARCH_BUDGET_STOP"
    assert recorder.events[-1].payload["reason"] == reason
    assert recorder.events[-1].payload["reserved_input_tokens"] == 3200
    assert recorder.events[-1].payload["reserved_output_tokens"] == 400
    assert trace.metadata["budget_stop"] == recorder.events[-1].payload


def test_global_limit_still_blocks_composition():
    shared, recorder = budget()
    shared.input_tokens = 7990
    request = SimpleNamespace(messages=[AIMessage(content="x" * 100)], system_message="", tools=[])

    async def never_call(_):
        pytest.fail("Global budget remains enforced")

    with pytest.raises(ServiceError) as error:
        asyncio.run(shared.awrap_model_call(request, never_call))
    assert error.value.code == "AI_TOKEN_LIMIT"
    assert recorder.events[-1].payload["reserved_input_tokens"] == 0


def test_tool_projection_is_bounded_and_keeps_full_internal_evidence():
    chunk = SimpleNamespace(chunk_id="chunk", document_id="document", page=2, text="á" * 10000)
    projected = json.loads(model_evidence([chunk]))[0]
    assert projected == {"chunk_id": "chunk", "document_id": "document", "page": 2,
        "text": "á" * 800, "truncated": True}
    assert len(chunk.text) == 10000
