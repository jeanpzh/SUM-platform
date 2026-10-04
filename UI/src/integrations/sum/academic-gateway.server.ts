import { z } from 'zod'
import { AcademicContextBuilder } from '../../academic/context/context-builder'
import {
  academicQueryPlanSchema,
  academicQueryContextSchema,
  policyScopeSchema,
} from '../../academic/context/schemas'
import type { StudentSession } from './source'

const gatewayRequestSchema = z.strictObject({
  schema_version: z.literal('academic-context-v2'),
  run_id: z.uuid(),
  owner_id: z.string().min(1).max(160),
  connection_id: z.uuid(),
  query: z.string().trim().min(3).max(2000),
  plan: academicQueryPlanSchema,
})
export const academicContextEnvelopeSchema = z.strictObject({
  schemaVersion: z.literal('academic-context-v2'),
  source: z.enum(['sum', 'mock']),
  snapshotId: z.uuid(),
  retrievedAt: z.iso.datetime(),
  expiresAt: z.iso.datetime(),
  context: academicQueryContextSchema,
  policyScope: policyScopeSchema.optional(),
  missingRequirements: z
    .array(
      z.enum([
        'ACADEMIC_HISTORY',
        'STUDY_PLAN',
        'ACADEMIC_PROGRAMMING',
        'INSTITUTIONAL_RULES',
      ]),
    )
    .max(4),
})

interface GatewayDependencies {
  /** Must authenticate the AI service; never forward its headers into SUM context. */
  authorize(request: Request): Promise<boolean>
  /** Verify ownership, consent, connection lifetime; resolve plan/faculty/school selectors on the server. */
  resolveSession(ownerId: string, connectionId: string): Promise<StudentSession>
  /** Configure without retrieveRules: the Python AI service owns published RAG retrieval. */
  builder: AcademicContextBuilder
  source?: 'sum' | 'mock'
}

/** Mount at /internal/academic-context in the future SUM gateway, after its adapter is provided. */
export function createAcademicGatewayHandler(deps: GatewayDependencies) {
  return async (request: Request): Promise<Response> => {
    const respond = (value: unknown, status = 200) =>
      Response.json(value, { status, headers: { 'Cache-Control': 'no-store' } })
    if (request.method !== 'POST')
      return respond({ code: 'METHOD_NOT_ALLOWED' }, 405)
    if (!(await deps.authorize(request)))
      return respond({ code: 'ACADEMIC_GATEWAY_UNAUTHORIZED' }, 403)
    try {
      const body = await request.text()
      if (body.length > 16000)
        return respond({ code: 'ACADEMIC_REQUEST_TOO_LARGE' }, 413)
      const input = gatewayRequestSchema.parse(JSON.parse(body))
      const session = await deps.resolveSession(
        input.owner_id,
        input.connection_id,
      )
      if (session.connectionId !== input.connection_id)
        return respond({ code: 'ACADEMIC_CONNECTION_INVALID' }, 403)
      if (
        session.policyScope &&
        (session.policyScope.planCode.trim() !== session.planCode.trim() ||
          (input.plan.entities.term &&
            session.policyScope.term !== input.plan.entities.term))
      )
        return respond({ code: 'ACADEMIC_POLICY_SCOPE_INVALID' }, 403)
      const retrievedAt = new Date()
      const context = await deps.builder.buildFromPlan(
        input.query,
        session,
        input.plan,
      )
      if (context.institutionalRules)
        throw new Error('Shared RAG must be retrieved in the AI service')
      return respond(
        academicContextEnvelopeSchema.parse({
          schemaVersion: 'academic-context-v2',
          source: deps.source ?? 'sum',
          snapshotId: crypto.randomUUID(),
          retrievedAt: retrievedAt.toISOString(),
          expiresAt: new Date(retrievedAt.getTime() + 60000).toISOString(),
          context,
          ...(session.policyScope
            ? { policyScope: policyScopeSchema.parse(session.policyScope) }
            : {}),
          missingRequirements: [],
        }),
      )
    } catch {
      // Validation/provider errors can contain raw input: return a code only, never log the exception.
      return respond({ code: 'ACADEMIC_CONTEXT_UNAVAILABLE' }, 503)
    }
  }
}
