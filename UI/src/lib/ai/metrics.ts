import * as z from 'zod'
import { runSchema, AiHttpError } from './client'

const latency = z.object({
  count: z.number().nonnegative(),
  mean_ms: z.number().nullable(),
  p50_ms: z.number().nullable(),
  p95_ms: z.number().nullable(),
  percentiles_approximate: z.boolean(),
})
const metricsSchema = z.object({
  days: z.number(),
  summary: latency.extend({
    statuses: z.record(z.string(), z.number()),
    abstentions: z.number(),
    rate_limits: z.number(),
    timeouts: z.number(),
    input_tokens: z.number(),
    output_tokens: z.number(),
    estimated_cost_usd: z.number(),
    tool_calls: z.number(),
  }),
  stages: z.array(latency.extend({ stage: z.string() })),
  series: z.array(
    latency.extend({ hour: z.string(), estimated_cost_usd: z.number() }),
  ),
  quality: z
    .object({
      count: z.number(),
      recall_at_k: z.number(),
      precision_at_k: z.number(),
      mrr: z.number(),
    })
    .nullable(),
})
export type MetricsResponse = z.infer<typeof metricsSchema>
export type MetricsFilters = {
  days: number
  provider?: string
  model?: string
  generation?: string
  status?: string
}

export async function fetchMetrics(
  filters: MetricsFilters,
  signal?: AbortSignal,
): Promise<MetricsResponse> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters))
    if (value !== undefined && value !== '') params.set(key, String(value))
  const response = await fetch(`/api/ai/metrics?${params}`, {
    credentials: 'same-origin',
    signal,
  })
  if (!response.ok) throw new AiHttpError(response.status)
  return metricsSchema.parse(await response.json())
}

export function latencyLabel(value: number | null): string {
  return value === null ? 'Sin datos' : `${(value / 1000).toFixed(2)} s`
}

const evaluationCatalogSchema = z.object({
  datasets: z.array(
    z.object({
      dataset_id: z.string(),
      version: z.string(),
      cases: z.number(),
      available: z.boolean(),
    }),
  ),
  evaluations: z.array(
    z.object({
      id: z.uuid(),
      dataset_id: z.string(),
      dataset_version: z.string(),
      provider: z.string(),
      model: z.string(),
      created_at: z.string(),
      cases: z.number(),
      completed: z.number(),
      failed: z.number(),
      recall_at_k: z.number().nullable(),
      precision_at_k: z.number().nullable(),
      mrr: z.number().nullable(),
    }),
  ),
})
export type EvaluationCatalog = z.infer<typeof evaluationCatalogSchema>
export async function fetchEvaluations(): Promise<EvaluationCatalog> {
  const response = await fetch('/api/ai/evaluations', {
    credentials: 'same-origin',
  })
  if (!response.ok) throw new AiHttpError(response.status)
  return evaluationCatalogSchema.parse(await response.json())
}
export async function startEvaluation(
  datasetId: string,
  provider: string,
  model: string,
  providerConfigId?: string | null,
  providerRevision?: number | null,
): Promise<void> {
  const response = await fetch('/api/ai/evaluations', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': crypto.randomUUID(),
    },
    body: JSON.stringify({
      dataset_id: datasetId,
      provider,
      model,
      ...(providerConfigId
        ? {
            provider_config_id: providerConfigId,
            provider_revision: providerRevision,
          }
        : {}),
    }),
  })
  if (!response.ok) throw new AiHttpError(response.status)
}

export async function fetchMetricRuns(
  filters: MetricsFilters,
  page = 0,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({ limit: '21', offset: String(page * 20) })
  for (const [key, value] of Object.entries(filters))
    if (value !== undefined && value !== '') params.set(key, String(value))
  const response = await fetch(`/api/ai/runs?${params}`, {
    credentials: 'same-origin',
    signal,
  })
  if (!response.ok) throw new AiHttpError(response.status)
  return z.array(runSchema).parse(await response.json())
}
