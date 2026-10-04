"""Closed tool catalog: empty academic arguments cannot widen the original plan."""

import asyncio
import hashlib
import json
import time
from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import Field
from sum_contracts.academic import AcademicQueryContext, selected
from sum_contracts.ai import AuditEvent
from sum_contracts.models import ServiceError
from sum_contracts.student import RuleCheck, StudentModel

from .enrollment_engine import EnrollmentEngine


class QueryScopedInput(StudentModel):
    """All selectors come from the validated plan; no tool may override them."""

    # LangChain bypasses validation for schemas with no fields. Keep a constant marker.
    scope: Literal["current_query"] = "current_query"


class InstitutionalSearchInput(StudentModel):
    search_query: str = Field(min_length=3, max_length=300)


TOOL_POLICY = {
    "COMPLETED_CREDITS": ("get_completed_credits",),
    "COURSE_STATUS": ("get_course_results",),
    "GRADE_QUERY": ("get_course_results",),
    "CHECK_PREREQUISITES": ("get_course_prerequisites",),
    "CHECK_PREREQUISITE_FULFILLMENT": ("get_course_prerequisites", "validate_prerequisites"),
    "CHECK_COURSE_ELIGIBILITY": (
        "get_course_prerequisites",
        "validate_prerequisites",
        "get_institutional_rules",
        "search_institutional_rules",
    ),
    "GET_COURSE_SCHEDULE": ("get_course_schedules",),
    "CHECK_SCHEDULE_CONFLICTS": ("get_course_schedules", "detect_schedule_conflicts"),
    "CHECK_CREDIT_LOAD": (
        "validate_credit_load",
        "get_institutional_rules",
        "search_institutional_rules",
    ),
    "SIMULATE_ENROLLMENT": (
        "validate_prerequisites",
        "get_course_schedules",
        "detect_schedule_conflicts",
        "validate_credit_load",
        "simulate_enrollment",
        "get_institutional_rules",
        "search_institutional_rules",
    ),
    "LIST_AVAILABLE_COURSES": (
        "list_available_courses",
        "get_institutional_rules",
        "search_institutional_rules",
    ),
    "REMAINING_COURSES": ("list_pending_courses",),
    "GENERAL_ACADEMIC_RULE": ("get_institutional_rules", "search_institutional_rules"),
    "OTHER": (),
}
DESCRIPTIONS = {
    "get_completed_credits": "Read only the derived total of approved credits; unknown totals stay null.",
    "get_course_results": "Read only the requested course result; grades only for an explicit grade query.",
    "get_course_prerequisites": "Read definitions for requested courses only, without private history.",
    "validate_prerequisites": "Check requested courses against scoped history and a reviewed versioned policy. UNKNOWN is not approval.",
    "get_course_schedules": "Read only schedules and sections already selected by the query plan.",
    "detect_schedule_conflicts": "Compute overlap of selected sections. Missing or ambiguous sections return UNKNOWN.",
    "validate_credit_load": "Compute selected credits and compare against the reviewed limit, never a model-invented limit.",
    "simulate_enrollment": "Validate prerequisites, credits and conflicts, examine at most 64 section combinations and return at most 3 verified alternatives. No official enrollment.",
    "list_pending_courses": "Read derived pending curriculum entries with their progress verification flag.",
    "list_available_courses": "Check offered candidates deterministically; recommend only entries marked VALID. This does not validate a combined timetable.",
    "get_institutional_rules": "Read at most three already retrieved published institutional chunks.",
    "search_institutional_rules": "Perform one additional bounded search in the same pinned publications. Cannot select SUM categories or another student.",
}
CRITICAL_TOOLS = {
    "CHECK_COURSE_ELIGIBILITY": "validate_prerequisites",
    "CHECK_PREREQUISITE_FULFILLMENT": "validate_prerequisites",
    "CHECK_CREDIT_LOAD": "validate_credit_load",
    "CHECK_SCHEDULE_CONFLICTS": "detect_schedule_conflicts",
    "SIMULATE_ENROLLMENT": "simulate_enrollment",
    "LIST_AVAILABLE_COURSES": "list_available_courses",
}


def build_student_tools(session, evidence, trace, max_calls, retrieve_more=None):
    lock = asyncio.Lock()
    cache = {}
    searched = False

    async def action(name):
        await session.collect()
        context = session.envelope.context if session.envelope else AcademicQueryContext()
        needs_rules = "INSTITUTIONAL_RULES" in session.plan.requirements
        policy = session.registry.enrollment_policy(
            session.envelope, evidence, require_evidence=needs_rules
        )
        # Pure curriculum fulfillment uses reviewed server semantics, without adding normative RAG.
        engine = EnrollmentEngine(
            session.plan, context, policy, citation_ids=None if needs_rules else ()
        )
        plain = context.model_dump(mode="json", exclude_unset=True)
        fields = {
            "get_completed_credits": "academicHistory",
            "get_course_results": "academicHistory",
            "get_course_schedules": "academicProgramming",
            "list_pending_courses": "studyPlan",
        }
        if name in fields:
            return (
                {fields[name]: plain[fields[name]]}
                if fields[name] in plain
                else {"status": "UNKNOWN", "reasons": ["MISSING_CONTEXT"]}
            )
        if name == "get_course_prerequisites":
            return (
                {
                    "studyPlan": {
                        "courses": [
                            {
                                "courseCode": c.courseCode,
                                "courseName": c.courseName,
                                "group": c.group,
                                "prerequisites": [
                                    p.model_dump(mode="json") for p in c.prerequisites or ()
                                ],
                            }
                            for c in context.studyPlan.courses
                            if selected(c, session.plan)
                        ]
                    }
                }
                if context.studyPlan
                else {"status": "UNKNOWN", "reasons": ["MISSING_CONTEXT"]}
            )
        if name == "get_institutional_rules":
            return {
                "institutionalRules": {
                    "chunks": [
                        {"citationId": str(e.chunk_id), "text": e.text[:800]} for e in evidence[:3]
                    ]
                }
            }
        methods = {
            "validate_prerequisites": engine.prerequisites,
            "detect_schedule_conflicts": engine.conflicts,
            "validate_credit_load": engine.credit_load,
            "simulate_enrollment": engine.simulate,
            "list_available_courses": engine.available,
        }
        result = methods[name]()
        session.tool_results[name] = result
        if result.ruleId and result.citationIds and CRITICAL_TOOLS.get(session.plan.intent) == name:
            # Store only server-computed checks; the model cannot supply their outcome or version.
            session.checks = [c for c in session.checks if c.rule_id != result.ruleId]
            session.checks.append(
                RuleCheck(
                    rule_id=result.ruleId,
                    version=result.ruleVersion,
                    outcome={
                        "VALID": "satisfied",
                        "INVALID": "not_satisfied",
                        "UNKNOWN": "unknown",
                    }[result.status],
                    description=policy.description,
                    citation_ids=result.citationIds,
                )
            )
        return result.model_dump(mode="json", exclude_none=True)

    async def execute(name, operation):
        # LangGraph can invoke multiple tools concurrently; serialize budget reservation and cache updates.
        async with lock:
            if len(trace) >= max_calls:
                raise ServiceError("AI_TOOL_LIMIT", "Se alcanzó el límite de herramientas.", 429)
            session.assert_fresh()
            if hasattr(session.recorder, "context"):
                await session.recorder.context()
            number, started = len(trace) + 1, time.monotonic()
            item = {"tool": name, "chunk_ids": [], "cached": name in cache}
            trace.append(item)
            await session.recorder.record(
                AuditEvent(
                    operation_id=f"student:tool:{number}:start", kind="tool", payload=dict(item)
                )
            )
            try:
                result = cache[name] if name in cache else await operation()
                encoded = json.dumps(result, ensure_ascii=False)
                if len(encoded) > 16000:
                    raise ValueError("Bounded tool result exceeded")
                cache[name] = result
                item["status"] = result.get("status", "READ")
                if result.get("ruleVersion"):
                    item["rule_version"] = result["ruleVersion"]
                if result.get("engineVersion"):
                    item["engine_version"] = result["engineVersion"]
                    item["result_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
                item["result_bytes"] = len(encoded.encode())
                return encoded
            except asyncio.CancelledError:
                item["status"] = "CANCELLED"
                raise
            except Exception:
                item["status"] = "ERROR"
                # Exception strings and validation inputs may contain private values.
                raise ServiceError(
                    "ACADEMIC_TOOL_FAILED", "No se pudo verificar la operación académica.", 422
                ) from None
            finally:
                item["duration_ms"] = (time.monotonic() - started) * 1000
                await session.recorder.record(
                    AuditEvent(
                        operation_id=f"student:tool:{number}:end",
                        kind="tool",
                        payload=dict(item),
                        duration_ms=item["duration_ms"],
                    )
                )

    def scoped_tool(name):
        async def invoke(scope="current_query"):
            return await execute(name, lambda: action(name))

        return StructuredTool.from_function(
            name=name,
            description=DESCRIPTIONS[name],
            coroutine=invoke,
            args_schema=QueryScopedInput,
        )

    async def search(search_query):
        async def retrieve():
            nonlocal searched
            if searched or retrieve_more is None:
                raise ServiceError(
                    "AI_RETRIEVAL_LIMIT", "La recuperación adicional no está disponible.", 429
                )
            searched = True
            items = await retrieve_more(search_query)
            # Replace with a bounded union, prioritizing the additional relevant chunks.
            merged = {item.chunk_id: item for item in (*items[:3], *evidence)}
            evidence[:] = list(merged.values())[:3]
            # New evidence can establish a reviewed rule; discard prior UNKNOWN computations.
            cache.clear()
            session.tool_results.clear()
            session.checks.clear()
            return await action("get_institutional_rules")

        return await execute("search_institutional_rules", retrieve)

    return [
        StructuredTool.from_function(
            name=name,
            description=DESCRIPTIONS[name],
            coroutine=search,
            args_schema=InstitutionalSearchInput,
        )
        if name == "search_institutional_rules"
        else scoped_tool(name)
        for name in TOOL_POLICY[session.plan.intent]
        if name != "search_institutional_rules" or retrieve_more is not None
    ]
