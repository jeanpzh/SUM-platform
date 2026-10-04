import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sum_ai.tool_validation import ResearchToolValidationMiddleware
from sum_ai.tools import RESEARCH_TOOL_SCHEMAS
from sum_contracts.models import ServiceError


class Recorder:
    def __init__(self):
        self.events = []

    async def context(self):
        await asyncio.sleep(0)

    async def record(self, event):
        self.events.append(event)


def request(name, args):
    return SimpleNamespace(tool_call={"name": name, "args": args, "id": str(uuid4())})


def test_tool_schemas_publish_bounds_to_the_model():
    search = RESEARCH_TOOL_SCHEMAS["search_published_chunks"].model_json_schema()["properties"]
    context = RESEARCH_TOOL_SCHEMAS["get_published_chunk_context"].model_json_schema()["properties"]
    selection = RESEARCH_TOOL_SCHEMAS["select_answer_evidence"].model_json_schema()["properties"]
    assert search["top_k"]["minimum"] == 1 and search["top_k"]["maximum"] == 8
    assert search["query"]["minLength"] == 3 and search["query"]["maxLength"] == 500
    assert context["radius"]["minimum"] == 0 and context["radius"]["maximum"] == 2
    assert selection["chunk_ids"]["minItems"] == 1 and selection["chunk_ids"]["maxItems"] == 8


@pytest.mark.parametrize("name,args", [
    ("search_published_chunks", {"query": "La norma", "top_k": 10}),
    ("search_published_chunks", {"query": "   ", "top_k": 4}),
    ("search_published_chunks", {"query": "La norma", "top_k": True}),
    ("get_published_chunk_context", {"chunk_id": str(uuid4()), "radius": 5}),
    ("get_published_chunk_context", {"chunk_id": "inventado", "radius": 1}),
    ("select_answer_evidence", {"chunk_ids": []}),
    ("select_answer_evidence", {"chunk_ids": [str(uuid4()) for _ in range(9)]}),
    ("select_answer_evidence", {"chunk_ids": ["inventado"]}),
    ("inspect_document_relationships", {"document_ids": []}),
])
def test_invalid_inputs_are_audited_and_return_feedback_without_executing(name, args):
    recorder, trace = Recorder(), []
    middleware = ResearchToolValidationMiddleware(trace, recorder, 6)

    async def handler(_):
        raise AssertionError("Invalid arguments must never execute a tool")

    reply = asyncio.run(middleware.awrap_tool_call(request(name, args), handler))
    assert reply.status == "error" and "Correct the arguments" in reply.content
    assert len(trace) == 1 and trace[0]["code"] == "AI_TOOL_INPUT_INVALID"
    assert recorder.events[0].payload["arguments"] == args


def test_rejected_calls_share_the_tool_limit_even_in_parallel():
    recorder, trace = Recorder(), []
    middleware = ResearchToolValidationMiddleware(trace, recorder, 6)

    async def handler(_):
        raise AssertionError("No tool execution")

    async def check():
        results = await asyncio.gather(*(middleware.awrap_tool_call(
            request("select_answer_evidence", {"chunk_ids": []}), handler) for _ in range(7)),
            return_exceptions=True)
        assert sum(isinstance(result, ServiceError) and result.code == "AI_TOOL_LIMIT" for result in results) == 1

    asyncio.run(check())
    assert len(trace) == len(recorder.events) == 6
    assert len({event.operation_id for event in recorder.events}) == 6


@pytest.mark.parametrize("code", ["CORPUS_CHANGED", "AI_TOOL_SCOPE", "AI_RUN_TERMINAL", "AI_TOOL_LIMIT"])
def test_scope_cancellation_and_capacity_errors_still_halt(code):
    middleware = ResearchToolValidationMiddleware([], Recorder(), 6)

    async def handler(_):
        raise ServiceError(code, "fixture", 409)

    with pytest.raises(ServiceError) as error:
        asyncio.run(middleware.awrap_tool_call(request("search_published_chunks", {"query": "La norma"}), handler))
    assert error.value.code == code


@pytest.mark.parametrize("query", ["á" * 5000, float("nan")])
def test_invalid_argument_audit_is_json_safe_and_bounded(query):
    recorder = Recorder()
    middleware = ResearchToolValidationMiddleware([], recorder, 6)

    async def handler(_):
        raise AssertionError("No tool execution")

    asyncio.run(middleware.awrap_tool_call(request("search_published_chunks", {"query": query}), handler))
    payload = json.dumps(recorder.events[0].payload, allow_nan=False, ensure_ascii=False).encode()
    assert len(payload) < 16384
    assert recorder.events[0].payload["arguments"]["truncated"]
