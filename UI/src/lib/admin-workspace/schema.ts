import * as z from 'zod'
import { jobTimingsSchema } from '#/lib/pdf-ingestion/timings'
import { sourceMetadataSchema } from '#/lib/pdf-ingestion/schema'

export const EMBEDDING_PROFILE = {
  model: 'intfloat/multilingual-e5-base',
  dimensions: 768,
  maxTokens: 512,
} as const

export const settingsSchema = z
  .object({
    workspaceName: z
      .string()
      .trim()
      .min(3, 'Escribe al menos 3 caracteres.')
      .max(80),
    chunkSize: z
      .number()
      .int()
      .min(64, 'El mínimo es 64.')
      .max(480, 'El máximo es 480.'),
    overlap: z.number().int().min(0).max(120),
    topK: z.number().int().min(1).max(10),
    minMatch: z.number().min(0).max(1),
    embeddingBatchSize: z.number().int().min(1).max(64),
    extractionConcurrency: z.number().int().min(1).max(8),
    pageBatchSize: z.number().int().min(1).max(100),
  })
  .refine((settings) => settings.overlap < settings.chunkSize, {
    path: ['overlap'],
    message: 'El solapamiento debe ser menor que el tamaño del fragmento.',
  })

export const chunkSchema = z.object({
  id: z.string().min(1).max(160),
  page: z.number().int().min(1).max(2000),
  text: z.string().trim().min(1).max(20000),
  vector: z.array(z.number()).length(EMBEDDING_PROFILE.dimensions).optional(),
})

export const corpusDocumentSchema = z.object({
  id: z.string().min(1).max(160),
  title: z.string().trim().min(1).max(300),
  fileName: z.string().max(300),
  source: z.string().max(2048),
  category: z.string().max(80),
  status: z.enum(['published', 'archived']),
  sample: z.boolean(),
  indexedChunkSize: z.number().int().min(1),
  indexedOverlap: z.number().int().min(0),
  chunks: z.array(chunkSchema).min(1).max(2000),
})

const jobSchema = z.object({
  id: z.string(),
  fileName: z.string(),
  originUrl: z.string(),
  resolution: z.string(),
  applicability: z.string(),
  status: z.enum(['queued', 'processing', 'published', 'failed', 'cancelled']),
  updatedAt: z.string(),
  progress: z.number().optional(),
  note: z.string().optional(),
  stage: z.number().int().min(0).max(5).optional(),
  documentId: z.string().optional(),
  versionId: z.string().optional(),
  source: z.enum(['backend', 'sample']).optional(),
  sequence: z.number().int().nonnegative().optional(),
  counts: z
    .object({
      paginas: z.number().int().nonnegative().optional(),
      fragmentos: z.number().int().nonnegative().optional(),
      vectores: z.number().int().nonnegative().optional(),
    })
    .optional(),
  errorCode: z.string().optional(),
  sourceMetadata: sourceMetadataSchema.optional(),
  title: z.string().optional(),
  timings: jobTimingsSchema.optional(),
})

export const workspaceSchema = z.object({
  version: z.literal(1),
  settings: settingsSchema,
  documents: z.array(corpusDocumentSchema).max(200),
  jobs: z.array(jobSchema).max(500),
})

export type WorkspaceSettings = z.infer<typeof settingsSchema>
export type CorpusDocument = z.infer<typeof corpusDocumentSchema>
export type CorpusChunk = z.infer<typeof chunkSchema>
export type WorkspaceState = z.infer<typeof workspaceSchema>

export const defaultSettings: WorkspaceSettings = {
  workspaceName: 'FISI · UNMSM',
  chunkSize: 384,
  overlap: 48,
  topK: 4,
  minMatch: 0.2,
  embeddingBatchSize: 32,
  extractionConcurrency: 2,
  pageBatchSize: 10,
}

export const pipelineStages = [
  'Validación',
  'Extracción',
  'Fragmentación',
  'Vectores',
  'Almacenamiento',
  'Publicación',
] as const
