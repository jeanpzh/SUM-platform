import type {
  AcademicQueryPlan,
  HistoryDomain,
  PlanDomain,
  ProgrammingDomain,
  AcademicQueryContext,
} from './schemas'

export const canonical = (value: string) =>
  value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLocaleLowerCase('es')
export function selectCourses<
  T extends { courseCode: string; courseName: string },
>(courses: T[], plan: AcademicQueryPlan): T[] {
  const codes = new Set((plan.entities.courseCodes ?? []).map(canonical))
  const names = new Set((plan.entities.courseNames ?? []).map(canonical))
  if (!codes.size && !names.size) return []
  const selected = courses.filter(
    (course) =>
      codes.has(canonical(course.courseCode)) ||
      names.has(canonical(course.courseName)) ||
      names.has(canonical(course.courseCode)),
  )
  for (const name of names) {
    if (
      new Set(
        selected
          .filter((c) => canonical(c.courseName) === name)
          .map((c) => c.courseCode),
      ).size > 1
    )
      throw new Error('Ambiguous course name; specify its code')
  }
  return selected
}

export function prerequisiteGraph(
  courses: PlanDomain['courses'],
  targets: PlanDomain['courses'],
): PlanDomain['courses'] {
  const indexed = new Map(courses.map((course) => [course.courseCode, course]))
  const visited = new Set<string>()
  const pending = targets.map((course) => course.courseCode)
  const selected: PlanDomain['courses'] = []
  for (let i = 0; i < pending.length; i++) {
    const code = pending[i]
    if (visited.has(code)) continue
    visited.add(code)
    if (visited.size > 100)
      throw new Error('Prerequisite graph exceeds the query budget')
    const course = indexed.get(code)
    if (!course) continue // Missing definitions are retained as edges, never replaced with the full plan.
    selected.push(course)
    for (const prerequisite of course.prerequisites)
      if (prerequisite.courseCode) pending.push(prerequisite.courseCode)
  }
  return selected
}

export function courseStatus(
  history: HistoryDomain,
  courseCode: string,
  complete: boolean,
) {
  const attempts = history.courses.filter(
    (course) => course.courseCode === courseCode,
  )
  if (attempts.some((course) => course.status === 'PASSED'))
    return 'PASSED' as const
  if (!attempts.length)
    return complete ? ('NOT_TAKEN' as const) : ('UNKNOWN' as const)
  if (attempts.some((course) => course.status === 'UNKNOWN'))
    return 'UNKNOWN' as const
  if (attempts.some((course) => course.status === 'FAILED'))
    return 'FAILED' as const
  return 'WITHDRAWN' as const
}

export function completedCredits(
  history: HistoryDomain,
  complete: boolean,
): AcademicQueryContext['academicHistory'] {
  const passed = new Map<string, number>()
  for (const course of history.courses)
    if (course.status === 'PASSED') {
      const prior = passed.get(course.courseCode)
      if (prior !== undefined && prior !== course.credits)
        throw new Error('Conflicting credits for a repeated course')
      passed.set(course.courseCode, course.credits)
    }
  const unresolved = new Set(
    history.courses
      .filter((c) => c.status === 'UNKNOWN' && !passed.has(c.courseCode))
      .map((c) => c.courseCode),
  ).size
  return complete && !unresolved
    ? {
        completedCredits: Array.from(passed.values()).reduce(
          (sum, value) => sum + value,
          0,
        ),
      }
    : { completedCredits: null, unresolvedCourses: unresolved }
}

export function projectPlan(
  courses: PlanDomain['courses'],
  includeDegreeFields = false,
  creditCodes: ReadonlySet<string> = new Set(),
): NonNullable<AcademicQueryContext['studyPlan']> {
  return {
    courses: courses.map((course) =>
      includeDegreeFields
        ? {
            courseCode: course.courseCode,
            courseName: course.courseName,
            credits: course.credits,
            type: course.type,
          }
        : creditCodes.has(course.courseCode)
          ? {
              courseCode: course.courseCode,
              courseName: course.courseName,
              credits: course.credits,
              group: course.group,
              prerequisites: course.prerequisites.map((p) => ({
                courseCode: p.courseCode,
                courseName: p.courseName,
                group: p.group,
                credits: p.credits,
              })),
            }
          : {
              courseCode: course.courseCode,
              courseName: course.courseName,
              group: course.group,
              prerequisites: course.prerequisites.map((p) => ({
                courseCode: p.courseCode,
                courseName: p.courseName,
                group: p.group,
                credits: p.credits,
              })),
            },
    ),
  }
}

export function projectSchedule(
  courses: ProgrammingDomain['courses'],
  includeDetails = true,
): NonNullable<AcademicQueryContext['academicProgramming']> {
  return {
    courses: courses.map((course) => ({
      courseCode: course.courseCode,
      courseName: course.courseName,
      section: course.section,
      schedule: course.schedule.map((slot) =>
        includeDetails
          ? {
              day: slot.day,
              start: slot.start,
              end: slot.end,
              room: slot.room,
              type: slot.type,
            }
          : { day: slot.day, start: slot.start, end: slot.end },
      ),
    })),
  }
}

export function selectSections(
  courses: ProgrammingDomain['courses'],
  plan: AcademicQueryPlan,
) {
  return selectCourses(courses, plan).filter((course) => {
    const references = (plan.entities.sections ?? []).filter(
      (s) =>
        (s.courseCode &&
          canonical(s.courseCode) === canonical(course.courseCode)) ||
        (s.courseName &&
          canonical(s.courseName) === canonical(course.courseName)),
    )
    return (
      !references.length || references.some((s) => s.section === course.section)
    )
  })
}
