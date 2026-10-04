import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sum_ai.workflow import run_once
from sum_contracts.ai import CreateRunRequest, RunContext, RunResult


class Reporter:
    def __init__(self, context):
        self.context_value = context
        self.events = []

    async def context(self, run_id):
        return self.context_value

    async def record(self, event):
        self.events.append(event)


class Runner:
    async def run(self, run, reporter):
        return RunResult(answer="No hay evidencia.", provider="ollama", model="llama3.2",
                         abstained=True)


def test_workflow_reports_terminal_result_with_stable_operation_id():
    context = RunContext(run_id=uuid4(), owner_id="admin", status="queued",
                         created_at=datetime.now(timezone.utc),
                         request=CreateRunRequest(question="Una pregunta", provider="ollama", model="llama3.2"))
    reporter = Reporter(context)
    result = asyncio.run(run_once(str(context.run_id), Runner(), reporter))
    assert result == {"run_id": str(context.run_id)}
    assert [event.kind for event in reporter.events] == ["started", "completed"]
    assert reporter.events[-1].result.abstained


def test_graph_recursion_limit_is_recorded_without_workflow_retry(monkeypatch):
    import inngest
    import pytest
    from langgraph.errors import GraphRecursionError
    from sum_ai.runner import AgentLimits, AgentRunner

    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    class LoopRunner(AgentRunner):
        async def _run(self, *_):
            raise GraphRecursionError("fixture graph limit")

    context = RunContext(run_id=uuid4(), owner_id="admin", status="queued",
        created_at=datetime.now(timezone.utc),
        request=CreateRunRequest(question="Una pregunta", provider="ollama", model="fixture"))
    reporter = Reporter(context)
    runner = LoopRunner(None, object(), None, AgentLimits())
    with pytest.raises(inngest.NonRetriableError):
        asyncio.run(run_once(str(context.run_id), runner, reporter))
    assert reporter.events[-1].kind == "failed"
    assert reporter.events[-1].code == "AI_GRAPH_LIMIT"
