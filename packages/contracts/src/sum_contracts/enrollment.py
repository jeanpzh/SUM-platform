"""Reviewed pre-enrollment rules and bounded deterministic tool results."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from .student_base import StudentModel

CheckStatus = Literal["VALID", "INVALID", "UNKNOWN"]
Reason = Literal[
    "MISSING_CONTEXT",
    "MISSING_REVIEWED_POLICY",
    "UNSUPPORTED_PREREQUISITE",
    "UNKNOWN_COURSE_RESULT",
    "PREREQUISITE_NOT_PASSED",
    "COURSE_ALREADY_PASSED",
    "MISSING_COURSE",
    "MISSING_CREDITS",
    "CREDIT_LIMIT_EXCEEDED",
    "MISSING_SCHEDULE",
    "INVALID_SCHEDULE",
    "SCHEDULE_CONFLICT",
    "PREFERENCE_NOT_MET",
    "PARTIAL_SEARCH",
]


class ReviewedEnrollmentPolicy(StudentModel):
    kind: Literal["pre_enrollment"]
    rule_id: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=80)
    reviewed_by: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    applicability_verified: Literal[True]
    faculty_code: int = Field(ge=0)
    school_code: int = Field(ge=0)
    specialty_code: int = Field(ge=0)
    curriculum: str = Field(min_length=1, max_length=40)
    academic_period: str = Field(min_length=1, max_length=40)
    prerequisite_operator: Literal["ALL"]
    max_credits: float = Field(gt=0, le=100)
    citation_ids: tuple[UUID, ...] = Field(min_length=1, max_length=8)
    generation_ids: tuple[UUID, ...] = Field(min_length=1, max_length=8)


class PrerequisiteCheck(StudentModel):
    courseCode: str = Field(min_length=1, max_length=40)
    status: CheckStatus
    missingPrerequisites: tuple[str, ...] = Field(default=(), max_length=100)
    reasons: tuple[Reason, ...] = Field(default=(), max_length=16)


class SelectedSection(StudentModel):
    courseCode: str = Field(min_length=1, max_length=40)
    section: int = Field(ge=0)


class ScheduleConflict(StudentModel):
    courseA: str
    sectionA: int
    courseB: str
    sectionB: int
    day: Literal["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]
    startMinutes: int = Field(ge=0, le=1439)
    endMinutes: int = Field(ge=1, le=1440)


class EnrollmentAlternative(StudentModel):
    selections: tuple[SelectedSection, ...] = Field(min_length=1, max_length=5)
    totalCredits: float = Field(ge=0, le=500)
    idleMinutes: int = Field(ge=0)


class DeterministicResult(StudentModel):
    status: CheckStatus
    engineVersion: Literal["pre-enrollment-v1"] = "pre-enrollment-v1"
    reasons: tuple[Reason, ...] = Field(default=(), max_length=16)
    checks: tuple[PrerequisiteCheck, ...] = Field(default=(), max_length=100)
    conflicts: tuple[ScheduleConflict, ...] = Field(default=(), max_length=100)
    alternatives: tuple[EnrollmentAlternative, ...] = Field(default=(), max_length=3)
    totalCredits: float | None = Field(default=None, ge=0, le=500)
    creditLimit: float | None = Field(default=None, gt=0, le=100)
    ruleId: str | None = None
    ruleVersion: str | None = None
    citationIds: tuple[UUID, ...] = Field(default=(), max_length=8)
    examinedCombinations: int = Field(default=0, ge=0, le=64)
    truncated: bool = False
    rankingCriteria: tuple[Literal["MIN_IDLE_MINUTES", "SECTION_ORDER"], ...] = ()


class AcademicToolResult(StudentModel):
    tool: Literal[
        "validate_prerequisites",
        "detect_schedule_conflicts",
        "validate_credit_load",
        "simulate_enrollment",
        "list_available_courses",
    ]
    result: DeterministicResult
