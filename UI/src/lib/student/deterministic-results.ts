import { z } from 'zod'

const checkStatus = z.enum(['VALID', 'INVALID', 'UNKNOWN'])
const reason = z.enum([
  'MISSING_CONTEXT',
  'MISSING_REVIEWED_POLICY',
  'UNSUPPORTED_PREREQUISITE',
  'UNKNOWN_COURSE_RESULT',
  'PREREQUISITE_NOT_PASSED',
  'COURSE_ALREADY_PASSED',
  'MISSING_COURSE',
  'MISSING_CREDITS',
  'CREDIT_LIMIT_EXCEEDED',
  'MISSING_SCHEDULE',
  'INVALID_SCHEDULE',
  'SCHEDULE_CONFLICT',
  'PREFERENCE_NOT_MET',
  'PARTIAL_SEARCH',
])
const check = z.strictObject({
  courseCode: z.string().min(1).max(40),
  status: checkStatus,
  missingPrerequisites: z.array(z.string()).max(100),
  reasons: z.array(reason).max(16),
})
export const deterministicResultsSchema = z
  .array(
    z.strictObject({
      tool: z.enum([
        'validate_prerequisites',
        'detect_schedule_conflicts',
        'validate_credit_load',
        'simulate_enrollment',
        'list_available_courses',
      ]),
      result: z.strictObject({
        status: checkStatus,
        engineVersion: z.literal('pre-enrollment-v1'),
        reasons: z.array(reason).max(16),
        checks: z.array(check).max(100),
        conflicts: z
          .array(
            z.strictObject({
              courseA: z.string(),
              sectionA: z.number().int().nonnegative(),
              courseB: z.string(),
              sectionB: z.number().int().nonnegative(),
              day: z.enum([
                'LUNES',
                'MARTES',
                'MIERCOLES',
                'JUEVES',
                'VIERNES',
                'SABADO',
              ]),
              startMinutes: z.number().int().min(0).max(1439),
              endMinutes: z.number().int().min(1).max(1440),
            }),
          )
          .max(100),
        alternatives: z
          .array(
            z.strictObject({
              selections: z
                .array(
                  z.strictObject({
                    courseCode: z.string().min(1).max(40),
                    section: z.number().int().nonnegative(),
                  }),
                )
                .min(1)
                .max(5),
              totalCredits: z.number().nonnegative().max(500),
              idleMinutes: z.number().int().nonnegative(),
            }),
          )
          .max(3),
        totalCredits: z.number().nonnegative().max(500).nullable(),
        creditLimit: z.number().positive().max(100).nullable(),
        ruleId: z.string().nullable(),
        ruleVersion: z.string().nullable(),
        citationIds: z.array(z.uuid()).max(8),
        examinedCombinations: z.number().int().min(0).max(64),
        truncated: z.boolean(),
        rankingCriteria: z
          .array(z.enum(['MIN_IDLE_MINUTES', 'SECTION_ORDER']))
          .max(2),
      }),
    }),
  )
  .max(6)

export const validationLabels = {
  VALID: 'Comprobación válida',
  INVALID: 'Condición no satisfecha',
  UNKNOWN: 'Falta información verificada',
}
export const toolLabels = {
  validate_prerequisites: 'Prerrequisitos',
  detect_schedule_conflicts: 'Cruces de horario',
  validate_credit_load: 'Carga de créditos',
  simulate_enrollment: 'Simulación de pre-matrícula',
  list_available_courses: 'Cursos ofrecidos elegibles',
}
export const reasonLabels: Record<z.infer<typeof reason>, string> = {
  MISSING_CONTEXT: 'Falta contexto académico.',
  MISSING_REVIEWED_POLICY:
    'Falta una regla institucional revisada y aplicable.',
  UNSUPPORTED_PREREQUISITE: 'La semántica del prerrequisito requiere revisión.',
  UNKNOWN_COURSE_RESULT: 'Falta un resultado académico verificado.',
  PREREQUISITE_NOT_PASSED: 'Hay prerrequisitos sin aprobar.',
  COURSE_ALREADY_PASSED: 'El curso ya está aprobado.',
  MISSING_COURSE: 'No se identificó el curso.',
  MISSING_CREDITS: 'Faltan créditos del curso.',
  CREDIT_LIMIT_EXCEEDED: 'Se excede el límite de créditos.',
  MISSING_SCHEDULE: 'Falta un horario o una sección sin ambigüedad.',
  INVALID_SCHEDULE: 'Hay horarios incompletos o inconsistentes.',
  SCHEDULE_CONFLICT: 'Hay cruces de horario.',
  PREFERENCE_NOT_MET:
    'No se encontró una combinación que cumpla las preferencias y evite cruces.',
  PARTIAL_SEARCH:
    'Se alcanzó el límite de combinaciones; la búsqueda es parcial.',
}
