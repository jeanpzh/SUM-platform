import { z } from 'zod'
import { contextRequirements, intentRequirements } from './context-requirement'
import { selectCourses, canonical } from './projections'

const text = z.string().trim().min(1).max(160)
const code = z.string().trim().min(1).max(40)
const status = z.enum(['PASSED', 'FAILED', 'WITHDRAWN', 'UNKNOWN', 'NOT_TAKEN'])
export const plannerInputSchema = z.strictObject({
  query: z.string().trim().min(3).max(2000),
})
const sectionSelectionSchema = z
  .strictObject({
    courseCode: code.optional(),
    courseName: text.optional(),
    section: z.number().int().nonnegative(),
  })
  .refine(
    (s) => Boolean(s.courseCode) !== Boolean(s.courseName),
    'Exactly one course reference is required',
  )
export const policyScopeSchema = z.strictObject({
  facultyCode: z.number().int().nonnegative(),
  schoolCode: z.number().int().nonnegative(),
  specialtyCode: z.number().int().nonnegative(),
  planCode: code,
  term: code,
})
export const academicQueryPlanSchema = z
  .strictObject({
    intent: z.enum(
      Object.keys(intentRequirements) as [
        keyof typeof intentRequirements,
        ...Array<keyof typeof intentRequirements>,
      ],
    ),
    entities: z.strictObject({
      courseCodes: z.array(code).min(1).max(5).optional(),
      courseNames: z.array(text).min(1).max(5).optional(),
      term: code.optional(),
      sections: z.array(sectionSelectionSchema).min(1).max(5).optional(),
      preferences: z
        .strictObject({
          avoidDays: z
            .array(
              z.enum([
                'LUNES',
                'MARTES',
                'MIERCOLES',
                'JUEVES',
                'VIERNES',
                'SABADO',
              ]),
            )
            .max(6)
            .default([]),
          earliestStartMinutes: z.number().int().min(0).max(1439).optional(),
          latestEndMinutes: z.number().int().min(1).max(1440).optional(),
          preferredMaxCredits: z.number().positive().max(100).optional(),
        })
        .optional(),
    }),
    requirements: z.array(z.enum(contextRequirements)).max(4),
  })
  .superRefine((plan, ctx) => {
    const expected = intentRequirements[plan.intent]
    if (
      plan.requirements.length !== expected.length ||
      new Set(plan.requirements).size !== expected.length ||
      expected.some((item) => !plan.requirements.includes(item))
    ) {
      ctx.addIssue({
        code: 'custom',
        message: 'Requirements do not match the approved intent policy',
      })
    }
    const needsCourse = [
      'COURSE_STATUS',
      'GRADE_QUERY',
      'CHECK_COURSE_ELIGIBILITY',
      'CHECK_PREREQUISITE_FULFILLMENT',
      'CHECK_PREREQUISITES',
      'GET_COURSE_SCHEDULE',
      'CHECK_SCHEDULE_CONFLICTS',
      'CHECK_CREDIT_LOAD',
      'SIMULATE_ENROLLMENT',
    ].includes(plan.intent)
    if (
      needsCourse &&
      !plan.entities.courseCodes?.length &&
      !plan.entities.courseNames?.length
    )
      ctx.addIssue({
        code: 'custom',
        message: 'A course entity is required; ask for clarification',
      })
    if (plan.entities.preferences && plan.intent !== 'SIMULATE_ENROLLMENT')
      ctx.addIssue({
        code: 'custom',
        message: 'Preferences require simulation',
      })
    if (
      plan.entities.sections &&
      ![
        'GET_COURSE_SCHEDULE',
        'CHECK_SCHEDULE_CONFLICTS',
        'SIMULATE_ENROLLMENT',
      ].includes(plan.intent)
    )
      ctx.addIssue({
        code: 'custom',
        message: 'Sections require a schedule query',
      })
    if (
      new Set(plan.entities.courseCodes ?? []).size +
        new Set(plan.entities.courseNames ?? []).size >
      5
    )
      ctx.addIssue({
        code: 'custom',
        message: 'Request at most five course references',
      })
    for (const selection of plan.entities.sections ?? [])
      if (
        (selection.courseCode &&
          !plan.entities.courseCodes?.includes(selection.courseCode)) ||
        (selection.courseName &&
          !plan.entities.courseNames?.includes(selection.courseName))
      )
        ctx.addIssue({
          code: 'custom',
          message: 'Section outside course scope',
        })
    if (plan.intent === 'OTHER' && Object.keys(plan.entities).length)
      ctx.addIssue({
        code: 'custom',
        message: 'Clarification must not carry context selectors',
      })
  })
export type AcademicQueryPlan = z.infer<typeof academicQueryPlanSchema>

export const historyDomainSchema = z.strictObject({
  courses: z
    .array(
      z.strictObject({
        courseCode: code,
        courseName: text,
        credits: z.number().nonnegative().max(100),
        grade: z.number().finite(),
        term: code,
        status: status.exclude(['NOT_TAKEN']),
      }),
    )
    .max(5000),
})
const prerequisiteSchema = z.strictObject({
  courseCode: code.nullable(),
  courseName: text.nullable(),
  group: code,
  credits: z.number().nonnegative().max(1000),
})
export const planCourseSchema = z.strictObject({
  courseCode: code,
  courseName: text,
  credits: z.number().nonnegative().max(100),
  type: z.enum(['E', 'O']),
  group: code,
  prerequisites: z.array(prerequisiteSchema).max(100),
})
export const planDomainSchema = z.strictObject({
  courses: z.array(planCourseSchema).max(2000),
})
const slotSchema = z.strictObject({
  day: z.enum(['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO']),
  start: z.string().regex(/^\d{2}:\d{2}$/),
  end: z.string().regex(/^\d{2}:\d{2}$/),
  room: z.string().trim().max(80),
  type: z.enum(['T', 'P', 'L']),
})
export const programmingDomainSchema = z.strictObject({
  courses: z
    .array(
      z.strictObject({
        courseCode: code,
        courseName: text,
        section: z.number().int().nonnegative(),
        schedule: z.array(slotSchema).max(50),
      }),
    )
    .max(5000),
})
const contextSlotSchema = z.strictObject({
  day: slotSchema.shape.day,
  start: slotSchema.shape.start,
  end: slotSchema.shape.end,
  room: slotSchema.shape.room.optional(),
  type: slotSchema.shape.type.optional(),
})
const scheduledContextCourseSchema = z.strictObject({
  courseCode: code,
  courseName: text,
  section: z.number().int().nonnegative(),
  schedule: z.array(contextSlotSchema).max(50),
})
const courseStatusSchema = z.strictObject({ courseCode: code, status })
const gradeSchema = z.strictObject({
  courseCode: code,
  status,
  grade: z.number().finite(),
  term: code,
})
export const academicHistoryContextSchema = z.union([
  z.strictObject({
    completedCredits: z.number().nonnegative().nullable(),
    unresolvedCourses: z.number().int().nonnegative().optional(),
  }),
  z.strictObject({ courses: z.array(courseStatusSchema).max(300) }),
  z.strictObject({ courses: z.array(gradeSchema).max(300) }),
])
export const studyPlanContextSchema = z.strictObject({
  progressVerified: z.boolean().optional(),
  courses: z
    .array(
      z.strictObject({
        courseCode: code,
        courseName: text,
        credits: z.number().nonnegative().max(100).optional(),
        type: z.enum(['E', 'O']).optional(),
        group: code.optional(),
        prerequisites: z.array(prerequisiteSchema).max(100).optional(),
      }),
    )
    .max(300),
})
export const academicProgrammingContextSchema = z.union([
  z.strictObject({
    courses: z.array(scheduledContextCourseSchema).max(300),
  }),
  z.strictObject({
    courses: z
      .array(z.strictObject({ courseCode: code, courseName: text }))
      .max(300),
  }),
])
export const institutionalRulesContextSchema = z.strictObject({
  chunks: z
    .array(
      z.strictObject({
        citationId: z.uuid(),
        text: z.string().min(1).max(800),
      }),
    )
    .max(3),
})
export const academicQueryContextSchema = z.strictObject({
  academicHistory: academicHistoryContextSchema.optional(),
  studyPlan: studyPlanContextSchema.optional(),
  academicProgramming: academicProgrammingContextSchema.optional(),
  institutionalRules: institutionalRulesContextSchema.optional(),
})
export type AcademicQueryContext = z.infer<typeof academicQueryContextSchema>
export type HistoryDomain = z.infer<typeof historyDomainSchema>
export type PlanDomain = z.infer<typeof planDomainSchema>
export type ProgrammingDomain = z.infer<typeof programmingDomainSchema>

export function validateContextForPlan(
  value: unknown,
  input: AcademicQueryPlan,
): AcademicQueryContext {
  const plan = academicQueryPlanSchema.parse(input)
  const context = academicQueryContextSchema.parse(value)
  const categories = {
    academicHistory: 'ACADEMIC_HISTORY',
    studyPlan: 'STUDY_PLAN',
    academicProgramming: 'ACADEMIC_PROGRAMMING',
    institutionalRules: 'INSTITUTIONAL_RULES',
  } as const
  for (const key of Object.keys(context) as Array<keyof typeof categories>) {
    if (!plan.requirements.includes(categories[key]))
      throw new Error('Unrequested context category')
  }
  const history = context.academicHistory
  if (history) {
    if (
      plan.intent === 'COMPLETED_CREDITS'
        ? !('completedCredits' in history)
        : !('courses' in history)
    )
      throw new Error('Unrequested history projection')
    if (
      'courses' in history &&
      plan.intent !== 'GRADE_QUERY' &&
      history.courses.some((c) => 'grade' in c || 'term' in c)
    )
      throw new Error('Unrequested grade fields')
  }
  if (
    history &&
    'courses' in history &&
    plan.intent !== 'GRADE_QUERY' &&
    new Set(history.courses.map((c) => c.courseCode)).size !==
      history.courses.length
  )
    throw new Error('Duplicate course status')
  if (context.academicProgramming) {
    const keys = context.academicProgramming.courses.map((c) =>
      JSON.stringify([c.courseCode, 'section' in c ? c.section : null]),
    )
    if (new Set(keys).size !== keys.length)
      throw new Error('Duplicate programming entry')
    if (
      [
        'GET_COURSE_SCHEDULE',
        'CHECK_SCHEDULE_CONFLICTS',
        'SIMULATE_ENROLLMENT',
      ].includes(plan.intent) &&
      selectCourses(context.academicProgramming.courses, plan).length !==
        context.academicProgramming.courses.length
    )
      throw new Error('Unrelated programming courses')
    for (const course of context.academicProgramming.courses) {
      if ('section' in course) {
        if (
          ['CHECK_SCHEDULE_CONFLICTS', 'SIMULATE_ENROLLMENT'].includes(
            plan.intent,
          ) &&
          course.schedule.some((s) => 'room' in s || 'type' in s)
        )
          throw new Error('Unrequested schedule details')
        const selections = (plan.entities.sections ?? []).filter(
          (s) =>
            (s.courseCode &&
              canonical(s.courseCode) === canonical(course.courseCode)) ||
            (s.courseName &&
              canonical(s.courseName) === canonical(course.courseName)),
        )
        if (
          selections.length &&
          !selections.some((s) => s.section === course.section)
        )
          throw new Error('Unrequested course section')
      }
      if (
        ![
          'GET_COURSE_SCHEDULE',
          'CHECK_SCHEDULE_CONFLICTS',
          'SIMULATE_ENROLLMENT',
        ].includes(plan.intent) &&
        ('schedule' in course || 'section' in course)
      )
        throw new Error('Unrequested schedule fields')
    }
  }
  if (context.studyPlan) {
    if (
      new Set(context.studyPlan.courses.map((c) => c.courseCode)).size !==
      context.studyPlan.courses.length
    )
      throw new Error('Duplicate curriculum course')
    if (
      plan.intent !== 'REMAINING_COURSES' &&
      'progressVerified' in context.studyPlan
    )
      throw new Error('Unrequested progress fields')
    if (
      plan.intent !== 'REMAINING_COURSES' &&
      plan.intent !== 'LIST_AVAILABLE_COURSES'
    ) {
      const courses = context.studyPlan.courses
      const allowed = new Set(
        selectCourses(courses, plan).map((course) => course.courseCode),
      )
      if (!['CHECK_PREREQUISITES', 'CHECK_CREDIT_LOAD'].includes(plan.intent)) {
        const pending = Array.from(allowed)
        const indexed = new Map(
          courses.map((course) => [course.courseCode, course]),
        )
        for (const code of pending)
          for (const pre of indexed.get(code)?.prerequisites ?? []) {
            if (
              pre.courseCode &&
              indexed.has(pre.courseCode) &&
              !allowed.has(pre.courseCode)
            ) {
              allowed.add(pre.courseCode)
              pending.push(pre.courseCode)
            }
          }
      }
      if (courses.some((course) => !allowed.has(course.courseCode)))
        throw new Error('Unrelated curriculum courses')
    }
    for (const course of context.studyPlan.courses) {
      const creditsAllowed =
        plan.intent === 'REMAINING_COURSES' ||
        plan.intent === 'CHECK_CREDIT_LOAD' ||
        (plan.intent === 'SIMULATE_ENROLLMENT' &&
          selectCourses([course], plan).length > 0) ||
        (plan.intent === 'LIST_AVAILABLE_COURSES' &&
          context.academicProgramming?.courses.some(
            (c) => c.courseCode === course.courseCode,
          ))
      if (
        (!creditsAllowed && 'credits' in course) ||
        (plan.intent !== 'REMAINING_COURSES' && 'type' in course) ||
        (['REMAINING_COURSES', 'CHECK_CREDIT_LOAD'].includes(plan.intent) &&
          ('prerequisites' in course || 'group' in course))
      )
        throw new Error('Unrequested curriculum fields')
    }
  }

  if (history && 'courses' in history) {
    if (
      [
        'CHECK_COURSE_ELIGIBILITY',
        'CHECK_PREREQUISITE_FULFILLMENT',
        'LIST_AVAILABLE_COURSES',
        'SIMULATE_ENROLLMENT',
      ].includes(plan.intent)
    ) {
      const courses = context.studyPlan?.courses ?? []
      const related = new Set(
        courses.flatMap((course) => [
          course.courseCode,
          ...(course.prerequisites ?? []).flatMap((pre) =>
            pre.courseCode ? [pre.courseCode] : [],
          ),
        ]),
      )
      if (history.courses.some((course) => !related.has(course.courseCode)))
        throw new Error('Unrelated student courses')
    }
    if (
      plan.intent === 'GRADE_QUERY' &&
      history.courses.some(
        (course) =>
          'term' in course &&
          plan.entities.term &&
          course.term !== plan.entities.term,
      )
    )
      throw new Error('Unrequested grade term')
    if (
      ['GRADE_QUERY', 'COURSE_STATUS'].includes(plan.intent) &&
      plan.entities.courseCodes &&
      history.courses.some(
        (course) => !plan.entities.courseCodes?.includes(course.courseCode),
      )
    )
      throw new Error('Unrelated student course')
  }
  if (JSON.stringify(context).length > 16000)
    throw new Error(
      'Context exceeds the bounded academic budget; narrow the query',
    )
  return context
}
