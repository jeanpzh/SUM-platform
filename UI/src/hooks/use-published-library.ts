import { useEffect, useState } from 'react'
import { useWorkspace } from '#/components/admin/workspace-provider'
import { fetchPublishedDocuments } from '#/lib/pdf-ingestion/library'
import type { PublishedCatalogue } from '#/lib/pdf-ingestion/library'

export function usePublishedLibrary() {
  const ready = useWorkspace(
    (store) => store.loaded && store.backendStatus === 'ready',
  )
  const publications = useWorkspace((store) =>
    store.state.jobs
      .filter((job) => job.source === 'backend' && job.status === 'published')
      .map((job) => job.id)
      .join(','),
  )
  const backendRevision = useWorkspace((store) => store.backendRevision)
  const [query, setQueryValue] = useState('')
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<PublishedCatalogue | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query)
      setOffset(0)
    }, 300)
    return () => clearTimeout(timer)
  }, [query])
  useEffect(() => {
    if (!ready) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    async function load() {
      setLoading(true)
      try {
        const result = await fetchPublishedDocuments(
          search,
          offset,
          controller.signal,
        )
        if (!controller.signal.aborted) {
          setData(result)
          setError('')
        }
      } catch (cause) {
        if (!controller.signal.aborted)
          setError(
            cause instanceof Error
              ? cause.message
              : 'No se pudo cargar la biblioteca.',
          )
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
          timer = setTimeout(() => {
            void load()
          }, 10000)
        }
      }
    }
    void load()
    const refresh = () => {
      if (document.visibilityState === 'visible')
        setRevision((value) => value + 1)
    }
    document.addEventListener('visibilitychange', refresh)
    return () => {
      controller.abort()
      clearTimeout(timer)
      document.removeEventListener('visibilitychange', refresh)
    }
  }, [ready, search, offset, revision, publications, backendRevision])
  return {
    data,
    loading,
    error,
    ready,
    query,
    setQuery: setQueryValue,
    offset,
    setOffset,
    refresh: () => setRevision((value) => value + 1),
  }
}
