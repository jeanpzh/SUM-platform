import type { PlanResponse } from '../../../../types-SUM/plan'
import { planDomainSchema } from '../../../academic/context/schemas'
import type { PlanDomain } from '../../../academic/context/schemas'

export function normalizePlan(raw: PlanResponse, planCode: string): PlanDomain {
  const courses = new Map<string, PlanDomain['courses'][number]>()
  for (const row of raw.data) {
    if (row.codPlan.trim() !== planCode.trim()) continue
    const code = row.codAsignatura.trim()
    let course = courses.get(code)
    if (!course) {
      course = {
        courseCode: code,
        courseName: row.desAsignatura.trim(),
        credits: row.creditos,
        type: row.tipoAsignatura,
        group: row.codGrupo.trim(),
        prerequisites: [],
      }
      courses.set(code, course)
    } else if (
      course.courseName !== row.desAsignatura.trim() ||
      course.credits !== row.creditos ||
      course.type !== row.tipoAsignatura ||
      course.group !== row.codGrupo.trim()
    ) {
      throw new Error(
        'Conflicting curriculum rows; resolve the study-plan scope',
      )
    }
    const prerequisiteCode = row.codAsignaturaPre.trim()
    if (
      (prerequisiteCode && prerequisiteCode !== '--') ||
      row.codGrupoPre.trim() !== '--' ||
      row.creditosPre > 0
    ) {
      const hasCourse = Boolean(prerequisiteCode && prerequisiteCode !== '--')
      const edge = {
        courseCode: hasCourse ? prerequisiteCode : null,
        courseName: hasCourse ? row.desAsignaturaPre.trim() : null,
        group: row.codGrupoPre.trim(),
        credits: row.creditosPre,
      }
      if (
        !course.prerequisites.some(
          (p) =>
            p.courseCode === edge.courseCode &&
            p.group === edge.group &&
            p.credits === edge.credits,
        )
      )
        course.prerequisites.push(edge)
    }
  }
  return planDomainSchema.parse({ courses: Array.from(courses.values()) })
}
