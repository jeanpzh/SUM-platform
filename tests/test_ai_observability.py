import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sum_ai.observability import admin_trace_scope


@pytest.mark.parametrize("requested,has_key,capture", [
    (False, True, False), (True, False, False), (True, True, False), (True, True, True)])
def test_admin_trace_correlates_attempt_without_network(monkeypatch, requested, has_key, capture):
    import sum_ai.observability as module
    monkeypatch.setenv("LANGSMITH_TRACING", str(requested).lower())
    monkeypatch.setenv("LANGSMITH_API_KEY", "fixture" if has_key else "")
    monkeypatch.setenv("LANGSMITH_ADMIN_PROJECT", "admin-fixture")
    monkeypatch.setenv("LANGSMITH_ADMIN_CAPTURE_CONTENT", str(capture).lower())
    scopes, spans, clients, events = [], [], [], []

    @contextmanager
    def context(**kwargs):
        scopes.append(kwargs)
        yield

    @contextmanager
    def span(name, **kwargs):
        spans.append({"name": name, **kwargs})
        yield

    def client(content):
        clients.append(content)
        return "fake-client"

    monkeypatch.setattr(module, "tracing_context", context)
    monkeypatch.setattr(module, "trace", span)
    monkeypatch.setattr(module, "_client", client)
    run = SimpleNamespace(run_id=uuid4(), request=SimpleNamespace(
        audience="admin", provider="groq", model="openai/gpt-oss-120b", question="PRIVATE_QUERY"))

    class Recorder:
        attempt_id = "attempt-fixture"

        async def record(self, event):
            events.append(event)

    async def invoke():
        async with admin_trace_scope(run, Recorder()):
            pass

    asyncio.run(invoke())
    enabled = requested and has_key
    assert scopes[0]["enabled"] is enabled
    assert scopes[0]["metadata"]["sum_run_id"] == str(run.run_id)
    assert scopes[0]["metadata"]["attempt_id"] == "attempt-fixture"
    assert "PRIVATE_QUERY" not in str(scopes)
    payload = events[0].payload
    UUID(payload["trace_id"])
    assert payload["observability"] is enabled
    assert payload["capture_content"] is (enabled and capture)
    if enabled:
        assert clients == [capture]
        assert str(spans[0]["run_id"]) == payload["trace_id"]
        assert spans[0]["inputs"] == {}
    else:
        assert clients == spans == []


def test_student_keeps_its_existing_trace_scope(monkeypatch):
    import sum_ai.observability as module

    def unexpected(*args, **kwargs):
        pytest.fail("Admin tracing must not configure student tracing")

    monkeypatch.setattr(module, "_client", unexpected)
    monkeypatch.setattr(module, "tracing_context", unexpected)

    async def invoke():
        async with admin_trace_scope(SimpleNamespace(request=SimpleNamespace(audience="student")), None):
            pass

    asyncio.run(invoke())
