import { useState } from 'react'
import { useWorkspaceApi } from '#/components/admin/workspace-provider'
import {
  deleteDevelopmentDocument,
  reindexDocument,
} from '#/lib/pdf-ingestion/administration'
import { mapBackendJob } from '#/lib/pdf-ingestion/backend'
import { defaultSourceMetadata } from '#/lib/pdf-ingestion/schema'
import type { SourceMetadata } from '#/lib/pdf-ingestion/schema'

export function useDocumentAdministration(
  documentId: string,
  title: string,
  metadata?: SourceMetadata,
) {
  const store = useWorkspaceApi()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  async function run(operation: () => Promise<void>) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await operation()
      store.setState((current) => ({
        backendRevision: current.backendRevision + 1,
      }))
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No se pudo completar la operación.',
      )
    } finally {
      setBusy(false)
    }
  }
  async function reindex() {
    await run(async () => {
      const data = await reindexDocument(documentId)
      const sourceMetadata = metadata ?? defaultSourceMetadata
      store.getState().dispatch({
        type: 'upsert-job',
        job: mapBackendJob(data, {
          id: data.trabajo_id,
          title,
          fileName: title + '.pdf',
          originUrl: sourceMetadata.originUrl,
          resolution: sourceMetadata.resolution,
          applicability: sourceMetadata.documentType,
          sourceMetadata,
          status: 'queued',
          updatedAt: '',
        }),
      })
      setNotice('Reindexación en cola. Consulta su avance en Trabajos.')
    })
  }
  async function remove(confirmation: string) {
    await run(async () => {
      const result = await deleteDevelopmentDocument(documentId, confirmation)
      store.getState().dispatch({ type: 'remove-backend-document', documentId })
      setNotice(
        result.limpieza_pendiente
          ? 'Registro eliminado. El backend reintentará la limpieza de archivos pendiente.'
          : 'Registro y archivos eliminados del backend.',
      )
    })
  }
  return { reindex, remove, busy, error, notice }
}
