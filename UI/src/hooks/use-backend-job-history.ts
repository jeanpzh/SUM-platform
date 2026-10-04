import { useEffect, useState } from 'react'
import { useStore } from 'zustand'
import type { WorkspaceStoreApi } from '#/stores/admin-workspace-store'
import type { IndexingJob, JobFilter } from '#/data/pdf-ingestion-jobs'
import { fetchJobHistory, mapBackendJob } from '#/lib/pdf-ingestion/backend'
import { sourceMetadataSchema } from '#/lib/pdf-ingestion/schema'

const statusForBackend: Record<Exclude<JobFilter, 'all'>, string> = {
  active: 'active',
  published: 'published',
  failed: 'failed',
  cancelled: 'cancelled',
}
export function useBackendJobHistory(
  store: WorkspaceStoreApi,
  filter: JobFilter,
) {
  const ready = useStore(
    store,
    (current) => current.loaded && current.backendStatus === 'ready',
  )
  const [jobs, setJobs] = useState<IndexingJob[]>([])
  const backendRevision = useStore(store, (current) => current.backendRevision)
  const [counts, setCounts] = useState({
    queued: 0,
    processing: 0,
    published: 0,
    failed: 0,
    cancelled: 0,
  })
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    setOffset(0)
  }, [filter])
  useEffect(() => {
    if (!ready) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    const status =
      filter === 'active'
        ? 'active'
        : filter === 'all'
          ? 'all'
          : statusForBackend[filter]
    async function refresh() {
      setLoading(true)
      try {
        const result = await fetchJobHistory(status, offset, controller.signal)
        if (controller.signal.aborted) return
        const current = store.getState().state.jobs
        const mapped = result.trabajos.map((row) => {
          const metadata = row.metadatos
          const parsed = sourceMetadataSchema.parse({
            originUrl: metadata.fuente_url ?? '',
            resolution: metadata.codigo_documento ?? '',
            documentType: metadata.tipo_documento,
            priority: metadata.prioridad ?? 'normal',
            testDocument: metadata.es_prueba === true,
          })
          const title = row.titulo || 'Documento institucional'
          const previous = current.find((job) => job.id === row.trabajo_id) || {
            id: row.trabajo_id,
            fileName: row.archivo || title + '.pdf',
            originUrl: parsed.originUrl,
            resolution: parsed.resolution,
            applicability: parsed.documentType,
            status: 'queued' as const,
            updatedAt: row.actualizado_en || '',
            title,
            sourceMetadata: parsed,
          }
          return mapBackendJob(row, previous)
        })
        setJobs(mapped)
        setCounts(result.estados)
        setTotal(result.total)
        setError('')
        for (const job of mapped)
          store.getState().dispatch({ type: 'upsert-job', job })
      } catch (cause) {
        if (!controller.signal.aborted)
          setError(
            cause instanceof Error
              ? cause.message
              : 'No se pudo consultar el historial.',
          )
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
          const active = countsActive(store)
          timer = setTimeout(
            () => setRevision((value) => value + 1),
            active ? 2000 : 15000,
          )
        }
      }
    }
    void refresh()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [store, ready, filter, offset, revision, backendRevision])
  return {
    jobs,
    counts,
    total,
    offset,
    setOffset,
    loading,
    error,
    refresh: () => setRevision((value) => value + 1),
    ready,
  }
}
function countsActive(store: WorkspaceStoreApi) {
  return store
    .getState()
    .state.jobs.some(
      (job) =>
        job.source === 'backend' &&
        ['queued', 'processing'].includes(job.status),
    )
}
