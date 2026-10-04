import { useEffect, useState } from 'react'
import { fetchPublishedChunks } from '#/lib/pdf-ingestion/library'
import type {
  PublishedDocument,
  PublishedChunks,
} from '#/lib/pdf-ingestion/library'

export function usePublishedChunks(document: PublishedDocument) {
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<PublishedChunks | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    void fetchPublishedChunks(document, offset, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setData(result)
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted)
          setError(
            cause instanceof Error
              ? cause.message
              : 'No se pudieron leer los fragmentos.',
          )
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [document, offset, revision])
  return {
    data,
    loading,
    error,
    offset,
    setOffset,
    retry: () => setRevision((value) => value + 1),
  }
}
