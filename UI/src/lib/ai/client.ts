import * as z from 'zod'

const uuid = z.uuid()
export const modelChoiceSchema = z.strictObject({
  provider: z.enum([
    'ollama',
    'openai',
    'anthropic',
    'google',
    'groq',
    'custom',
  ]),
  model: z.string().min(1),
  available: z.boolean(),
  provider_config_id: uuid.nullable().optional(),
  provider_revision: z.number().int().positive().nullable().optional(),
  connection_name: z.string().optional(),
  supports_tools: z.boolean(),
  supports_structured_output: z.boolean(),
  pricing_date: z.string(),
  input_usd_per_million: z.number().nonnegative(),
  output_usd_per_million: z.number().nonnegative(),
})
export type ModelChoice = z.infer<typeof modelChoiceSchema>

export const evidenceSchema = z.strictObject({
  chunk_id: uuid,
  document_id: uuid,
  version_id: uuid,
  generation_id: uuid,
  page: z.number().int().positive(),
  locator: z.string(),
  text: z.string(),
  rank: z.number().int().positive(),
  score: z.number().nullable().optional(),
})
export const citationSchema = evidenceSchema.pick({
  chunk_id: true,
  document_id: true,
  version_id: true,
  generation_id: true,
  page: true,
  locator: true,
})
export type Citation = z.infer<typeof citationSchema>

export const runResultSchema = z.strictObject({
  answer: z.string(),
  citations: z.array(citationSchema),
  evidence: z.array(evidenceSchema),
  provider: z.string(),
  model: z.string(),
  usage: z.strictObject({
    input_tokens: z.number().nonnegative(),
    output_tokens: z.number().nonnegative(),
    estimated_cost_usd: z.number().nonnegative(),
    pricing_date: z.string().nullable().optional(),
  }),
  timings: z.record(z.string(), z.number()),
  tool_trace: z.array(z.record(z.string(), z.unknown())),
  limitations: z.array(z.string()),
  abstained: z.boolean(),
  student_analysis: z.unknown().nullable().optional(),
  evaluation: z
    .object({
      recall_at_k: z.number(),
      precision_at_k: z.number(),
      mrr: z.number(),
      k: z.number(),
    })
    .nullable()
    .optional(),
})
export type RunResult = z.infer<typeof runResultSchema>

export const runSchema = z.object({
  run_id: uuid,
  status: z.enum(['queued', 'running', 'completed', 'failed', 'cancelled']),
  stage: z.string().nullable().optional(),
  sequence: z.number().int().nonnegative(),
  provider: z.string().optional(),
  model: z.string().optional(),
  question: z.string().optional(),
  retrieval_audit: z
    .object({
      evidence: z.array(evidenceSchema).max(8),
      generation_ids: z.array(uuid).max(8),
      profiles: z.array(z.record(z.string(), z.unknown())).max(2),
      corpus_sha256: z.string(),
    })
    .optional(),
  configuration: z
    .object({
      name: z.string(),
      base_url: z.string(),
      revision: z.number(),
      models: z.array(
        z.object({
          model: z.string(),
          input_usd_per_million: z.number(),
          output_usd_per_million: z.number(),
          pricing_date: z.string(),
        }),
      ),
    })
    .optional(),
  provider_config_id: uuid.nullable().optional(),
  provider_revision: z.number().int().positive().nullable().optional(),
  result: runResultSchema.nullable().optional(),
  error_code: z.string().nullable().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
})
export type Run = z.infer<typeof runSchema>

const requestSchema = z.strictObject({
  question: z.string().trim().min(3).max(2000),
  provider: modelChoiceSchema.shape.provider,
  model: z.string().min(1).max(150),
  provider_config_id: uuid.optional(),
  provider_revision: z.number().int().positive().optional(),
  document_ids: z.array(uuid).max(20),
  top_k: z.number().int().min(1).max(10),
})
export type CreateRunRequest = z.infer<typeof requestSchema>

const auditSchema = z.object({
  sequence: z.number().int().nonnegative(),
  operation_id: z.string(),
  kind: z.string(),
  stage: z.string().nullable().optional(),
  duration_ms: z.number().nullable().optional(),
  code: z.string().nullable().optional(),
  payload: z.record(z.string(), z.unknown()),
  created_at: z.string(),
})
export type AuditEvent = z.infer<typeof auditSchema>

export class AiHttpError extends Error {
  readonly status: number
  readonly retryAfter: number | null
  constructor(status: number, retryAfter: number | null = null) {
    super(
      status === 429
        ? 'Se alcanzó la cuota de consultas. Intenta más tarde.'
        : status === 401 || status === 403
          ? 'Inicia sesión como administrador.'
          : 'No se pudo completar la consulta de IA.',
    )
    this.status = status
    this.retryAfter = retryAfter
  }
}

async function checked(response: Response) {
  if (!response.ok) {
    const retry = Number(response.headers.get('retry-after'))
    throw new AiHttpError(
      response.status,
      Number.isFinite(retry) && retry > 0 ? retry : null,
    )
  }
  return response.json()
}

export async function fetchModels(
  signal?: AbortSignal,
): Promise<ModelChoice[]> {
  return z
    .array(modelChoiceSchema)
    .parse(
      await checked(
        await fetch('/api/ai/models', { credentials: 'same-origin', signal }),
      ),
    )
}

export async function createRun(
  input: CreateRunRequest,
  key: string,
): Promise<Run> {
  const payload = requestSchema.parse(input)
  if (!key || key.length > 200)
    throw new Error('Clave de idempotencia inválida.')
  return runSchema.parse(
    await checked(
      await fetch('/api/ai/runs', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key },
        body: JSON.stringify(payload),
      }),
    ),
  )
}

export async function getRun(
  runId: string,
  signal?: AbortSignal,
): Promise<Run> {
  return runSchema.parse(
    await checked(
      await fetch(`/api/ai/runs/${uuid.parse(runId)}`, {
        credentials: 'same-origin',
        signal,
      }),
    ),
  )
}

export async function cancelRun(runId: string): Promise<Run> {
  return runSchema.parse(
    await checked(
      await fetch(`/api/ai/runs/${uuid.parse(runId)}/cancel`, {
        method: 'POST',
        credentials: 'same-origin',
      }),
    ),
  )
}

export async function fetchRunEvents(
  runId: string,
  signal?: AbortSignal,
): Promise<AuditEvent[]> {
  const response = await fetch(`/api/ai/runs/${uuid.parse(runId)}/events`, {
    credentials: 'same-origin',
    signal,
  })
  if (!response.ok) throw new AiHttpError(response.status)
  const raw = await response.text()
  return raw.split('\n\n').flatMap((block) => {
    const data = block
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())
      .join('\n')
    return data ? [auditSchema.parse(JSON.parse(data))] : []
  })
}

export function watchRun(
  runId: string,
  after: number,
  onEvent: (event: AuditEvent) => void,
  onError?: (error: Error) => void,
): () => void {
  uuid.parse(runId)
  const controller = new AbortController()
  void (async () => {
    let cursor = after
    let reconnects = 0
    while (!controller.signal.aborted && reconnects < 5) {
      try {
        const response = await fetch(`/api/ai/runs/${runId}/events`, {
          credentials: 'same-origin',
          headers: { 'Last-Event-ID': String(cursor) },
          signal: controller.signal,
        })
        if (!response.ok || !response.body)
          throw new AiHttpError(response.status)
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder
            .decode(value, { stream: true })
            .replace(/\r\n/g, '\n')
          let boundary: number
          while ((boundary = buffer.indexOf('\n\n')) >= 0) {
            const block = buffer.slice(0, boundary)
            buffer = buffer.slice(boundary + 2)
            const data = block
              .split('\n')
              .filter((line) => line.startsWith('data:'))
              .map((line) => line.slice(5).trim())
              .join('\n')
            if (!data) continue
            const event = auditSchema.parse(JSON.parse(data))
            if (event.sequence <= cursor) continue
            cursor = event.sequence
            onEvent(event)
            if (['completed', 'failed', 'cancelled'].includes(event.kind))
              return
          }
        }
        reconnects++
      } catch (cause) {
        if (controller.signal.aborted) return
        reconnects++
        if (reconnects >= 5) {
          onError?.(
            cause instanceof Error
              ? cause
              : new Error('Conexión interrumpida.'),
          )
          return
        }
      }
      if (!controller.signal.aborted)
        await new Promise((resolve) =>
          setTimeout(resolve, Math.min(1000 * reconnects, 5000)),
        )
    }
    if (!controller.signal.aborted)
      onError?.(new Error('Conexión interrumpida.'))
  })()
  return () => controller.abort()
}
