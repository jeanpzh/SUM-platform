import * as z from 'zod'
import { jobTimingsSchema } from './timings'
import { toBackendMetadata } from './schema'
import type { SourceMetadata } from './schema'
import type { IndexingJob, JobStatus } from '#/data/pdf-ingestion-jobs'

export const backendJobSchema = z.object({
  trabajo_id: z.uuid(),
  documento_id: z.uuid(),
  version_id: z.uuid(),
  estado: z.enum([
    'en_cola',
    'procesando',
    'completado',
    'fallido',
    'cancelado',
  ]),
  etapa: z
    .enum([
      'validando',
      'extrayendo',
      'fragmentando',
      'generando_vectores',
      'guardando',
      'publicando',
    ])
    .nullable(),
  mensaje: z.string(),
  secuencia: z.number().int().nonnegative(),
  progreso: z.object({
    paginas: z.number().int().nonnegative().optional(),
    fragmentos: z.number().int().nonnegative().optional(),
    vectores: z.number().int().nonnegative().optional(),
  }),
  tiempos: jobTimingsSchema.optional(),
  actualizado_en: z.string().optional(),
  codigo_error: z.string().nullable().optional(),
})
export type BackendJob = z.infer<typeof backendJobSchema>
const statuses: Record<BackendJob['estado'], JobStatus> = {
  en_cola: 'queued',
  procesando: 'processing',
  completado: 'published',
  fallido: 'failed',
  cancelado: 'cancelled',
}
const stages = [
  'validando',
  'extrayendo',
  'fragmentando',
  'generando_vectores',
  'guardando',
  'publicando',
]

export function mapBackendJob(
  data: BackendJob,
  previous: IndexingJob,
): IndexingJob {
  return {
    ...previous,
    id: data.trabajo_id,
    documentId: data.documento_id,
    versionId: data.version_id,
    source: 'backend',
    status: statuses[data.estado],
    stage: data.etapa ? stages.indexOf(data.etapa) : undefined,
    progress: undefined,
    counts: data.progreso,
    timings: data.tiempos,
    sequence: data.secuencia,
    errorCode: data.codigo_error ?? undefined,
    updatedAt: data.actualizado_en ?? 'Ahora',
    note: data.mensaje,
  }
}

function message(data: unknown, fallback: string) {
  const parsed = z.object({ mensaje: z.string() }).safeParse(data)
  return parsed.success ? parsed.data.mensaje : fallback
}

export async function fetchJob(
  path: string,
  method = 'GET',
  signal?: AbortSignal,
) {
  const response = await fetch('/api/indexing/' + path, {
    method,
    signal,
  })
  const data: unknown = await response.json()
  if (!response.ok)
    throw new Error(message(data, 'No se pudo consultar el servicio.'))
  return backendJobSchema.parse(data)
}

export async function checkConnection(signal?: AbortSignal) {
  const response = await fetch('/api/indexing/connection', {
    signal,
  })
  const data: unknown = await response.json()
  if (!response.ok)
    throw new Error(message(data, 'No se pudo conectar al backend.'))
  const capabilities = await fetch('/api/indexing/capabilities', { signal })
  if (!capabilities.ok)
    throw new Error(
      message(
        await capabilities.clone().json(),
        'No se pudo consultar la configuración del backend.',
      ),
    )
  const info = z
    .object({
      env_mode: z.enum(['DEVELOPMENT', 'PRODUCTION']),
      embedding_profile: z.object({
        provider: z.enum(['tei', 'ollama', 'openai']),
        model: z.string(),
        revision: z.string(),
        dimension: z.number().int(),
        max_tokens: z.number().int(),
      }),
      stale_documents: z.number().int().nonnegative(),
    })
    .parse(await capabilities.json())
  return info
}

export const backendHistorySchema = z.object({
  trabajos: z.array(
    backendJobSchema.extend({
      titulo: z.string(),
      archivo: z.string(),
      metadatos: z.record(z.string(), z.unknown()),
    }),
  ),
  total: z.number().int().nonnegative(),
  limite: z.number().int(),
  offset: z.number().int(),
  estados: z.object({
    queued: z.number().int(),
    processing: z.number().int(),
    published: z.number().int(),
    failed: z.number().int(),
    cancelled: z.number().int(),
  }),
})
export async function fetchJobHistory(
  status: string,
  offset: number,
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({ limit: '25', offset: String(offset) })
  if (status !== 'all') query.set('status', status)
  const response = await fetch('/api/indexing/history?' + query, { signal })
  const data: unknown = await response.json()
  if (!response.ok)
    throw new Error(message(data, 'No se pudo consultar el historial.'))
  return backendHistorySchema.parse(data)
}

export function uploadPdf({
  file,
  title,
  metadata,
  key,
  documentId,
  onProgress,
}: {
  file: File
  title: string
  metadata: SourceMetadata
  key: string
  documentId?: string
  onProgress?: (percent: number) => void
}): Promise<BackendJob> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open(
      'POST',
      '/api/indexing/documents' +
        (documentId ? '/' + encodeURIComponent(documentId) + '/versions' : ''),
    )
    request.timeout = 120000
    request.setRequestHeader('Idempotency-Key', key)
    request.upload.onprogress = (event) => {
      if (event.lengthComputable)
        onProgress?.(Math.round((event.loaded / event.total) * 100))
    }
    request.onerror = () =>
      reject(
        new Error(
          'No se pudo confirmar la carga. Reintenta para consultar la misma solicitud.',
        ),
      )
    request.ontimeout = () =>
      reject(
        new Error(
          'La carga agotó el tiempo de espera. Reintenta con la misma solicitud.',
        ),
      )
    request.onload = () => {
      try {
        const data: unknown = JSON.parse(request.responseText)
        if (request.status < 200 || request.status >= 300)
          reject(new Error(message(data, 'La carga fue rechazada.')))
        else resolve(backendJobSchema.parse(data))
      } catch {
        reject(new Error('El servicio devolvió una respuesta no compatible.'))
      }
    }
    const body = new FormData()
    body.append('archivo', file, file.name)
    body.append('metadatos', JSON.stringify(toBackendMetadata(title, metadata)))
    request.send(body)
  })
}
