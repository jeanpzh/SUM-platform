import { z } from 'zod'
import { deterministicResultsSchema } from './deterministic-results'
import type { UIMessage } from 'ai'
import { runResultSchema, runSchema } from '#/lib/ai/client'

export const optionsSchema = z.strictObject({
  use_academic_context: z.boolean(),
  connection_id: z.uuid().nullable().optional(),
  course_hint: z.string().trim().min(1).max(120).nullable().optional(),
})
export type StudentOptions = z.infer<typeof optionsSchema>
const academicField = z.enum([
  'curriculum',
  'course_attempts',
  'enrollment',
  'academic_period',
])
export const analysisSchema = z.strictObject({
  route: z.enum(['regulations', 'personalized', 'clarification']),
  answer_basis: z
    .enum(['published_rag', 'sum_projection', 'clarification'])
    .default('published_rag'),
  context: z.strictObject({
    status: z.enum([
      'not_requested',
      'available',
      'missing',
      'expired',
      'unavailable',
    ]),
    source: z.enum(['sum', 'mock']).nullable(),
    snapshot_id: z.uuid().nullable(),
    missing_fields: z.array(academicField).max(4),
  }),
  checks: z
    .array(
      z.strictObject({
        rule_id: z.string(),
        version: z.string(),
        outcome: z.enum(['satisfied', 'not_satisfied', 'unknown']),
        description: z.string(),
        citation_ids: z.array(z.uuid()).max(8),
        missing_fields: z.array(academicField).max(4),
      }),
    )
    .max(8),
  deterministic_results: deterministicResultsSchema.default([]),
  components: z
    .array(z.enum(['sources', 'context_status', 'rule_checks', 'next_steps']))
    .max(4),
  next_steps: z.array(z.string()).max(5),
  trace_id: z.uuid().nullable(),
})
export const studentResultSchema = runResultSchema.extend({
  student_analysis: analysisSchema.nullable(),
})
export const studentRunSchema = runSchema.extend({
  audience: z.literal('student'),
  student_options: optionsSchema,
  result: studentResultSchema.nullable(),
})
export const publicAuditSchema = z.object({
  sequence: z.number().int().nonnegative(),
  kind: z.string(),
  stage: z.string().nullable(),
  duration_ms: z.number().nullable(),
  code: z.string().nullable(),
  created_at: z.string(),
  tool: z.string().nullable(),
})
export const dataSchemas = {
  run: z.strictObject({ run_id: z.uuid() }),
  audit: publicAuditSchema,
  result: studentResultSchema,
}
export type StudentResult = z.infer<typeof studentResultSchema>
export type StudentRun = z.infer<typeof studentRunSchema>
export type StudentAudit = z.infer<typeof publicAuditSchema>
export type StudentMessage = UIMessage<
  { run_id: string },
  {
    run: { run_id: string }
    audit: StudentAudit
    result: StudentResult
  }
>

export async function studentFetch(path: string, init?: RequestInit) {
  const response = await fetch(`/api/student/ai/${path}`, {
    credentials: 'same-origin',
    ...init,
  })
  if (!response.ok) {
    if (response.status === 401)
      throw new Error('Inicia sesión para ver tus consultas.')
    if (response.status === 429)
      throw new Error('Alcanzaste tu límite de consultas. Intenta más tarde.')
    throw new Error('No se pudo recuperar la consulta. Intenta nuevamente.')
  }
  return response.json()
}
