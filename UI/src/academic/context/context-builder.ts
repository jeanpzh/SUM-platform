import type { StudentSession, SumSources } from '../../integrations/sum/source'
import { normalizeHistory } from '../../integrations/sum/mappers/historial.mapper'
import type { ReviewedGradingPolicy } from '../../integrations/sum/mappers/historial.mapper'
import { normalizePlan } from '../../integrations/sum/mappers/plan.mapper'
import { normalizeProgramming } from '../../integrations/sum/mappers/programacion.mapper'
import { ContextPlanner } from './context-planner'
import {
  academicQueryPlanSchema,
  institutionalRulesContextSchema,
  validateContextForPlan,
} from './schemas'
import type {
  AcademicQueryContext,
  AcademicQueryPlan,
  PlanDomain,
  HistoryDomain,
} from './schemas'
import {
  completedCredits,
  courseStatus,
  prerequisiteGraph,
  projectPlan,
  projectSchedule,
  selectCourses,
  selectSections,
} from './projections'

interface BuilderDependencies {
  planner: ContextPlanner
  sources: SumSources
  policy?: ReviewedGradingPolicy
  retrieveRules?: (
    query: string,
  ) => Promise<Array<{ citationId: string; text: string }>>
  audit?: (summary: {
    intent: string
    requirements: readonly string[]
    categories: string[]
    bytes: number
    gradingPolicyVersion?: string
  }) => void | Promise<void>
}

export class AcademicContextBuilder {
  private deps: BuilderDependencies
  constructor(deps: BuilderDependencies) {
    this.deps = deps
  }

  async build(
    query: string,
    session: StudentSession,
  ): Promise<AcademicQueryContext> {
    return this.buildFromPlan(
      query,
      session,
      await this.deps.planner.plan({ query }),
    )
  }

  async buildFromPlan(
    query: string,
    session: StudentSession,
    input: AcademicQueryPlan,
  ): Promise<AcademicQueryContext> {
    const plan = academicQueryPlanSchema.parse(input)
    const required = new Set(plan.requirements)
    const context: AcademicQueryContext = {}
    // One fetch per selected endpoint, in parallel. No course-by-course network requests.
    const [history, curriculum, programming] = await Promise.all([
      required.has('ACADEMIC_HISTORY')
        ? this.deps.sources
            .history(session)
            .then((raw) => normalizeHistory(raw, this.deps.policy))
        : undefined,
      required.has('STUDY_PLAN')
        ? this.deps.sources
            .plan(session)
            .then((raw) => normalizePlan(raw, session.planCode))
        : undefined,
      required.has('ACADEMIC_PROGRAMMING')
        ? this.deps.sources
            .programming(session, plan.entities.term)
            .then(normalizeProgramming)
        : undefined,
    ])
    const complete = session.historyComplete === true
    let graph: PlanDomain['courses'] = []
    if (curriculum) {
      if (plan.intent === 'REMAINING_COURSES' && history) {
        // History is needed to derive the pending set but individual grades/statuses are not exposed.
        const pending = curriculum.courses.filter(
          (course) =>
            courseStatus(history, course.courseCode, complete) !== 'PASSED',
        )
        context.studyPlan = projectPlan(pending, true)
        context.studyPlan.progressVerified =
          complete &&
          history.courses.every((course) => course.status !== 'UNKNOWN')
      } else if (plan.intent === 'LIST_AVAILABLE_COURSES') {
        const offered = new Set(
          programming?.courses.map((course) => course.courseCode),
        )
        const candidates = curriculum.courses.filter(
          (course) =>
            offered.has(course.courseCode) &&
            history &&
            courseStatus(history, course.courseCode, complete) !== 'PASSED',
        )
        graph = prerequisiteGraph(curriculum.courses, candidates)
        context.studyPlan = projectPlan(
          graph,
          false,
          new Set(candidates.map((c) => c.courseCode)),
        )
      } else {
        const targets = selectCourses(curriculum.courses, plan)
        graph = ['CHECK_PREREQUISITES', 'CHECK_CREDIT_LOAD'].includes(
          plan.intent,
        )
          ? targets
          : prerequisiteGraph(curriculum.courses, targets)
        context.studyPlan =
          plan.intent === 'CHECK_CREDIT_LOAD'
            ? {
                courses: targets.map((c) => ({
                  courseCode: c.courseCode,
                  courseName: c.courseName,
                  credits: c.credits,
                })),
              }
            : projectPlan(
                graph,
                false,
                plan.intent === 'SIMULATE_ENROLLMENT'
                  ? new Set(targets.map((c) => c.courseCode))
                  : new Set(),
              )
      }
    }
    if (history) {
      if (plan.intent === 'COMPLETED_CREDITS')
        context.academicHistory = completedCredits(history, complete)
      else if (
        plan.intent === 'COURSE_STATUS' ||
        plan.intent === 'GRADE_QUERY'
      ) {
        const scopedHistory = {
          courses: history.courses.filter(
            (course) =>
              !plan.entities.term || course.term === plan.entities.term,
          ),
        }
        const selected = selectCourses(scopedHistory.courses, plan)
        const codes = Array.from(
          new Set(selected.map((course) => course.courseCode)),
        )
        context.academicHistory =
          plan.intent === 'GRADE_QUERY'
            ? {
                courses: selected.map((course) => ({
                  courseCode: course.courseCode,
                  status: course.status,
                  grade: course.grade,
                  term: course.term,
                })),
              }
            : {
                courses: codes.map((courseCode) => ({
                  courseCode,
                  status: courseStatus(scopedHistory, courseCode, complete),
                })),
              }
      } else if (plan.intent !== 'REMAINING_COURSES') {
        context.academicHistory = this.projectRelevantHistory(
          history,
          graph,
          complete,
        )
      }
    }
    if (programming) {
      if (
        [
          'GET_COURSE_SCHEDULE',
          'CHECK_SCHEDULE_CONFLICTS',
          'SIMULATE_ENROLLMENT',
        ].includes(plan.intent)
      )
        context.academicProgramming = projectSchedule(
          selectSections(programming.courses, plan),
          plan.intent === 'GET_COURSE_SCHEDULE',
        )
      else {
        const graphCodes = new Set(
          context.studyPlan?.courses
            .filter((c) => c.credits !== undefined)
            .map((c) => c.courseCode),
        )
        const offered = programming.courses.filter((course) =>
          graphCodes.has(course.courseCode),
        )
        context.academicProgramming = {
          courses: Array.from(
            new Map(
              offered.map((course) => [
                course.courseCode,
                {
                  courseCode: course.courseCode,
                  courseName: course.courseName,
                },
              ]),
            ).values(),
          ),
        }
      }
    }
    if (required.has('INSTITUTIONAL_RULES') && this.deps.retrieveRules) {
      const chunks = await this.deps.retrieveRules(query)
      context.institutionalRules = institutionalRulesContextSchema.parse({
        chunks: chunks.slice(0, 3).map((chunk) => ({
          citationId: chunk.citationId,
          text: chunk.text.slice(0, 800),
        })),
      })
    }
    const validated = validateContextForPlan(context, plan)
    await this.deps.audit?.({
      intent: plan.intent,
      requirements: plan.requirements,
      categories: Object.keys(validated),
      bytes: JSON.stringify(validated).length,
      gradingPolicyVersion: this.deps.policy?.version,
    })
    return validated
  }

  private projectRelevantHistory(
    history: HistoryDomain,
    graph: PlanDomain['courses'],
    complete: boolean,
  ): AcademicQueryContext['academicHistory'] {
    const relevantCodes = Array.from(
      new Set([
        ...graph.flatMap((course) =>
          course.prerequisites.flatMap((p) =>
            p.courseCode ? [p.courseCode] : [],
          ),
        ),
        ...graph.map((course) => course.courseCode),
      ]),
    )
    return {
      courses: relevantCodes.map((courseCode) => ({
        courseCode,
        status: courseStatus(history, courseCode, complete),
      })),
    }
  }
}

export async function buildAcademicContext(
  query: string,
  studentSession: StudentSession,
  dependencies: BuilderDependencies,
): Promise<AcademicQueryContext> {
  return new AcademicContextBuilder(dependencies).build(query, studentSession)
}
