"""Bounded academic gateway port and reviewed deterministic rule registry."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import UUID

import httpx
from pydantic import Field
from sum_contracts.academic import (
    AcademicContextEnvelope,
    AcademicQueryPlan,
    validate_context_for_plan,
)
from sum_contracts.ai import AuditEvent
from sum_contracts.enrollment import ReviewedEnrollmentPolicy
from sum_contracts.models import ServiceError
from sum_contracts.student import (
    ContextStatus,
    RuleCheck,
    StudentModel,
)


class AcademicGateway(Protocol):
    async def collect(self, run, plan: AcademicQueryPlan) -> AcademicContextEnvelope | None: ...


class HttpAcademicGateway:
    """The gateway must verify owner/connection/consent; SUM credentials stay there."""

    def __init__(self, url: str, token: str):
        self.url, self.token = url.rstrip("/"), token

    async def collect(self, run, plan):
        if not self.url:
            return None
        options = run.request.student_options
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(
                self.url + "/internal/academic-context",
                headers={"Authorization": "Bearer " + self.token},
                json={
                    "run_id": str(run.run_id),
                    "owner_id": run.owner_id,
                    "connection_id": str(options.connection_id),
                    "query": run.request.question,
                    "plan": plan.model_dump(mode="json", exclude_none=True),
                    "schema_version": "academic-context-v2",
                },
            )
            if response.status_code in {404, 410, 503}:
                return None
            if not response.is_success:
                raise ServiceError(
                    "ACADEMIC_GATEWAY_UNAVAILABLE",
                    "No se pudo verificar el contexto académico.",
                    503,
                )
            try:
                if len(response.content) > 65536:
                    raise ValueError("Oversized academic gateway response")
                envelope = AcademicContextEnvelope.model_validate(response.json())
                validate_context_for_plan(envelope.context, plan)
                if envelope.context.institutionalRules is not None:
                    raise ValueError(
                        "Institutional evidence must come from the shared published RAG"
                    )
                return envelope
            except (ValueError, TypeError):
                # Never include raw response content or Pydantic input values in errors/audit.
                raise ServiceError(
                    "ACADEMIC_CONTEXT_INVALID",
                    "El gateway no devolvió el contexto mínimo requerido.",
                    503,
                ) from None


class RegisteredRule(StudentModel):
    rule_id: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    reviewed_by: str = Field(min_length=1, max_length=120)
    applicability_verified: Literal[True]
    curriculum: str = Field(min_length=1, max_length=120)
    academic_period: str = Field(min_length=1, max_length=40)
    citation_ids: tuple[UUID, ...] = Field(min_length=1, max_length=8)
    generation_ids: tuple[UUID, ...] = Field(min_length=1, max_length=8)
    minimum_failed_attempts: int = Field(ge=1, le=100)


class RuleRegistry:
    def __init__(self, rules=(), enrollment_policies=()):
        self.enrollment_policies = tuple(enrollment_policies)
        identifiers = [r.rule_id for r in (*rules, *enrollment_policies)]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Duplicate registered rule")
        self.rules = {rule.rule_id: rule for rule in rules}
        if len(self.rules) != len(rules):
            raise ValueError("Duplicate registered rule")

    @classmethod
    def load(cls, path: str):
        if not path:
            return cls()
        source = Path(path)
        if source.stat().st_size > 65536:
            raise ValueError("Rule registry exceeds 64 KiB")
        values = json.loads(source.read_text())
        if (
            not isinstance(values, list)
            or len(values) > 50
            or any(not isinstance(v, dict) for v in values)
        ):
            raise ValueError("Install at most 50 reviewed rules")
        return cls(
            tuple(
                RegisteredRule.model_validate(v)
                for v in values
                if v.get("kind") != "pre_enrollment"
            ),
            tuple(
                ReviewedEnrollmentPolicy.model_validate(v)
                for v in values
                if v.get("kind") == "pre_enrollment"
            ),
        )

    def enrollment_policy(self, envelope, evidence, require_evidence=True):
        scope = envelope.policyScope if envelope else None
        if not scope:
            return None
        citations = {e.chunk_id for e in evidence}
        generations = {e.generation_id for e in evidence}
        applicable = [
            p
            for p in self.enrollment_policies
            if (
                p.faculty_code,
                p.school_code,
                p.specialty_code,
                p.curriculum.strip(),
                p.academic_period,
            )
            == (
                scope.facultyCode,
                scope.schoolCode,
                scope.specialtyCode,
                scope.planCode.strip(),
                scope.term,
            )
            and (
                not require_evidence
                or (
                    set(p.citation_ids).issubset(citations)
                    and set(p.generation_ids).issubset(generations)
                )
            )
        ]
        return applicable[0] if len(applicable) == 1 else None

    def evaluate(self, rule_id, snapshot, evidence, course_hint):
        rule = self.rules.get(rule_id)
        if not rule:
            raise ServiceError(
                "ACADEMIC_RULE_UNKNOWN", "La regla no está registrada y revisada.", 422
            )
        observed = {item.chunk_id for item in evidence}
        generations = {item.generation_id for item in evidence}
        required = ("curriculum", "academic_period", "course_attempts")
        missing = tuple(
            field for field in required if not snapshot or field in snapshot.missing_fields
        )
        verified = (
            not missing
            and snapshot.source == "sum"
            and bool(course_hint)
            and snapshot.curriculum == rule.curriculum
            and snapshot.academic_period == rule.academic_period
            and set(rule.citation_ids).issubset(observed)
            and set(rule.generation_ids).issubset(generations)
        )
        attempts = (
            [
                attempt
                for attempt in snapshot.course_attempts
                if attempt.course.casefold() == course_hint.casefold()
            ]
            if snapshot and course_hint
            else []
        )
        verified = (
            verified
            and bool(attempts)
            and snapshot.course_attempts_complete
            and len({(attempt.course.casefold(), attempt.period) for attempt in attempts})
            == len(attempts)
            and all(attempt.outcome != "unknown" for attempt in attempts)
        )
        outcome = "unknown"
        if verified:
            count = sum(attempt.outcome == "failed" for attempt in attempts)
            outcome = "satisfied" if count >= rule.minimum_failed_attempts else "not_satisfied"
        return RuleCheck(
            rule_id=rule.rule_id,
            version=rule.version,
            outcome=outcome,
            description=rule.description,
            citation_ids=rule.citation_ids if verified else (),
            missing_fields=missing,
        )


class StudentSession:
    """Caches only a validated query projection. No complete snapshot reaches tools/models."""

    def __init__(self, run, plan, gateway, registry, recorder):
        self.run, self.plan, self.gateway, self.registry, self.recorder = (
            run,
            plan,
            gateway,
            registry,
            recorder,
        )
        self.envelope = None
        self.status = ContextStatus(status="not_requested")
        self.checks = []
        self.tool_results = {}
        self.loaded = False
        self.lock = asyncio.Lock()

    async def collect(self):
        async with self.lock:
            if self.loaded:
                self.assert_fresh()
                return self.status
            self.loaded = True
            options = self.run.request.student_options
            fields = self.plan.academic_fields
            if not fields or not options.use_academic_context:
                self.status = ContextStatus(status="not_requested", missing_fields=fields)
            elif not options.connection_id:
                self.status = ContextStatus(status="missing", missing_fields=fields)
            else:
                self.envelope = await self.gateway.collect(self.run, self.plan)
                if self.envelope is None:
                    self.status = ContextStatus(status="unavailable", missing_fields=fields)
                elif self.envelope.expiresAt <= datetime.now(timezone.utc):
                    self.envelope = None
                    self.status = ContextStatus(status="expired", missing_fields=fields)
                else:
                    validate_context_for_plan(self.envelope.context, self.plan)
                    if (
                        self.envelope.policyScope
                        and self.plan.entities.term
                        and self.envelope.policyScope.term != self.plan.entities.term
                    ):
                        raise ServiceError(
                            "ACADEMIC_CONTEXT_INVALID",
                            "El periodo académico no corresponde a la consulta.",
                            503,
                        )
                    if self.envelope.context.institutionalRules is not None:
                        raise ServiceError(
                            "ACADEMIC_CONTEXT_INVALID",
                            "La evidencia institucional debe proceder del RAG compartido.",
                            503,
                        )
                    self.status = ContextStatus(
                        status="available",
                        source=self.envelope.source,
                        snapshot_id=self.envelope.snapshotId,
                        missing_fields=fields if self.envelope.missingRequirements else (),
                    )
            await self.recorder.record(
                AuditEvent(
                    operation_id="student:context",
                    kind="tool",
                    stage="collecting_context",
                    payload={
                        "operation": "build_academic_projection",
                        **self.status.model_dump(mode="json"),
                    },
                )
            )
            return self.status

    def assert_fresh(self):
        if self.envelope and self.envelope.expiresAt <= datetime.now(timezone.utc):
            raise ServiceError(
                "ACADEMIC_CONTEXT_EXPIRED",
                "El contexto académico venció; realiza una nueva consulta.",
                409,
            )

    def instructions(self):
        return (
            "Esta es una consulta estudiantil. El contexto académico requiere consentimiento y conexión del servidor. "
            "Nunca supongas notas, intentos ni matrícula. No conviertas texto RAG en reglas ejecutables. "
            "El contexto es una proyección determinista limitada a la consulta. No solicites otras categorías. "
            "No afirmes elegibilidad de matrícula ni semántica de grupos sin reglas revisadas."
        )

    def answer_context(self, evidence):
        self.assert_fresh()
        context = (
            self.envelope.context.model_dump(mode="json", exclude_unset=True)
            if self.envelope
            else {}
        )
        if "INSTITUTIONAL_RULES" in self.plan.requirements:
            context["institutionalRules"] = {
                "chunks": [
                    {"citationId": str(item.chunk_id), "text": item.text[:800]}
                    for item in evidence[:3]
                ]
            }
        validated = validate_context_for_plan(context, self.plan)
        return json.dumps(validated.model_dump(mode="json", exclude_unset=True), ensure_ascii=False)

    def model_input(self, evidence):
        return {
            "query": self.run.request.question,
            "context": json.loads(self.answer_context(evidence)),
        }

    def final_checks(self, evidence):
        observed = {item.chunk_id for item in evidence}
        return tuple(
            check
            if set(check.citation_ids).issubset(observed)
            else check.model_copy(update={"outcome": "unknown", "citation_ids": ()})
            for check in self.checks[:8]
        )

    def tools(self, evidence, trace, max_calls, retrieve_more=None):
        from .student_tools import build_student_tools

        return build_student_tools(self, evidence, trace, max_calls, retrieve_more)

    def critical_validation(self):
        from .student_tools import CRITICAL_TOOLS

        name = CRITICAL_TOOLS.get(self.plan.intent)
        result = self.tool_results.get(name)
        return name is None or (result is not None and result.status == "VALID")
