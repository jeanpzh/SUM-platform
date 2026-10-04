import type { ProgramacionResponse } from '../../../../types-SUM/programacion-academica'
import { programmingDomainSchema } from '../../../academic/context/schemas'
import type { ProgrammingDomain } from '../../../academic/context/schemas'

export function normalizeProgramming(
  raw: ProgramacionResponse,
): ProgrammingDomain {
  // The alumno block is deliberately never read. No identity, profile or enrollment payload crosses this boundary.
  return programmingDomainSchema.parse({
    courses: raw.data.programacion.map((course) => ({
      courseCode: course.codAsignatura.trim(),
      courseName: course.desAsignatura.trim(),
      section: course.codSeccion,
      schedule: course.horarios.map((slot) => ({
        day: slot.dia,
        start: slot.horaInicio,
        end: slot.horaFin,
        room: slot.codAula.trim(),
        type: slot.codTipoHoraAsignatura,
      })),
    })),
  })
}
