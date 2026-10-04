import { useState } from 'react'
import { useWorkspace } from '#/components/admin/workspace-provider'
import { retrieveChunks } from '#/lib/admin-workspace/retrieval'

export function useRetrieval() {
  const documents = useWorkspace((store) => store.state.documents)
  const settings = useWorkspace((store) => store.state.settings)
  const [query, setQuery] = useState('')
  const [documentId, setDocumentId] = useState('all')
  const [submitted, setSubmitted] = useState('')
  const [error, setError] = useState('')

  function search(value = query) {
    const trimmed = value.trim()
    if (trimmed.length < 3) {
      setError('Escribe al menos 3 caracteres.')
      return
    }
    setError('')
    setQuery(trimmed)
    setSubmitted(trimmed)
  }

  // Recompute submitted results when the corpus, scope or retrieval profile changes.
  const currentHits = submitted
    ? retrieveChunks(submitted, documents, settings, documentId)
    : []

  return {
    query,
    setQuery,
    documentId,
    setDocumentId,
    submitted,
    hits: currentHits,
    search,
    error,
    documents,
    settings,
  }
}
