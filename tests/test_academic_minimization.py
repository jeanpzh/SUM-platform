"""Focused privacy-boundary tests: no infrastructure, provider calls or SUMAdapter."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from functools import wraps
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sum_ai.academic_planner import ContextPlanner
from sum_ai.student_context import StudentSession
from sum_contracts.academic import (
    AcademicQueryContext,
    AcademicQueryPlan,
    validate_context_for_plan,
)


def run_async(function):
    @wraps(function)
    def run():
        return asyncio.run(function())

    return run


def plan(intent, requirements, entities=None):
    return AcademicQueryPlan(intent=intent, requirements=requirements, entities=entities or {})


def test_unrequested_history_and_grade_fields_rejected():
    schedule = plan(
        "GET_COURSE_SCHEDULE",
        ("ACADEMIC_PROGRAMMING",),
        {"courseNames": ["Inteligencia Artificial"]},
    )
    with pytest.raises(ValueError):
        validate_context_for_plan({"academicHistory": {"completedCredits": 142}}, schedule)
    with pytest.raises(ValidationError):
        AcademicQueryContext.model_validate(
            {"academicHistory": {"completedCredits": 142, "token": "SECRET"}}
        )
    eligibility = plan(
        "CHECK_PREREQUISITE_FULFILLMENT",
        ("ACADEMIC_HISTORY", "STUDY_PLAN"),
        {"courseCodes": ["CO"]},
    )
    with pytest.raises(ValueError):
        validate_context_for_plan(
            {
                "academicHistory": {
                    "courses": [
                        {"courseCode": "PR", "status": "PASSED", "grade": 15, "term": "2025-2"}
                    ]
                }
            },
            eligibility,
        )


@run_async
async def test_obvious_queries_also_use_the_llm_interpretation():
    seen = []

    async def classify(value):
        seen.append(value)
        return {"intent": "OTHER", "entities": {}, "requirements": []}

    result = await ContextPlanner(classify).plan({"query": "¿Cuántos créditos he aprobado?"})
    assert result.intent == "OTHER"
    assert seen == [{"query": "¿Cuántos créditos he aprobado?"}]


@run_async
async def test_semantic_classifier_receives_only_query():
    seen = []

    async def classify(value):
        seen.append(value)
        return {
            "intent": "GET_COURSE_SCHEDULE",
            "entities": {"courseNames": ["IA"]},
            "requirements": ["ACADEMIC_PROGRAMMING"],
        }

    result = await ContextPlanner(classify).plan({"query": "Organiza mi lunes para asistir a IA"})
    assert result.intent == "GET_COURSE_SCHEDULE"
    assert seen == [{"query": "Organiza mi lunes para asistir a IA"}]
    with pytest.raises(ValidationError):
        await ContextPlanner(classify).plan({"query": "Consulta académica", "grades": [15]})


@run_async
async def test_actual_student_model_boundary_omits_session_metadata_and_caches_fetch():
    from sum_contracts.academic import AcademicContextEnvelope

    now = datetime.now(timezone.utc)
    envelope = AcademicContextEnvelope(
        schemaVersion="academic-context-v2",
        source="sum",
        snapshotId=uuid4(),
        retrievedAt=now,
        expiresAt=now + timedelta(minutes=5),
        context={"academicHistory": {"completedCredits": 142}},
    )

    class Gateway:
        count = 0

        async def collect(self, run, query_plan):
            self.count += 1
            return envelope

    class Recorder:
        events = []

        async def record(self, value):
            self.events.append(value)

    gateway, recorder = Gateway(), Recorder()
    run = SimpleNamespace(
        request=SimpleNamespace(
            question="¿Cuántos créditos he aprobado?",
            student_options=SimpleNamespace(
                use_academic_context=True, connection_id=uuid4(), course_hint="UNRELATED_HINT"
            ),
        )
    )
    query_plan = plan("COMPLETED_CREDITS", ("ACADEMIC_HISTORY",))
    session = StudentSession(run, query_plan, gateway, None, recorder)
    await session.collect()
    await session.collect()
    assert gateway.count == 1
    assert json.loads(session.answer_context([])) == {"academicHistory": {"completedCredits": 142}}
    prompt = session.model_input([])
    assert prompt == {
        "query": "¿Cuántos créditos he aprobado?",
        "context": {"academicHistory": {"completedCredits": 142}},
    }
    assert "UNRELATED_HINT" not in json.dumps(prompt)
    assert str(envelope.snapshotId) not in json.dumps(prompt)
    assert "142" not in json.dumps([e.model_dump(mode="json") for e in recorder.events])


@run_async
async def test_general_rule_never_fetches_student_context():
    class Gateway:
        async def collect(self, *_):
            pytest.fail("General regulation must not access SUM")

    class Recorder:
        async def record(self, *_):
            pass

    run = SimpleNamespace(
        request=SimpleNamespace(
            question="¿Cuál es el reglamento para retiro de curso?",
            student_options=SimpleNamespace(use_academic_context=True),
        )
    )
    session = StudentSession(
        run, plan("GENERAL_ACADEMIC_RULE", ("INSTITUTIONAL_RULES",)), Gateway(), None, Recorder()
    )
    await session.collect()
    assert json.loads(session.answer_context([])) == {"institutionalRules": {"chunks": []}}


def test_source_allowed_but_unrelated_courses_rejected():
    schedule = plan("GET_COURSE_SCHEDULE", ("ACADEMIC_PROGRAMMING",), {"courseNames": ["IA"]})
    with pytest.raises(ValueError):
        validate_context_for_plan(
            {
                "academicProgramming": {
                    "courses": [
                        {
                            "courseCode": "BD",
                            "courseName": "Base de Datos",
                            "section": 1,
                            "schedule": [],
                        }
                    ]
                }
            },
            schedule,
        )
    with pytest.raises(ValueError):
        AcademicQueryPlan(
            intent="GET_COURSE_SCHEDULE",
            entities={},
            requirements=("ACADEMIC_HISTORY", "ACADEMIC_PROGRAMMING"),
        )


def test_empty_course_selection_does_not_become_a_grade_projection():
    query_plan = plan('CHECK_PREREQUISITE_FULFILLMENT', ('ACADEMIC_HISTORY', 'STUDY_PLAN'), {'courseNames': ['Curso no encontrado']})
    context = validate_context_for_plan({'academicHistory': {'courses': []}, 'studyPlan': {'courses': []}}, query_plan)
    assert context.model_dump(mode='json', exclude_unset=True) == {'academicHistory': {'courses': []}, 'studyPlan': {'courses': []}}


def test_orchestrator_skips_rag_for_credits_and_sends_only_query_context(monkeypatch):
    from sum_ai.runner import AgentLimits, StructuredAnswer
    from sum_ai.student_runner import StudentOrchestrator
    from sum_contracts.academic import AcademicContextEnvelope
    from sum_contracts.ai import CreateRunRequest, RunContext, RunUsage

    now = datetime.now(timezone.utc)
    run = RunContext(
        run_id=uuid4(),
        owner_id="PRIVATE_OWNER",
        status="running",
        created_at=now,
        request=CreateRunRequest(
            question="¿Cuántos créditos he aprobado?",
            provider="ollama",
            model="llama3.2",
            audience="student",
            student_options={"use_academic_context": True, "connection_id": uuid4()},
        ),
    )
    envelope = AcademicContextEnvelope(
        schemaVersion="academic-context-v2",
        source="sum",
        snapshotId=uuid4(),
        retrievedAt=now,
        expiresAt=now + timedelta(minutes=5),
        context={"academicHistory": {"completedCredits": 142}},
    )
    prompts = []

    class Gateway:
        async def collect(self, *_):
            return envelope

    class Recorder:
        async def record(self, *_):
            pass

    class Retriever:
        async def retrieve(self, *_):
            pytest.fail("A pure SUM-derived credit query must not retrieve institutional RAG")

    class Model:
        async def ainvoke(self, value, **_):
            prompts.append(json.loads(value["messages"][0]["content"]))
            return {"structured_response": StructuredAnswer(answer="Has aprobado 142 créditos.")}

    monkeypatch.setattr("sum_ai.student_runner.create_agent", lambda *_, **__: Model())
    base = SimpleNamespace(
        registry=SimpleNamespace(resolve=lambda *_: "offline-model"),
        retriever=Retriever(),
        quota=None,
        limits=AgentLimits(),
    )
    orchestrator = StudentOrchestrator(base, Gateway(), None)
    query_plan = plan("COMPLETED_CREDITS", ("ACADEMIC_HISTORY",))
    session = StudentSession(run, query_plan, Gateway(), None, Recorder())
    asyncio.run(session.collect())
    result = asyncio.run(
        orchestrator._answer(
            run, Recorder(), SimpleNamespace(usage=lambda: RunUsage()), session, {}
        )
    )
    assert not result.abstained
    assert not result.citations
    assert prompts == [
        {
            "query": "¿Cuántos créditos he aprobado?",
            "context": {"academicHistory": {"completedCredits": 142}},
        }
    ]


def test_backend_permits_citation_free_sum_answers_only_with_verified_private_basis():
    from sum_backend.student_result import is_sum_projection_answer
    from sum_contracts.ai import CreateRunRequest, RunResult
    from sum_contracts.student import ContextStatus, StudentAnalysis

    request = CreateRunRequest(
        question="¿Cuántos créditos he aprobado?",
        provider="ollama",
        model="llama3.2",
        audience="student",
        student_options={"use_academic_context": True, "connection_id": uuid4()},
    )
    analysis = StudentAnalysis(
        route="personalized",
        answer_basis="sum_projection",
        context=ContextStatus(status="available", source="sum", snapshot_id=uuid4()),
    )
    result = RunResult(
        answer="Has aprobado 142 créditos.",
        provider="ollama",
        model="llama3.2",
        student_analysis=analysis,
    )
    assert is_sum_projection_answer(request, result)
    assert not is_sum_projection_answer(
        request,
        result.model_copy(
            update={
                "student_analysis": analysis.model_copy(update={"answer_basis": "published_rag"})
            }
        ),
    )
    assert not is_sum_projection_answer(
        request,
        result.model_copy(
            update={
                "student_analysis": analysis.model_copy(
                    update={"context": ContextStatus(status="unavailable")}
                )
            }
        ),
    )
    assert not is_sum_projection_answer(request.model_copy(update={"audience": "admin"}), result)
    assert not is_sum_projection_answer(
        request.model_copy(
            update={
                "student_options": request.student_options.model_copy(
                    update={"use_academic_context": False}
                )
            }
        ),
        result,
    )
