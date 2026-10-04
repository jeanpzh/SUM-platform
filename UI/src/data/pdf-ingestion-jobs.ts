import type { JobTimings } from '#/lib/pdf-ingestion/timings'
import type { SourceMetadata } from '#/lib/pdf-ingestion/schema'

export type JobStatus =
  'queued' | 'processing' | 'published' | 'failed' | 'cancelled'

export type IndexingJob = {
  id: string
  fileName: string
  originUrl: string
  resolution: string
  applicability: string
  status: JobStatus
  updatedAt: string
  progress?: number
  note?: string
  stage?: number
  documentId?: string
  versionId?: string
  source?: 'backend' | 'sample'
  sequence?: number
  counts?: { paginas?: number; fragmentos?: number; vectores?: number }
  errorCode?: string
  sourceMetadata?: SourceMetadata
  timings?: JobTimings
  title?: string
}

export type JobFilter = 'all' | 'active' | 'published' | 'failed' | 'cancelled'

export const initialIndexingJobs: IndexingJob[] = [
  {
    id: 'job-current',
    fileName: 'Reglamento-Matricula-Pregrado-2026.pdf',
    originUrl: 'https://sum.unmsm.edu.pe',
    resolution: 'RR / 2026',
    applicability: 'Por verificar',
    status: 'processing',
    updatedAt: 'Hoy, 10:24',
    progress: 62,
    stage: 3,
    note: 'Extracción completa · creando segmentos para búsqueda.',
  },
  {
    id: 'job-published',
    fileName: 'Cronograma-Pregrado-2026.pdf',
    originUrl: 'https://sum.unmsm.edu.pe',
    resolution: '2026',
    applicability: 'Pregrado',
    status: 'published',
    updatedAt: 'Hoy, 08:15',
    note: 'Listo para consultas con referencias a la página de origen.',
  },
  {
    id: 'job-failed',
    fileName: 'Directiva-Rectificacion-Notas.pdf',
    originUrl: 'https://sistemas.unmsm.edu.pe',
    resolution: 'Directiva / 2024',
    applicability: 'Pregrado',
    status: 'failed',
    updatedAt: 'Ayer, 16:42',
    note: 'La versión publicada anterior sigue disponible.',
  },
]
