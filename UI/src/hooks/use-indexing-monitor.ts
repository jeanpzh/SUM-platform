import { useEffect } from 'react'
import { useStore } from 'zustand'
import { fetchJob, mapBackendJob } from '#/lib/pdf-ingestion/backend'
import { runConcurrent } from '#/lib/pdf-ingestion/files'
import type { WorkspaceStoreApi } from '#/stores/admin-workspace-store'

export function useIndexingMonitor(store: WorkspaceStoreApi) {
  const ready = useStore(
    store,
    (current) => current.backendStatus === 'ready' && current.loaded,
  )
  useEffect(() => {
    if (!ready) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    const refreshed = new Set<string>()
    async function refresh() {
      const jobs = store
        .getState()
        .state.jobs.filter(
          (job) =>
            job.source === 'backend' &&
            (['queued', 'processing'].includes(job.status) ||
              !refreshed.has(job.id) ||
              (job.timings?.intentos.some(
                (attempt) => attempt.resultado === 'en_curso',
              ) &&
                Date.now() - Date.parse(job.updatedAt) < 60000)),
        )
      await runConcurrent(jobs, 3, async (job) => {
        try {
          const data = await fetchJob(
            'jobs/' + job.id,
            'GET',
            controller.signal,
          )
          if (controller.signal.aborted) return
          refreshed.add(job.id)
          if (data.secuencia >= (job.sequence ?? -1))
            store
              .getState()
              .dispatch({ type: 'upsert-job', job: mapBackendJob(data, job) })
          if (store.getState().monitoringErrors[job.id])
            store.setState((current) => ({
              monitoringErrors: { ...current.monitoringErrors, [job.id]: '' },
            }))
        } catch (cause) {
          if (!controller.signal.aborted)
            store.setState((current) => ({
              monitoringErrors: {
                ...current.monitoringErrors,
                [job.id]:
                  cause instanceof Error
                    ? cause.message
                    : 'No se pudo actualizar el trabajo.',
              },
            }))
        }
      })
      if (!controller.signal.aborted)
        timer = setTimeout(() => {
          void refresh()
        }, 2000)
    }
    void refresh()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [store, ready])
}
