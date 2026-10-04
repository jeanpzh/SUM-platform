"""Closed query-specific wire contracts. Raw SUM responses do not belong here."""

import json
import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .student import StudentModel

Requirement = Literal[
    "ACADEMIC_HISTORY", "STUDY_PLAN", "ACADEMIC_PROGRAMMING", "INSTITUTIONAL_RULES"
]
Intent = Literal[
    "COMPLETED_CREDITS",
    "COURSE_STATUS",
    "GRADE_QUERY",
    "CHECK_COURSE_ELIGIBILITY",
    "CHECK_PREREQUISITE_FULFILLMENT",
    "CHECK_PREREQUISITES",
    "GET_COURSE_SCHEDULE",
    "LIST_AVAILABLE_COURSES",
    "REMAINING_COURSES",
    "GENERAL_ACADEMIC_RULE",
    "CHECK_SCHEDULE_CONFLICTS",
    "CHECK_CREDIT_LOAD",
    "SIMULATE_ENROLLMENT",
    "OTHER",
]
INTENT_REQUIREMENTS = {
    "COMPLETED_CREDITS": ("ACADEMIC_HISTORY",),
    "COURSE_STATUS": ("ACADEMIC_HISTORY",),
    "GRADE_QUERY": ("ACADEMIC_HISTORY",),
    "CHECK_COURSE_ELIGIBILITY": ("ACADEMIC_HISTORY", "STUDY_PLAN", "INSTITUTIONAL_RULES"),
    "CHECK_PREREQUISITE_FULFILLMENT": ("ACADEMIC_HISTORY", "STUDY_PLAN"),
    "CHECK_PREREQUISITES": ("STUDY_PLAN",),
    "GET_COURSE_SCHEDULE": ("ACADEMIC_PROGRAMMING",),
    "LIST_AVAILABLE_COURSES": (
        "ACADEMIC_HISTORY",
        "STUDY_PLAN",
        "ACADEMIC_PROGRAMMING",
        "INSTITUTIONAL_RULES",
    ),
    "REMAINING_COURSES": ("ACADEMIC_HISTORY", "STUDY_PLAN"),
    "GENERAL_ACADEMIC_RULE": ("INSTITUTIONAL_RULES",),
    "CHECK_SCHEDULE_CONFLICTS": ("ACADEMIC_PROGRAMMING",),
    "CHECK_CREDIT_LOAD": ("STUDY_PLAN", "INSTITUTIONAL_RULES"),
    "SIMULATE_ENROLLMENT": (
        "ACADEMIC_HISTORY",
        "STUDY_PLAN",
        "ACADEMIC_PROGRAMMING",
        "INSTITUTIONAL_RULES",
    ),
    "OTHER": (),
}


class QueryInput(StudentModel):
    query: str = Field(min_length=3, max_length=2000)


class SectionSelection(StudentModel):
    courseCode: str | None = Field(default=None, min_length=1, max_length=40)
    courseName: str | None = Field(default=None, min_length=1, max_length=160)
    section: int = Field(ge=0)

    @model_validator(mode="after")
    def course_reference(self):
        if bool(self.courseCode) == bool(self.courseName):
            raise ValueError("A section requires exactly one course reference")
        return self


class SchedulePreferences(StudentModel):
    avoidDays: tuple[
        Literal["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"], ...
    ] = Field(default=(), max_length=6)
    earliestStartMinutes: int | None = Field(default=None, ge=0, le=1439)
    latestEndMinutes: int | None = Field(default=None, ge=1, le=1440)
    preferredMaxCredits: float | None = Field(default=None, gt=0, le=100)


class QueryEntities(StudentModel):
    courseCodes: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=5)
    courseNames: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=5)
    term: str | None = Field(default=None, min_length=1, max_length=40)
    sections: tuple[SectionSelection, ...] | None = Field(default=None, min_length=1, max_length=5)
    preferences: SchedulePreferences | None = None

    @model_validator(mode="after")
    def bounded_entities(self):
        for values, limit in ((self.courseCodes, 40), (self.courseNames, 160)):
            if values and any(not value.strip() or len(value) > limit for value in values):
                raise ValueError("Invalid course entity")
        return self


class AcademicQueryPlan(StudentModel):
    intent: Intent
    entities: QueryEntities
    requirements: tuple[Requirement, ...] = Field(max_length=4)

    @model_validator(mode="after")
    def closed_requirements(self):
        expected = INTENT_REQUIREMENTS[self.intent]
        if len(self.requirements) != len(expected) or set(self.requirements) != set(expected):
            raise ValueError("Requirements do not match the approved intent policy")
        needs_course = self.intent in {
            "COURSE_STATUS",
            "GRADE_QUERY",
            "CHECK_COURSE_ELIGIBILITY",
            "CHECK_PREREQUISITE_FULFILLMENT",
            "CHECK_PREREQUISITES",
            "GET_COURSE_SCHEDULE",
            "CHECK_SCHEDULE_CONFLICTS",
            "CHECK_CREDIT_LOAD",
            "SIMULATE_ENROLLMENT",
        }
        if needs_course and not self.entities.courseCodes and not self.entities.courseNames:
            raise ValueError("A course entity is required; ask for clarification")
        if self.intent == "OTHER" and self.entities.model_dump(exclude_none=True):
            raise ValueError("Clarification must not carry context selectors")
        if self.entities.preferences and self.intent != "SIMULATE_ENROLLMENT":
            raise ValueError("Preferences require a simulation plan")
        if self.entities.sections and self.intent not in {
            "GET_COURSE_SCHEDULE",
            "CHECK_SCHEDULE_CONFLICTS",
            "SIMULATE_ENROLLMENT",
        }:
            raise ValueError("Sections require a schedule query")
        if (
            len(set(self.entities.courseCodes or ())) + len(set(self.entities.courseNames or ()))
            > 5
        ):
            raise ValueError("Request at most five course references")
        for selection in self.entities.sections or ():
            if selection.courseCode and selection.courseCode not in (
                self.entities.courseCodes or ()
            ):
                raise ValueError("Section outside the requested course scope")
            if selection.courseName and selection.courseName not in (
                self.entities.courseNames or ()
            ):
                raise ValueError("Section outside the requested course scope")
        return self

    @property
    def route(self):
        return (
            "clarification"
            if self.intent == "OTHER"
            else "regulations"
            if self.intent == "GENERAL_ACADEMIC_RULE"
            else "personalized"
        )

    @property
    def academic_fields(self):
        # UI status vocabulary only. Never use this legacy vocabulary to fetch a full snapshot.
        values = []
        if "ACADEMIC_HISTORY" in self.requirements:
            values.append("course_attempts")
        if "STUDY_PLAN" in self.requirements:
            values.append("curriculum")
        if "ACADEMIC_PROGRAMMING" in self.requirements:
            values.append("academic_period")
        return tuple(values)


Status = Literal["PASSED", "FAILED", "WITHDRAWN", "UNKNOWN", "NOT_TAKEN"]


class CreditsContext(StudentModel):
    completedCredits: float | None = Field(ge=0)
    unresolvedCourses: int | None = Field(default=None, ge=0)


class CourseStatus(StudentModel):
    courseCode: str = Field(min_length=1, max_length=40)
    status: Status


class CourseGrade(CourseStatus):
    grade: float
    term: str = Field(min_length=1, max_length=40)


class HistoryStatusContext(StudentModel):
    courses: tuple[CourseStatus, ...] = Field(max_length=300)


class HistoryGradeContext(StudentModel):
    courses: tuple[CourseGrade, ...] = Field(max_length=300)


class Prerequisite(StudentModel):
    courseCode: str | None = Field(min_length=1, max_length=40)
    courseName: str | None = Field(min_length=1, max_length=160)
    group: str = Field(min_length=1, max_length=40)
    credits: float = Field(ge=0, le=1000)


class PlanCourse(StudentModel):
    courseCode: str = Field(min_length=1, max_length=40)
    courseName: str = Field(min_length=1, max_length=160)
    credits: float | None = Field(default=None, ge=0, le=100)
    type: Literal["E", "O"] | None = None
    group: str | None = Field(default=None, min_length=1, max_length=40)
    prerequisites: tuple[Prerequisite, ...] | None = Field(default=None, max_length=100)


class StudyPlanContext(StudentModel):
    courses: tuple[PlanCourse, ...] = Field(max_length=300)
    progressVerified: bool | None = None


class ScheduleSlot(StudentModel):
    day: Literal["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    room: str | None = Field(default=None, max_length=80)
    type: Literal["T", "P", "L"] | None = None


class OfferedCourse(StudentModel):
    courseCode: str = Field(min_length=1, max_length=40)
    courseName: str = Field(min_length=1, max_length=160)


class ScheduledCourse(OfferedCourse):
    section: int = Field(ge=0)
    schedule: tuple[ScheduleSlot, ...] = Field(max_length=50)


class ScheduleContext(StudentModel):
    courses: tuple[ScheduledCourse, ...] = Field(max_length=300)


class OfferingContext(StudentModel):
    courses: tuple[OfferedCourse, ...] = Field(max_length=300)


class InstitutionalChunk(StudentModel):
    citationId: UUID
    text: str = Field(min_length=1, max_length=800)


class InstitutionalContext(StudentModel):
    chunks: tuple[InstitutionalChunk, ...] = Field(max_length=3)


class AcademicQueryContext(StudentModel):
    academicHistory: CreditsContext | HistoryStatusContext | HistoryGradeContext | None = None
    studyPlan: StudyPlanContext | None = None
    academicProgramming: ScheduleContext | OfferingContext | None = None
    institutionalRules: InstitutionalContext | None = None

    @model_validator(mode="after")
    def no_placeholders(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Omit unrelated categories rather than providing null placeholders")
        return self


class PolicyScope(StudentModel):
    facultyCode: int = Field(ge=0)
    schoolCode: int = Field(ge=0)
    specialtyCode: int = Field(ge=0)
    planCode: str = Field(min_length=1, max_length=40)
    term: str = Field(min_length=1, max_length=40)


class AcademicContextEnvelope(StudentModel):
    schemaVersion: Literal["academic-context-v2"]
    source: Literal["sum", "mock"]
    snapshotId: UUID
    retrievedAt: datetime
    expiresAt: datetime
    context: AcademicQueryContext
    missingRequirements: tuple[Requirement, ...] = Field(default=(), max_length=4)
    policyScope: PolicyScope | None = None

    @model_validator(mode="after")
    def lifetime(self):
        if (
            self.retrievedAt.tzinfo is None
            or self.expiresAt.tzinfo is None
            or self.expiresAt <= self.retrievedAt
        ):
            raise ValueError("Timezone-aware ordered context lifetime required")
        return self


def canonical(value):
    return " ".join(
        "".join(c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c))
        .casefold()
        .split()
    )


def selected(course, plan):
    codes = {canonical(value) for value in plan.entities.courseCodes or ()}
    names = {canonical(value) for value in plan.entities.courseNames or ()}
    return canonical(course.courseCode) in codes | names or canonical(course.courseName) in names


def validate_context_for_plan(value, plan: AcademicQueryPlan) -> AcademicQueryContext:
    context = AcademicQueryContext.model_validate(value)
    categories = {
        "academicHistory": "ACADEMIC_HISTORY",
        "studyPlan": "STUDY_PLAN",
        "academicProgramming": "ACADEMIC_PROGRAMMING",
        "institutionalRules": "INSTITUTIONAL_RULES",
    }
    for name, category in categories.items():
        if getattr(context, name) is not None and category not in plan.requirements:
            raise ValueError("Unrequested context category")
    history = context.academicHistory
    if history:
        if (plan.intent == "COMPLETED_CREDITS") != isinstance(history, CreditsContext):
            raise ValueError("Unrequested history projection")
        if isinstance(history, HistoryGradeContext) and plan.intent != "GRADE_QUERY":
            raise ValueError("Unrequested grade fields")
    if isinstance(history, HistoryStatusContext) and len(
        {c.courseCode for c in history.courses}
    ) != len(history.courses):
        raise ValueError("Duplicate course status")
    programming = context.academicProgramming
    if programming:
        keys = [
            (c.courseCode, c.section if isinstance(programming, ScheduleContext) else None)
            for c in programming.courses
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate programming entry")
        if plan.intent in {
            "GET_COURSE_SCHEDULE",
            "CHECK_SCHEDULE_CONFLICTS",
            "SIMULATE_ENROLLMENT",
        }:
            if not isinstance(programming, ScheduleContext) or any(
                not selected(c, plan) for c in programming.courses
            ):
                raise ValueError("Unrequested programming course or fields")
        elif isinstance(programming, ScheduleContext) and programming.courses:
            raise ValueError("Unrequested schedule fields")
        if isinstance(programming, ScheduleContext):
            for course in programming.courses:
                if plan.intent in {"CHECK_SCHEDULE_CONFLICTS", "SIMULATE_ENROLLMENT"} and any(
                    {"room", "type"} & slot.model_fields_set for slot in course.schedule
                ):
                    raise ValueError("Unrequested schedule details")
                matches = [
                    s
                    for s in plan.entities.sections or ()
                    if (s.courseCode and canonical(s.courseCode) == canonical(course.courseCode))
                    or (s.courseName and canonical(s.courseName) == canonical(course.courseName))
                ]
                if matches and not any(s.section == course.section for s in matches):
                    raise ValueError("Unrequested course section")
    curriculum = context.studyPlan
    if curriculum:
        if len({c.courseCode for c in curriculum.courses}) != len(curriculum.courses):
            raise ValueError("Duplicate curriculum course")
        if plan.intent != "REMAINING_COURSES" and "progressVerified" in curriculum.model_fields_set:
            raise ValueError("Unrequested progress fields")
        for course in curriculum.courses:
            if plan.intent == "REMAINING_COURSES":
                forbidden = {"prerequisites", "group"}
            elif plan.intent == "CHECK_CREDIT_LOAD":
                forbidden = {"prerequisites", "group", "type"}
            elif plan.intent in {"SIMULATE_ENROLLMENT", "LIST_AVAILABLE_COURSES"}:
                credits_allowed = (
                    selected(course, plan)
                    if plan.intent == "SIMULATE_ENROLLMENT"
                    else bool(
                        programming
                        and any(c.courseCode == course.courseCode for c in programming.courses)
                    )
                )
                forbidden = {"type"} if credits_allowed else {"type", "credits"}
            else:
                forbidden = {"credits", "type"}
            if forbidden & course.model_fields_set:
                raise ValueError("Unrequested curriculum fields")
    if curriculum and plan.intent not in {"LIST_AVAILABLE_COURSES", "REMAINING_COURSES"}:
        targets = [course for course in curriculum.courses if selected(course, plan)]
        graph = {course.courseCode: course for course in curriculum.courses}
        allowed = {course.courseCode for course in targets}
        pending = list(allowed)
        for code in (
            pending if plan.intent not in {"CHECK_PREREQUISITES", "CHECK_CREDIT_LOAD"} else ()
        ):
            for pre in graph[code].prerequisites or ():
                if pre.courseCode in graph and pre.courseCode not in allowed:
                    allowed.add(pre.courseCode)
                    pending.append(pre.courseCode)
        if any(course.courseCode not in allowed for course in curriculum.courses):
            raise ValueError("Unrelated curriculum courses")
    if (
        history
        and hasattr(history, "courses")
        and plan.intent
        in {
            "CHECK_COURSE_ELIGIBILITY",
            "CHECK_PREREQUISITE_FULFILLMENT",
            "LIST_AVAILABLE_COURSES",
            "SIMULATE_ENROLLMENT",
        }
    ):
        related = {c.courseCode for c in curriculum.courses} if curriculum else set()
        if curriculum:
            related.update(
                p.courseCode
                for c in curriculum.courses
                for p in c.prerequisites or ()
                if p.courseCode
            )
        if any(c.courseCode not in related for c in history.courses):
            raise ValueError("Unrelated student courses")
    if (
        isinstance(history, HistoryGradeContext)
        and plan.entities.term
        and any(course.term != plan.entities.term for course in history.courses)
    ):
        raise ValueError("Unrequested grade term")
    if (
        isinstance(history, (HistoryGradeContext, HistoryStatusContext))
        and plan.intent in {"GRADE_QUERY", "COURSE_STATUS"}
        and plan.entities.courseCodes
        and any(course.courseCode not in plan.entities.courseCodes for course in history.courses)
    ):
        raise ValueError("Unrelated student course")
    if (
        len(json.dumps(context.model_dump(mode="json", exclude_unset=True), ensure_ascii=False))
        > 16000
    ):
        raise ValueError("Academic context exceeds the query budget")
    return context
