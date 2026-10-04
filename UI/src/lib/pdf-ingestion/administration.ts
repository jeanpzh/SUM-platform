import * as z from 'zod'
import { backendJobSchema } from './backend'

export const embeddingProfileSchema = z.object({
  provider: z.enum(['tei', 'ollama', 'openai']),
  model: z.string().trim().min(1, 'Indica el modelo.').max(200),
  revision: z.string().trim().min(1, 'Indica la revisión.').max(200),
  dimension: z.literal(768),
  max_tokens: z.number().int().min(64).max(8192),
})
export type EmbeddingConfiguration = z.infer<typeof embeddingProfileSchema>

export async function administrationRequest(
  path: string,
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  body?: unknown,
): Promise<unknown> {
  const response = await fetch('/api/indexing/' + path, {
    method,
    headers:
      body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data: unknown = await response.json()
  if (!response.ok) {
    const error = z.object({ mensaje: z.string() }).safeParse(data)
    throw new Error(
      error.success ? error.data.mensaje : 'No se pudo completar la operación.',
    )
  }
  return data
}

export async function reindexDocument(documentId: string) {
  return backendJobSchema.parse(
    await administrationRequest('documents/' + documentId + '/reindex', 'POST'),
  )
}

export const bulkReindexSchema = z.object({
  trabajos: z.array(backendJobSchema),
  total: z.number().int().nonnegative(),
})

export async function deleteDevelopmentDocument(
  documentId: string,
  title: string,
) {
  return z
    .object({ limpieza_pendiente: z.boolean() })
    .parse(
      await administrationRequest('documents/' + documentId, 'DELETE', {
        confirmar_titulo: title,
      }),
    )
}
