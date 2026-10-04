"""Tool allowlists/privacy only; no SUM integration or model/simulation functional tests."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sum_ai.student_context import RuleRegistry, StudentSession
from sum_contracts.academic import AcademicContextEnvelope, AcademicQueryPlan


class Recorder:
    def __init__(self):
        self.events = []

    async def record(self, value):
        self.events.append(value)


def session(intent="CHECK_COURSE_ELIGIBILITY"):
    requirements = (
        ("ACADEMIC_HISTORY", "STUDY_PLAN", "INSTITUTIONAL_RULES")
        if intent == "CHECK_COURSE_ELIGIBILITY"
        else ("ACADEMIC_PROGRAMMING",)
    )
    plan = AcademicQueryPlan(
        intent=intent, entities={"courseCodes": ["CO"]}, requirements=requirements
    )
    now = datetime.now(timezone.utc)
    context = {
        "academicHistory": {
            "courses": [
                {"courseCode": "PR", "status": "PASSED"},
                {"courseCode": "CO", "status": "NOT_TAKEN"},
            ]
        },
        "studyPlan": {
            "courses": [
                {
                    "courseCode": "CO",
                    "courseName": "Compiladores",
                    "group": "--",
                    "prerequisites": [
                        {
                            "courseCode": "PR",
                            "courseName": "Programación",
                            "group": "--",
                            "credits": 0,
                        }
                    ],
                }
            ]
        },
    }
    if intent == "GET_COURSE_SCHEDULE":
        context = {
            "academicProgramming": {
                "courses": [
                    {"courseCode": "CO", "courseName": "Compiladores", "section": 1, "schedule": []}
                ]
            }
        }
    envelope = AcademicContextEnvelope(
        schemaVersion="academic-context-v2",
        source="mock",
        snapshotId=uuid4(),
        retrievedAt=now,
        expiresAt=now + timedelta(minutes=5),
        context=context,
    )

    class Gateway:
        async def collect(self, *_):
            return envelope

    run = SimpleNamespace(
        request=SimpleNamespace(
            question="Una consulta",
            student_options=SimpleNamespace(use_academic_context=True, connection_id=uuid4()),
        )
    )
    value = StudentSession(run, plan, Gateway(), RuleRegistry(), Recorder())
    asyncio.run(value.collect())
    return value


def test_eligibility_registers_specific_tools_and_no_generic_context_dump():
    tools = session().tools([], [], 6)
    names = {tool.name for tool in tools}
    assert {
        "get_course_prerequisites",
        "validate_prerequisites",
        "get_institutional_rules",
    } <= names
    assert "request_academic_context" not in names
    assert "get_course_results" not in names
    assert "simulate_enrollment" not in names


def test_schedule_tool_cannot_accept_another_student_or_unrequested_course():
    value = session("GET_COURSE_SCHEDULE")
    tools = value.tools([], [], 6)
    assert {tool.name for tool in tools} == {"get_course_schedules"}
    with pytest.raises(ValidationError):
        asyncio.run(
            tools[0].ainvoke({"courseCode": "OTHER", "student_id": "SECRET", "token": "SECRET"})
        )


def test_missing_reviewed_policy_cannot_claim_prerequisites_verified_and_audit_has_no_values():
    value = session()
    tool = next(tool for tool in value.tools([], [], 6) if tool.name == "validate_prerequisites")
    result = json.loads(asyncio.run(tool.ainvoke({})))
    assert result["status"] == "UNKNOWN"
    assert not result["checks"] or all(check["status"] == "UNKNOWN" for check in result["checks"])
    audit = json.dumps([event.model_dump(mode="json") for event in value.recorder.events])
    assert "PASSED" not in audit
    assert "Compiladores" not in audit


def test_tool_calls_are_bounded_and_cache_does_not_fetch_more_sum():
    value = session("GET_COURSE_SCHEDULE")
    trace = []
    tool = value.tools([], trace, 2)[0]
    first = asyncio.run(tool.ainvoke({}))
    assert asyncio.run(tool.ainvoke({})) == first
    assert trace[1]["cached"] is True
    from sum_contracts.models import ServiceError

    with pytest.raises(ServiceError):
        asyncio.run(tool.ainvoke({}))
    assert len(trace) == 2


def test_tool_failures_audit_only_safe_metadata():
    value = session("CHECK_COURSE_ELIGIBILITY")

    def broken(*_):
        raise ValueError("PRIVATE_TOKEN PRIVATE_NAME")

    value.registry.enrollment_policy = broken
    tool = next(t for t in value.tools([], [], 6) if t.name == "validate_prerequisites")
    from sum_contracts.models import ServiceError

    with pytest.raises(ServiceError) as error:
        asyncio.run(tool.ainvoke({}))
    assert "PRIVATE" not in str(error.value)
    audit = json.dumps([event.model_dump(mode="json") for event in value.recorder.events])
    assert "PRIVATE" not in audit
    assert "ERROR" in audit


def test_additional_rag_is_once_bounded_and_never_changes_sum_scope():
    value = session()
    calls = []

    async def retrieve(query):
        calls.append(query)
        return [
            SimpleNamespace(chunk_id=uuid4(), text="Shared institutional rule") for _ in range(6)
        ]

    evidence, trace = [], []
    tools = value.tools(evidence, trace, 6, retrieve)
    search = next(t for t in tools if t.name == "search_institutional_rules")
    result = json.loads(asyncio.run(search.ainvoke({"search_query": "Reglas de prerrequisitos"})))
    assert len(result["institutionalRules"]["chunks"]) == 3
    assert set(result) == {"institutionalRules"}
    asyncio.run(search.ainvoke({"search_query": "Otra búsqueda"}))
    assert len(calls) == 1
    assert value.plan.requirements == ("ACADEMIC_HISTORY", "STUDY_PLAN", "INSTITUTIONAL_RULES")


def test_policy_scope_is_metadata_not_model_context():
    value = session()
    from sum_contracts.academic import PolicyScope

    value.envelope.policyScope = PolicyScope(
        facultyCode=20, schoolCode=1, specialtyCode=0, planCode="2018", term="2026-1"
    )
    model_input = value.model_input([])
    assert set(model_input) == {"query", "context"}
    assert "policyScope" not in json.dumps(model_input)
    assert "snapshotId" not in json.dumps(model_input)
