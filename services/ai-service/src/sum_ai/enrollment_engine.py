"""Pure, bounded computations over query projections; never SUM I/O or model calls."""

from decimal import Decimal
from itertools import combinations, islice, product

from sum_contracts.academic import ScheduleContext, canonical, selected
from sum_contracts.enrollment import (
    DeterministicResult,
    EnrollmentAlternative,
    PrerequisiteCheck,
    ScheduleConflict,
    SelectedSection,
)


def aggregate(statuses):
    values = tuple(statuses)
    return (
        "INVALID"
        if "INVALID" in values
        else "UNKNOWN"
        if not values or "UNKNOWN" in values
        else "VALID"
    )


class EnrollmentEngine:
    def __init__(self, plan, context, policy=None, citation_ids=None):
        self.plan, self.context, self.policy = plan, context, policy
        self.citation_ids = citation_ids

    def result(self, status, **fields):
        if self.policy:
            fields.update(
                ruleId=self.policy.rule_id,
                ruleVersion=self.policy.version,
                citationIds=self.policy.citation_ids
                if self.citation_ids is None
                else self.citation_ids,
            )
        return DeterministicResult(status=status, **fields)

    def targets(self):
        courses = self.context.studyPlan.courses if self.context.studyPlan else ()
        if self.plan.intent == "LIST_AVAILABLE_COURSES":
            offered = (
                {c.courseCode for c in self.context.academicProgramming.courses}
                if self.context.academicProgramming
                else set()
            )
            return [c for c in courses if c.courseCode in offered]
        return [c for c in courses if selected(c, self.plan)]

    def complete_targets(self, targets):
        # Every textual reference must resolve; never silently simulate a subset of requested courses.
        return bool(targets) and all(
            any(
                canonical(c.courseCode) == canonical(ref)
                or canonical(c.courseName) == canonical(ref)
                for c in targets
            )
            for ref in (
                *(self.plan.entities.courseCodes or ()),
                *(self.plan.entities.courseNames or ()),
            )
        )

    def prerequisites(self):
        if not self.policy:
            return self.result("UNKNOWN", reasons=("MISSING_REVIEWED_POLICY",))
        targets = self.targets()
        history = self.context.academicHistory
        if not self.complete_targets(targets) or not history or not hasattr(history, "courses"):
            return self.result("UNKNOWN", reasons=("MISSING_CONTEXT",))
        statuses = {c.courseCode: c.status for c in history.courses}
        checks = []
        for course in targets:
            reasons, missing = [], []
            own = statuses.get(course.courseCode, "UNKNOWN")
            if self.plan.intent != "CHECK_PREREQUISITE_FULFILLMENT":
                if own == "PASSED":
                    reasons.append("COURSE_ALREADY_PASSED")
                elif own == "UNKNOWN":
                    reasons.append("UNKNOWN_COURSE_RESULT")
            if course.prerequisites is None or course.group not in ("--", ""):
                reasons.append("UNSUPPORTED_PREREQUISITE")
            for pre in course.prerequisites or ():
                if not pre.courseCode or pre.group not in ("--", "") or pre.credits:
                    reasons.append("UNSUPPORTED_PREREQUISITE")
                    continue
                status = statuses.get(pre.courseCode, "UNKNOWN")
                if status != "PASSED":
                    missing.append(pre.courseCode)
                    reasons.append(
                        "UNKNOWN_COURSE_RESULT"
                        if status == "UNKNOWN"
                        else "PREREQUISITE_NOT_PASSED"
                    )
            reasons = tuple(dict.fromkeys(reasons))
            status = (
                "INVALID"
                if any(r in reasons for r in ("COURSE_ALREADY_PASSED", "PREREQUISITE_NOT_PASSED"))
                else "UNKNOWN"
                if reasons
                else "VALID"
            )
            checks.append(
                PrerequisiteCheck(
                    courseCode=course.courseCode,
                    status=status,
                    missingPrerequisites=tuple(missing),
                    reasons=reasons,
                )
            )
        return self.result(aggregate(c.status for c in checks), checks=tuple(checks))

    def credit_load(self, targets=None):
        targets = self.targets() if targets is None else targets
        if not self.complete_targets(targets) or any(c.credits is None for c in targets):
            return self.result("UNKNOWN", reasons=("MISSING_CREDITS",))
        total = float(sum((Decimal(str(c.credits)) for c in targets), Decimal(0)))
        if not self.policy:
            return self.result("UNKNOWN", reasons=("MISSING_REVIEWED_POLICY",), totalCredits=total)
        limit = self.policy.max_credits
        preferences = self.plan.entities.preferences
        if preferences and preferences.preferredMaxCredits:
            limit = min(limit, preferences.preferredMaxCredits)
        return self.result(
            "VALID" if total <= limit else "INVALID",
            totalCredits=total,
            creditLimit=limit,
            reasons=() if total <= limit else ("CREDIT_LIMIT_EXCEEDED",),
        )

    def schedules(self):
        programming = self.context.academicProgramming
        if not isinstance(programming, ScheduleContext):
            return []
        return list(programming.courses)

    @staticmethod
    def slots(courses):
        result = []
        for course in courses:
            if not course.schedule:
                return None
            for slot in course.schedule:
                try:
                    sh, sm = map(int, slot.start.split(":"))
                    eh, em = map(int, slot.end.split(":"))
                    start, end = sh * 60 + sm, eh * 60 + em
                    if not (
                        0 <= sh < 24
                        and 0 <= eh < 24
                        and 0 <= sm < 60
                        and 0 <= em < 60
                        and start < end
                    ):
                        return None
                except (TypeError, ValueError):
                    return None
                result.append((course, slot.day, start, end))
        return result

    def conflicts(self, courses=None):
        courses = self.schedules() if courses is None else courses
        if not self.complete_targets(courses) or len({c.courseCode for c in courses}) != len(
            courses
        ):
            return self.result("UNKNOWN", reasons=("MISSING_SCHEDULE",))
        slots = self.slots(courses)
        if slots is None:
            return self.result("UNKNOWN", reasons=("INVALID_SCHEDULE",))
        conflicts = []
        for a, b in combinations(slots, 2):
            if a[1] == b[1] and max(a[2], b[2]) < min(a[3], b[3]):
                conflicts.append(
                    ScheduleConflict(
                        courseA=a[0].courseCode,
                        sectionA=a[0].section,
                        courseB=b[0].courseCode,
                        sectionB=b[0].section,
                        day=a[1],
                        startMinutes=max(a[2], b[2]),
                        endMinutes=min(a[3], b[3]),
                    )
                )
                if len(conflicts) >= 100:
                    break
        return self.result(
            "INVALID" if conflicts else "VALID",
            conflicts=tuple(conflicts),
            reasons=("SCHEDULE_CONFLICT",) if conflicts else (),
        )

    def preferences_met(self, slots):
        preferences = self.plan.entities.preferences
        return not preferences or all(
            day not in preferences.avoidDays
            and (
                preferences.earliestStartMinutes is None
                or start >= preferences.earliestStartMinutes
            )
            and (preferences.latestEndMinutes is None or end <= preferences.latestEndMinutes)
            for _, day, start, end in slots
        )

    @staticmethod
    def idle_minutes(slots):
        total = 0
        for day in {s[1] for s in slots}:
            ordered = sorted((s[2], s[3]) for s in slots if s[1] == day)
            total += sum(max(0, b[0] - a[1]) for a, b in zip(ordered, ordered[1:]))
        return total

    def simulate(self):
        prereqs, credits = self.prerequisites(), self.credit_load()
        status = aggregate((prereqs.status, credits.status))
        if status != "VALID":
            return self.result(
                status,
                reasons=tuple(dict.fromkeys((*prereqs.reasons, *credits.reasons))),
                checks=prereqs.checks,
                totalCredits=credits.totalCredits,
                creditLimit=credits.creditLimit,
            )
        targets = self.targets()
        if len(targets) > 5:
            return self.result("UNKNOWN", reasons=("MISSING_CONTEXT",))
        schedules = self.schedules()
        options = [
            sorted((s for s in schedules if s.courseCode == t.courseCode), key=lambda s: s.section)
            for t in targets
        ]
        if any(not choices for choices in options):
            return self.result("UNKNOWN", reasons=("MISSING_SCHEDULE",))
        # Invalid/absent section data cannot justify a negative conclusion about the complete offer.
        unknown = any(self.slots((s,)) is None for s in schedules)
        possibilities = 1
        for choices in options:
            possibilities *= len(choices)
        alternatives, examined = [], 0
        for candidate in islice(product(*options), 64):
            examined += 1
            slots = self.slots(candidate)
            if (
                slots is None
                or not self.preferences_met(slots)
                or self.conflicts(candidate).status != "VALID"
            ):
                continue
            alternatives.append(
                EnrollmentAlternative(
                    selections=tuple(
                        SelectedSection(courseCode=c.courseCode, section=c.section)
                        for c in candidate
                    ),
                    totalCredits=credits.totalCredits,
                    idleMinutes=self.idle_minutes(slots),
                )
            )
        alternatives.sort(
            key=lambda a: (a.idleMinutes, tuple((s.courseCode, s.section) for s in a.selections))
        )
        truncated = possibilities > examined
        status = "VALID" if alternatives else "UNKNOWN" if unknown or truncated else "INVALID"
        reasons = (
            ("PARTIAL_SEARCH",)
            if truncated
            else ("MISSING_SCHEDULE",)
            if unknown and not alternatives
            else ("PREFERENCE_NOT_MET",)
            if not alternatives
            else ()
        )
        return self.result(
            status,
            reasons=reasons,
            checks=prereqs.checks,
            alternatives=tuple(alternatives[:3]),
            totalCredits=credits.totalCredits,
            creditLimit=credits.creditLimit,
            examinedCombinations=examined,
            truncated=truncated,
            rankingCriteria=("MIN_IDLE_MINUTES", "SECTION_ORDER"),
        )

    def available(self):
        prereqs = self.prerequisites()
        if prereqs.status == "UNKNOWN" and not prereqs.checks:
            return prereqs
        targets = {c.courseCode: c for c in self.targets()}
        checks = []
        for check in prereqs.checks:
            credits = self.credit_load([targets[check.courseCode]])
            checks.append(
                PrerequisiteCheck(
                    courseCode=check.courseCode,
                    status=aggregate((check.status, credits.status)),
                    missingPrerequisites=check.missingPrerequisites,
                    reasons=tuple(dict.fromkeys((*check.reasons, *credits.reasons))),
                )
            )
        # A list may contain valid candidates alongside unknown ones; each result stays explicit.
        return self.result(
            "VALID"
            if any(c.status == "VALID" for c in checks)
            else aggregate(c.status for c in checks),
            checks=tuple(checks),
        )
