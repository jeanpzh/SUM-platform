"""Student domain contracts, independent of the future SUM response schema."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .enrollment import AcademicToolResult
from .student_base import StudentModel

AcademicField = Literal["curriculum", "course_attempts", "enrollment", "academic_period"]


class StudentOptions(StudentModel):
    use_academic_context: bool = False
    connection_id: UUID | None = None
    course_hint: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def consent(self):
        if self.connection_id and not self.use_academic_context:
            raise ValueError("Academic connection requires explicit consent")
        return self


class StudentConsultation(StudentModel):
    question: str = Field(min_length=3, max_length=2000)
    options: StudentOptions = Field(default_factory=StudentOptions)


class ConsultationPlan(StudentModel):
    route: Literal["regulations", "personalized", "clarification"]
    retrieval_query: str = Field(min_length=3, max_length=500)
    academic_fields: tuple[AcademicField, ...] = Field(default=(), max_length=4)
    clarification: str | None = Field(default=None, max_length=500)


class CourseAttempt(StudentModel):
    course: str = Field(min_length=1, max_length=120)
    period: str = Field(max_length=40)
    outcome: Literal["passed", "failed", "withdrawn", "unknown"]


class AcademicSnapshot(StudentModel):
    snapshot_id: UUID
    source: Literal["sum", "mock"]
    retrieved_at: datetime
    expires_at: datetime
    curriculum: str | None = Field(default=None, max_length=120)
    academic_period: str | None = Field(default=None, max_length=40)
    enrollment: Literal["active", "inactive", "unknown"] = "unknown"
    course_attempts: tuple[CourseAttempt, ...] = Field(default=(), max_length=100)
    course_attempts_complete: bool = False
    missing_fields: tuple[AcademicField, ...] = Field(default=(), max_length=4)

    @model_validator(mode="after")
    def valid_lifetime(self):
        if (
            self.retrieved_at.tzinfo is None
            or self.expires_at.tzinfo is None
            or self.expires_at <= self.retrieved_at
        ):
            raise ValueError("Snapshot requires timezone-aware retrieval and expiration in order")
        return self


class ContextStatus(StudentModel):
    status: Literal["not_requested", "available", "missing", "expired", "unavailable"]
    source: Literal["sum", "mock"] | None = None
    snapshot_id: UUID | None = None
    missing_fields: tuple[AcademicField, ...] = Field(default=(), max_length=4)


class RuleCheck(StudentModel):
    rule_id: str = Field(max_length=100)
    version: str = Field(max_length=80)
    outcome: Literal["satisfied", "not_satisfied", "unknown"]
    description: str = Field(max_length=500)
    citation_ids: tuple[UUID, ...] = Field(default=(), max_length=8)
    missing_fields: tuple[AcademicField, ...] = Field(default=(), max_length=4)


class StudentAnalysis(StudentModel):
    route: Literal["regulations", "personalized", "clarification"]
    answer_basis: Literal["published_rag", "sum_projection", "clarification"] = "published_rag"
    context: ContextStatus
    checks: tuple[RuleCheck, ...] = Field(default=(), max_length=8)
    deterministic_results: tuple[AcademicToolResult, ...] = Field(default=(), max_length=6)
    # Closed component vocabulary: future MCP tools must return this same schema.
    components: tuple[Literal["sources", "context_status", "rule_checks", "next_steps"], ...] = (
        Field(default=("sources", "context_status", "next_steps"), max_length=4)
    )
    next_steps: tuple[str, ...] = Field(default=(), max_length=5)
    trace_id: UUID | None = None
