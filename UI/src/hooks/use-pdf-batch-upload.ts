import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { usePdfFileSelection } from './use-pdf-file-selection'
import { useIndexingJobs } from './use-indexing-jobs'
import { useWorkspace } from '#/components/admin/workspace-provider'
import {
  defaultSourceMetadata,
  sourceMetadataSchema,
} from '#/lib/pdf-ingestion/schema'
import type {
  SourceMetadata,
  SourceMetadataInput,
} from '#/lib/pdf-ingestion/schema'
import { runConcurrent } from '#/lib/pdf-ingestion/files'

export function usePdfBatchUpload() {
  const selection = usePdfFileSelection()
  const jobs = useIndexingJobs()
  const connected = useWorkspace((store) => store.backendStatus === 'ready')
  const [confirmation, setConfirmation] = useState('')
  const form = useForm<SourceMetadataInput, unknown, SourceMetadata>({
    resolver: zodResolver(sourceMetadataSchema),
    defaultValues: defaultSourceMetadata,
    mode: 'onTouched',
  })
  const pending = selection.entries.filter(
    (entry) =>
      entry.validation === 'ready' && ['idle', 'error'].includes(entry.upload),
  )
  const checking = selection.entries.some(
    (entry) => entry.validation === 'checking',
  )
  const submit = form.handleSubmit(async (metadata) => {
    if (!connected || checking || !pending.length) return
    setConfirmation('')
    let accepted = 0
    let failed = 0
    const candidates = pending.filter((entry) => {
      if (!entry.title.trim() || entry.title.trim().length > 300) {
        selection.patch(entry.id, {
          error: 'El título debe tener entre 1 y 300 caracteres.',
        })
        failed++
        return false
      }
      selection.patch(entry.id, { upload: 'waiting', error: '' })
      return true
    })
    await runConcurrent(candidates, 3, async (entry) => {
      const request = entry.request ?? {
        key: crypto.randomUUID(),
        title: entry.title.trim(),
        metadata,
      }
      selection.patch(entry.id, { upload: 'uploading', request, progress: 0 })
      try {
        const job = await jobs.enqueue(
          entry.file,
          request.metadata,
          request.title,
          request.key,
          (progress) => selection.patch(entry.id, { progress }),
        )
        selection.patch(entry.id, {
          upload: 'accepted',
          progress: 100,
          jobId: job.id,
        })
        accepted++
      } catch (cause) {
        selection.patch(entry.id, {
          upload: 'error',
          error:
            cause instanceof Error
              ? cause.message
              : 'No se pudo cargar este PDF.',
        })
        failed++
      }
    })
    setConfirmation(
      `${accepted} PDF aceptados por el backend.${failed ? ` ${failed} requieren revisión o reintento.` : ''}`,
    )
  })
  return { selection, form, submit, confirmation, pending, checking, connected }
}
