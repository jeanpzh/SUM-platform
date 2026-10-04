import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  useWorkspace,
  useWorkspaceApi,
} from '#/components/admin/workspace-provider'
import { checkConnection } from '#/lib/pdf-ingestion/backend'
import {
  administrationRequest,
  bulkReindexSchema,
  embeddingProfileSchema,
} from '#/lib/pdf-ingestion/administration'
import type { EmbeddingConfiguration } from '#/lib/pdf-ingestion/administration'

const initialProfile: EmbeddingConfiguration = {
  provider: 'tei',
  model: 'intfloat/multilingual-e5-base',
  revision: 'd13f1b27baf31030b7fd040960d60d909913633f',
  dimension: 768,
  max_tokens: 512,
}

export function useEmbeddingAdministration() {
  const store = useWorkspaceApi()
  const profile = useWorkspace((current) => current.embeddingProfile)
  const ready = useWorkspace((current) => current.backendStatus === 'ready')
  const stale = useWorkspace((current) => current.staleEmbeddingDocuments)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const form = useForm<EmbeddingConfiguration>({
    resolver: zodResolver(embeddingProfileSchema),
    values: profile ? embeddingProfileSchema.parse(profile) : initialProfile,
    resetOptions: { keepDirtyValues: true },
  })
  async function refreshCapabilities() {
    const info = await checkConnection()
    store.setState({
      embeddingProfile: info.embedding_profile,
      staleEmbeddingDocuments: info.stale_documents,
      backendRevision: store.getState().backendRevision + 1,
    })
  }
  const save = form.handleSubmit(async (values) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const saved = embeddingProfileSchema.parse(
        await administrationRequest('admin/embedding-profile', 'PATCH', values),
      )
      form.reset(saved)
      store.setState({ embeddingProfile: saved })
      setNotice(
        'Modelo guardado en el backend. Se aplicará a los nuevos trabajos.',
      )
      await refreshCapabilities()
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No se pudo guardar el modelo.',
      )
    } finally {
      setBusy(false)
    }
  })
  async function reindexStale() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = bulkReindexSchema.parse(
        await administrationRequest('admin/reindex-stale', 'POST'),
      )
      setNotice(
        `${result.total} documentos enviados a reindexación. Puedes seguirlos en Trabajos.`,
      )
      await refreshCapabilities()
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No se pudo iniciar la reindexación.',
      )
    } finally {
      setBusy(false)
    }
  }
  return { form, save, reindexStale, ready, stale, busy, error, notice }
}
