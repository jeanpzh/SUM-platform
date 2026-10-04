import { useMemo, useState } from 'react'
import {
  useWorkspace,
  useWorkspaceApi,
} from '#/components/admin/workspace-provider'
import { fetchJob, mapBackendJob, uploadPdf } from '#/lib/pdf-ingestion/backend'
import { validatePdf } from '#/lib/pdf-ingestion/files'
import type { IndexingJob, JobFilter } from '#/data/pdf-ingestion-jobs'
import type { SourceMetadata } from '#/lib/pdf-ingestion/schema'

export function useIndexingJobs() {
  const jobs = useWorkspace((store) => store.state.jobs)
  const dispatch = useWorkspace((store) => store.dispatch)
  const store = useWorkspaceApi()
  const [actionError, setActionError] = useState('')
  const [busyIds, setBusyIds] = useState<string[]>([])
  const [filter, setFilter] = useState<JobFilter>('all')

  const visibleJobs = useMemo(
    () =>
      jobs.filter((job) => {
        if (filter === 'active')
          return job.status === 'queued' || job.status === 'processing'
        if (filter === 'published') return job.status === 'published'
        if (filter === 'failed') return job.status === 'failed'
        if (filter === 'cancelled') return job.status === 'cancelled'
        return true
      }),
    [filter, jobs],
  )

  async function enqueue(
    file: File,
    metadata: SourceMetadata,
    title = file.name.replace(/\.pdf$/i, ''),
    key: string = crypto.randomUUID(),
    onProgress?: (percent: number) => void,
    documentId?: string,
  ) {
    const data = await uploadPdf({
      file,
      metadata,
      title,
      key,
      onProgress,
      documentId,
    })
    const job: IndexingJob = {
      id: data.trabajo_id,
      fileName: file.name,
      originUrl: metadata.originUrl,
      resolution: metadata.resolution,
      applicability: metadata.documentType,
      sourceMetadata: metadata,
      title,
      status: 'queued',
      stage: 0,
      updatedAt: 'Ahora',
      note: data.mensaje,
    }

    const mapped = mapBackendJob(data, job)
    dispatch({ type: 'upsert-job', job: mapped })
    store.setState((current) => ({
      originals: new Map(current.originals).set(mapped.id, file),
      backendRevision: current.backendRevision + 1,
    }))
    setFilter('all')
    return mapped
  }

  async function retry(jobId: string, original?: File) {
    setActionError('')
    const job = store.getState().state.jobs.find((item) => item.id === jobId)
    if (!job || !['failed', 'cancelled'].includes(job.status)) return
    if (job.source !== 'backend') {
      dispatch({ type: 'retry', id: jobId })
      return
    }
    const previousRequest = store.getState().retryRequests.get(jobId)
    const file =
      previousRequest?.file ?? original ?? store.getState().originals.get(jobId)
    if (!file || !job.sourceMetadata) {
      setActionError(
        'Adjunta nuevamente el archivo original para crear una nueva versión.',
      )
      return
    }
    setBusyIds((ids) => [...ids, jobId])
    try {
      const invalid = await validatePdf(file)
      if (invalid) throw new Error(invalid)
      const request = previousRequest ?? { file, key: crypto.randomUUID() }
      store.setState((current) => ({
        retryRequests: new Map(current.retryRequests).set(jobId, request),
      }))
      await enqueue(
        request.file,
        job.sourceMetadata,
        job.title,
        request.key,
        undefined,
        job.documentId,
      )
      store.setState((current) => {
        const requests = new Map(current.retryRequests)
        requests.delete(jobId)
        return { retryRequests: requests }
      })
    } catch (cause) {
      setActionError(
        cause instanceof Error ? cause.message : 'No se pudo reintentar.',
      )
    } finally {
      setBusyIds((ids) => ids.filter((id) => id !== jobId))
    }
  }

  async function cancel(jobId: string) {
    setActionError('')
    const job = store.getState().state.jobs.find((item) => item.id === jobId)
    if (!job) return
    if (job.source !== 'backend') {
      dispatch({ type: 'cancel', id: jobId })
      return
    }
    setBusyIds((ids) => [...ids, jobId])
    try {
      const data = await fetchJob('jobs/' + jobId + '/cancel', 'POST')
      dispatch({ type: 'upsert-job', job: mapBackendJob(data, job) })
      store.setState((current) => ({
        backendRevision: current.backendRevision + 1,
      }))
    } catch (cause) {
      setActionError(
        cause instanceof Error ? cause.message : 'No se pudo cancelar.',
      )
    } finally {
      setBusyIds((ids) => ids.filter((id) => id !== jobId))
    }
  }

  return {
    jobs: visibleJobs,
    allJobs: jobs,
    filter,
    setFilter,
    enqueue,
    retry,
    cancel,
    actionError,
    busyIds,
  }
}
