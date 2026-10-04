import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sum_ai.retrieval import RetrievalBatch
from sum_ai.runner import AgentLimits, AgentRunner, StructuredAnswer, validate_answer
from sum_contracts.ai import CreateRunRequest, Evidence, RunContext


def run():
    return RunContext(run_id=uuid4(), owner_id="admin", status="queued",
                      created_at=datetime.now(timezone.utc),
                      request=CreateRunRequest(question="¿Cuál es la norma?", provider="ollama", model="llama3.2"))


def evidence():
    return Evidence(chunk_id=uuid4(), document_id=uuid4(), version_id=uuid4(),
                    generation_id=uuid4(), page=1, locator="p. 1", text="Norma publicada", rank=1)


def test_invalid_citation_abstains():
    source = evidence()
    valid = validate_answer(StructuredAnswer(answer="Según la norma.", citation_ids=(source.chunk_id,)), [source], "ollama", "llama3.2")
    assert not valid.abstained and len(valid.citations) == 1
    invalid = validate_answer(StructuredAnswer(answer="Una afirmación.", citation_ids=(uuid4(),)), [source], "ollama", "llama3.2")
    assert invalid.abstained and not invalid.citations


def test_no_evidence_skips_model():
    class Retriever:
        async def retrieve(self, *args):
            return RetrievalBatch((), {})

        def pin(self, *args):
            pass

    class Registry:
        def resolve(self, *args):
            raise AssertionError("No model call expected")

    class Quota:
        async def admit_request(self, actor):
            pass

    class Recorder:
        def __init__(self):
            self.events = []

        async def record(self, event):
            self.events.append(event)

    recorder = Recorder()
    result = asyncio.run(AgentRunner(Registry(), Retriever(), Quota(), AgentLimits()).run(run(), recorder))
    assert result.abstained
    assert any(event.kind == "stage" for event in recorder.events)


def test_limits_are_bounded():
    with pytest.raises(ValueError):
        AgentLimits(max_model_calls=100)


@pytest.mark.parametrize("invalid_tool", [None, "search", "context", "selection", "research_limit", "budget_stop"])
def test_real_langchain_agents_choose_tool_and_validate_answer(invalid_tool):
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from sum_ai.config import ModelConfig
    from sum_ai.quota import Reservation

    source = evidence()

    class ScriptedModel(BaseChatModel):
        replies: list

        @property
        def _llm_type(self):
            return "test-scripted"

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(generations=[ChatGeneration(message=self.replies.pop(0))])

    replies = [
        AIMessage(content="", tool_calls=[{"name": "search_published_chunks", "args": {"query": "La norma", "top_k": 4}, "id": "search-1", "type": "tool_call"}]),
        AIMessage(content="Evidencia suficiente."),
        AIMessage(content="", tool_calls=[{"name": "StructuredAnswer", "args": {"answer": "Según la norma publicada.", "citation_ids": [str(source.chunk_id)]}, "id": "answer-1", "type": "tool_call"}]),
    ]
    invalid = {
        "search": ("search_published_chunks", {"query": "La norma", "top_k": 10}),
        "context": ("get_published_chunk_context", {"chunk_id": str(source.chunk_id), "radius": 3}),
        "selection": ("select_answer_evidence", {"chunk_ids": [str(source.chunk_id)] * 2}),
    }
    if invalid_tool == "budget_stop":
        replies = [AIMessage(content="", tool_calls=[{"name": "search_published_chunks",
            "args": {"query": "La norma", "top_k": 4}, "id": f"search-{number}", "type": "tool_call"}],
            usage_metadata={"input_tokens": tokens, "output_tokens": 100, "total_tokens": tokens + 100})
            for number, tokens in enumerate((2000, 2500))] + [replies[-1]]
    elif invalid_tool == "research_limit":
        replies = [AIMessage(content="", tool_calls=[{"name": "search_published_chunks",
            "args": {"query": "La norma", "top_k": 4}, "id": f"search-{number}", "type": "tool_call"}])
            for number in range(3)] + [replies[-1]]
    elif invalid_tool:
        name, args = invalid[invalid_tool]
        replies.insert(0, AIMessage(content="", tool_calls=[{"name": name, "args": args,
            "id": "invalid-1", "type": "tool_call"}]))
    model = ScriptedModel(replies=replies)

    class Registry:
        def resolve(self, *_args):
            return model

        def config(self, *_args):
            return ModelConfig(provider="ollama", model="llama3.2", input_usd_per_million=0,
                               output_usd_per_million=0, pricing_date="2026-10-03")

    class Retriever:
        async def retrieve(self, *args):
            return RetrievalBatch((source,), {str(source.document_id): str(source.generation_id)})

        async def more(self, *args):
            return RetrievalBatch((source,), {str(source.document_id): str(source.generation_id)})

        def pin(self, *args):
            pass

        async def assert_current(self, *_args):
            pass

        def unpin(self, *_args):
            pass

    class Quota:
        def __init__(self):
            self.calls = 0

        async def admit_request(self, *_args):
            pass

        async def reserve(self, *_args):
            self.calls += 1
            return Reservation(str(uuid4()), "actor", "provider", 100, 999999)

        async def settle(self, *_args):
            pass

        async def release(self, *_args):
            pass

    class Recorder:
        def __init__(self):
            self.events = []

        async def record(self, event):
            self.events.append(event)

    recorder, quota = Recorder(), Quota()
    result = asyncio.run(AgentRunner(Registry(), Retriever(), quota, AgentLimits()).run(run(), recorder))
    assert not result.abstained
    assert quota.calls == (4 if invalid_tool in invalid or invalid_tool == "research_limit" else 3)
    assert result.tool_trace[-1]["tool"] == "search_published_chunks"
    assert any(event.kind == "tool" for event in recorder.events)
    if invalid_tool in invalid:
        rejection = next(event for event in recorder.events if event.code == "AI_TOOL_INPUT_INVALID")
        assert rejection.payload["arguments"] == invalid[invalid_tool][1]
        assert result.tool_trace[0]["code"] == "AI_TOOL_INPUT_INVALID"
    if invalid_tool == "budget_stop":
        stop = next(event for event in recorder.events if event.code == "AI_RESEARCH_BUDGET_STOP")
        assert stop.payload["consumed_input_tokens"] == 4500
        assert stop.payload["reserved_input_tokens"] == 3200
        assert len(result.tool_trace) == 2
        assert result.usage.input_tokens < 8000
    assert all(stage in result.timings for stage in ("retrieving", "researching", "composing", "verifying"))


def test_research_selection_can_replace_full_initial_context():
    from sum_ai.runner import select_answer_evidence
    initial = [evidence() for _ in range(8)]
    added = evidence()
    trace = [{"tool": "search_published_chunks", "chunk_ids": [str(added.chunk_id)]}]
    selected = select_answer_evidence(initial + [added], trace, 8)
    assert added in selected and len(selected) == 8
    trace.append({"tool": "select_answer_evidence", "chunk_ids": [str(added.chunk_id)]})
    assert select_answer_evidence(initial + [added], trace, 8) == [added]


def test_retry_cost_equals_durable_usage_cost():
    from types import SimpleNamespace

    from langchain_core.messages import AIMessage
    from sum_ai.config import ModelConfig
    from sum_ai.quota import Reservation
    from sum_ai.runner import BudgetMiddleware
    class Registry:
        def config(self, *_):
            return ModelConfig(provider="ollama", model="llama3.2", input_usd_per_million=2,
                output_usd_per_million=3, pricing_date="2026-10-03")
    class Quota:
        async def reserve(self, *_):
            return Reservation(str(uuid4()), "actor", "provider", 100, 99999)
        async def settle(self, *_):
            pass
    class Recorder:
        events = []
        async def record(self, event):
            self.events.append(event)
    recorder = Recorder()
    budget = BudgetMiddleware(run(), Registry(), Quota(), AgentLimits(), recorder)
    request = SimpleNamespace(messages=[AIMessage(content="question")], system_message="system", tools=[], model_settings={})
    request.override = lambda **_: request
    attempts = 0
    async def handler(_):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError()
        return SimpleNamespace(result=[AIMessage(content="ok", usage_metadata={"input_tokens": 5, "output_tokens": 2, "total_tokens": 7})])
    asyncio.run(budget.awrap_model_call(request, handler))
    assert budget.usage().estimated_cost_usd == pytest.approx(sum(e.payload["estimated_cost_usd"] for e in recorder.events if e.kind == "usage"))


def test_initial_evidence_is_audited_before_provider_failure():
    from sum_contracts.models import EmbeddingProfile, ServiceError
    source = evidence()
    profile = EmbeddingProfile("fixture", "v1", 768)
    class Retriever:
        async def retrieve(self, *_):
            return RetrievalBatch((source,), {str(source.document_id): str(source.generation_id)}, (profile,))
        def pin(self, *_):
            pass
    class Registry:
        def resolve(self, *_):
            raise ServiceError("AI_PROVIDER_UNAVAILABLE", "fixture", 503)
    class Recorder:
        events = []
        async def record(self, event):
            self.events.append(event)
    recorder = Recorder()
    with pytest.raises(ServiceError):
        asyncio.run(AgentRunner(Registry(), Retriever(), object(), AgentLimits()).run(run(), recorder))
    proof = next(e for e in recorder.events if e.kind == "evidence")
    assert proof.payload["evidence"][0]["chunk_id"] == str(source.chunk_id)
    assert proof.payload["generation_ids"] == [str(source.generation_id)]
    assert proof.payload["profiles"] == [profile.to_dict()]


def test_model_call_limit_survives_another_workflow_attempt():
    from types import SimpleNamespace

    from langchain_core.messages import AIMessage
    from sum_ai.config import ModelConfig
    from sum_ai.runner import BudgetMiddleware
    from sum_contracts.models import ServiceError
    class Registry:
        def config(self, *_):
            return ModelConfig(provider="ollama", model="llama3.2", input_usd_per_million=0,
                output_usd_per_million=0, pricing_date="2026-10-03")
    context = run().model_copy(update={"model_calls": 5})
    budget = BudgetMiddleware(context, Registry(), object(), AgentLimits(), object())
    request = SimpleNamespace(messages=[AIMessage(content="Pregunta")], system_message="", tools=[])
    async def handler(_):
        raise AssertionError("No sixth model call")
    with pytest.raises(ServiceError) as error:
        asyncio.run(budget.awrap_model_call(request, handler))
    assert error.value.code == "AI_MODEL_LIMIT"
