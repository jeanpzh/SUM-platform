import { useMemo, useState } from 'react'
import { useWorkspace } from '#/components/admin/workspace-provider'
import type { IndexingJob } from '#/data/pdf-ingestion-jobs'

export function useCorpusLibrary() {
  const documents = useWorkspace((store) => store.state.documents)
  const settings = useWorkspace((store) => store.state.settings)
  const jobs = useWorkspace((store) => store.state.jobs)
  const dispatch = useWorkspace((store) => store.dispatch)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [notice, setNotice] = useState('')

  const visibleDocuments = useMemo(
    () =>
      documents.filter(
        (doc) =>
          (status === 'all' || doc.status === status) &&
          (doc.title + ' ' + doc.category + ' ' + doc.source)
            .toLocaleLowerCase()
            .includes(query.toLocaleLowerCase()),
      ),
    [documents, query, status],
  )
  const selectedDocuments = documents.filter((doc) =>
    selectedIds.includes(doc.id),
  )
  const staleDocuments = documents.filter(
    (doc) =>
      doc.indexedChunkSize !== settings.chunkSize ||
      doc.indexedOverlap !== settings.overlap,
  )

  function toggleSelection(id: string) {
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    )
  }

  function selectVisible() {
    const ids = visibleDocuments.map((doc) => doc.id)
    const allSelected = ids.every((id) => selectedIds.includes(id))
    setSelectedIds((current) =>
      allSelected
        ? current.filter((id) => !ids.includes(id))
        : [...new Set([...current, ...ids])],
    )
  }

  function removeSelected() {
    dispatch({ type: 'remove', ids: selectedDocuments.map((doc) => doc.id) })
    setSelectedIds([])
    setNotice('Los documentos seleccionados se eliminaron del espacio local.')
  }

  function requestReindex(ids: string[]) {
    const newJobs: IndexingJob[] = documents
      .filter(
        (doc) =>
          ids.includes(doc.id) &&
          !jobs.some(
            (job) =>
              job.documentId === doc.id &&
              ['queued', 'processing'].includes(job.status),
          ),
      )
      .map((doc) => ({
        id: crypto.randomUUID(),
        documentId: doc.id,
        fileName: doc.fileName,
        originUrl: doc.source,
        resolution: 'Reindexación',
        applicability: doc.category,
        status: 'queued',
        stage: 0,
        updatedAt: 'Ahora',
        note: 'Solicitud local. El servicio de indexación debe ejecutar el nuevo perfil.',
      }))
    dispatch({ type: 'reindex', jobs: newJobs })
    setNotice(
      newJobs.length > 0
        ? String(newJobs.length) +
            ' solicitudes locales agregadas. La generación publicada se conserva.'
        : 'Estos documentos ya tienen una solicitud en curso.',
    )
  }

  return {
    documents,
    settings,
    visibleDocuments,
    selectedDocuments,
    selectedIds,
    staleDocuments,
    query,
    setQuery,
    status,
    setStatus,
    toggleSelection,
    selectVisible,
    removeSelected,
    requestReindex,
    notice,
    archive: (id: string) => dispatch({ type: 'archive', id }),
  }
}
