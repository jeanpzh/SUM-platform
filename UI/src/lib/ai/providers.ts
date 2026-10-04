import * as z from 'zod'

export const providerKinds = [
  'ollama',
  'openai',
  'google',
  'groq',
  'anthropic',
  'custom',
] as const
export type ProviderKind = (typeof providerKinds)[number]
export const providerDefinitions: Record<
  ProviderKind,
  { label: string; url: string; local?: boolean }
> = {
  ollama: {
    label: 'Ollama',
    url: 'http://host.docker.internal:11434',
    local: true,
  },
  openai: { label: 'OpenAI', url: 'https://api.openai.com/v1' },
  google: {
    label: 'Google Gemini',
    url: 'https://generativelanguage.googleapis.com',
  },
  groq: { label: 'GroqCloud', url: 'https://api.groq.com/openai/v1' },
  anthropic: { label: 'Anthropic', url: 'https://api.anthropic.com' },
  custom: {
    label: 'Custom',
    url: 'http://host.docker.internal:8080/v1',
    local: true,
  },
}
const modelSchema = z.strictObject({
  model: z
    .string()
    .min(1)
    .max(150)
    .regex(/^[A-Za-z0-9._:/-]+$/),
  input_usd_per_million: z.number().finite().min(0).max(10000),
  output_usd_per_million: z.number().finite().min(0).max(10000),
  pricing_date: z.iso.date(),
})
export const providerInputSchema = z.strictObject({
  provider: z.enum(providerKinds),
  name: z.string().trim().min(1).max(100),
  base_url: z.url().max(500),
  api_key: z.string().max(4096),
  priority: z.enum(['high', 'normal', 'low']),
  enabled: z.boolean(),
  models: z
    .array(modelSchema)
    .min(1)
    .max(20)
    .refine(
      (models) =>
        new Set(models.map((model) => model.model)).size === models.length,
      'No repitas modelos.',
    ),
  expected_revision: z.number().int().positive().optional(),
})
export type ProviderInput = z.infer<typeof providerInputSchema>
const providerSchema = providerInputSchema
  .omit({ api_key: true, expected_revision: true })
  .extend({
    id: z.uuid(),
    revision: z.number().int().positive(),
    has_api_key: z.boolean(),
    created_at: z.string(),
  })
export type ProviderConnection = z.infer<typeof providerSchema>

async function checked(response: Response) {
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const known: Record<string, string> = {
      AI_PROVIDER_HOST_DENIED:
        'Autoriza este host en AI_PROVIDER_ALLOWED_HOSTS del servidor.',
      AI_PROVIDER_KEY_MISSING:
        'Falta AI_PROVIDER_ENCRYPTION_KEY en el backend.',
      AI_PROVIDER_CONFLICT:
        'La conexión cambió. Recarga Settings antes de editarla.',
      AI_PROVIDER_KEY_REQUIRED: 'Introduce una API key para este proveedor.',
      AI_PROVIDER_URL_INVALID: 'Usa la URL oficial del proveedor.',
      AI_PROVIDER_NOT_FOUND:
        'La conexión no existe o no pertenece a este administrador.',
      AI_PROVIDER_RATE_LIMIT:
        'Se alcanzó una cuota. Espera antes de volver a probar.',
      AI_QUOTA_UNAVAILABLE: 'No se pudo confirmar capacidad de IA.',
      AI_PROVIDER_TIMEOUT:
        'El proveedor no respondió dentro del tiempo permitido.',
      AI_PROVIDER_UNAVAILABLE:
        'No se pudo contactar con el proveedor desde AI Service.',
    }
    throw new Error(
      known[data.codigo ?? data.code] ??
        (response.status === 422
          ? 'Revisa los datos de la conexión.'
          : 'No se pudo guardar o cargar la conexión.'),
    )
  }
  return response.json()
}
export async function fetchProviders(
  signal?: AbortSignal,
): Promise<ProviderConnection[]> {
  return z.array(providerSchema).parse(
    await checked(
      await fetch('/api/ai/providers', {
        credentials: 'same-origin',
        signal,
      }),
    ),
  )
}
export async function saveProvider(
  input: ProviderInput,
  id?: string,
): Promise<ProviderConnection> {
  const data = providerInputSchema.parse(input)
  const path = id
    ? `/api/ai/providers/${z.uuid().parse(id)}`
    : '/api/ai/providers'
  return providerSchema.parse(
    await checked(
      await fetch(path, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    ),
  )
}
export function modelChoiceKey(choice: {
  provider: string
  model: string
  provider_config_id?: string | null
  provider_revision?: number | null
}): string {
  return `${choice.provider_config_id || choice.provider}:${choice.provider_revision || 'env'}:${choice.model}`
}

const pricingSchema = z.strictObject({
  input_usd_per_million: z.number().finite().min(0).max(10000).nullable(),
  output_usd_per_million: z.number().finite().min(0).max(10000).nullable(),
  pricing_date: z.iso.date(),
  source: z.enum(['local', 'manual', 'litellm-bundled']),
})
export async function fetchModelPricing(provider: ProviderKind, model: string) {
  const query = new URLSearchParams({ provider, model })
  return pricingSchema.parse(
    await checked(
      await fetch(`/api/ai/providers/pricing?${query}`, {
        credentials: 'same-origin',
        signal: AbortSignal.timeout(8000),
      }),
    ),
  )
}

export const connectionProbeSchema = z.strictObject({
  provider: z.enum(providerKinds),
  base_url: z.url().max(500),
  api_key: z.string().max(4096),
  model: modelSchema.shape.model,
  config_id: z.uuid().optional(),
  expected_revision: z.number().int().positive().optional(),
})
export const probeResultSchema = z.strictObject({
  success: z.boolean(),
  code: z.string().min(1).max(64),
  latency_ms: z.number().finite().nonnegative(),
  tools_supported: z.boolean(),
  input_tokens: z.number().int().min(0).max(9000),
  output_tokens: z.number().int().min(0).max(9000),
})
export type ConnectionProbeResult = z.infer<typeof probeResultSchema>
export async function testProvider(
  input: z.infer<typeof connectionProbeSchema>,
): Promise<ConnectionProbeResult> {
  return probeResultSchema.parse(
    await checked(
      await fetch('/api/ai/providers/test', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(connectionProbeSchema.parse(input)),
        signal: AbortSignal.timeout(17000),
      }),
    ),
  )
}
export function probeMessage(result: ConnectionProbeResult): string {
  const messages: Record<string, string> = {
    AI_CONNECTION_OK: 'Conexión y llamada de herramienta verificadas.',
    AI_TOOLS_NOT_VERIFIED:
      'El modelo respondió, pero no confirmó una llamada de herramienta. Revisa su compatibilidad con RAG agentic.',
    AI_PROVIDER_AUTH_FAILED: 'El proveedor rechazó la API key o los permisos.',
    AI_MODEL_UNKNOWN: 'El proveedor no encontró este modelo.',
    AI_PROVIDER_RATE_LIMIT:
      'El proveedor rechazó la prueba por límite de cuota.',
    AI_PROVIDER_INPUT_UNSUPPORTED:
      'El proveedor rechazó el modelo, las herramientas o los parámetros de la prueba.',
    AI_PROVIDER_TIMEOUT: 'El proveedor no respondió dentro de 8 segundos.',
    AI_PROVIDER_UNAVAILABLE:
      'No se pudo completar la llamada al proveedor. Revisa su disponibilidad y la URL.',
  }
  return messages[result.code] || 'No se pudo verificar la conexión.'
}
