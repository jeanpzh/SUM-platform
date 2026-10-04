import type { HistorialResponse } from '../../../../types-SUM/historial-academico'
import { historyDomainSchema } from '../../../academic/context/schemas'
import type { HistoryDomain } from '../../../academic/context/schemas'

export interface ReviewedGradingPolicy {
  version: string
  outcome(input: {
    grade: number
    term: string
    gradingCriterion: boolean
  }): 'PASSED' | 'FAILED' | 'WITHDRAWN' | 'UNKNOWN'
}
export function normalizeHistory(
  raw: HistorialResponse,
  policy?: ReviewedGradingPolicy,
): HistoryDomain {
  return historyDomainSchema.parse({
    courses: raw.data.historial.map((course) => ({
      courseCode: course.codAsignatura.trim(),
      courseName: course.desAsignatura.trim(),
      credits: course.creditos,
      grade: course.calificacion,
      term: course.codSemestre.trim(),
      status:
        policy?.outcome({
          grade: course.calificacion,
          term: course.codSemestre.trim(),
          gradingCriterion: raw.data.criterioCalificacion,
        }) ?? 'UNKNOWN',
    })),
  })
}
