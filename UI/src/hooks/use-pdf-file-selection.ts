import { useRef, useState } from 'react'
import {
  fileIdentity,
  MAX_BATCH_FILES,
  runConcurrent,
  validatePdf,
} from '#/lib/pdf-ingestion/files'
import type { SourceMetadata } from '#/lib/pdf-ingestion/schema'

export type PdfSelection = {
  id: string
  file: File
  title: string
  validation: 'checking' | 'ready' | 'invalid'
  upload: 'idle' | 'waiting' | 'uploading' | 'accepted' | 'error'
  error: string
  progress?: number
  jobId?: string
  request?: { key: string; title: string; metadata: SourceMetadata }
}

export function usePdfFileSelection() {
  const [entries, setEntries] = useState<PdfSelection[]>([])
  const current = useRef(entries)
  const [notice, setNotice] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  function update(updater: (items: PdfSelection[]) => PdfSelection[]) {
    current.current = updater(current.current)
    setEntries(current.current)
  }
  function patch(id: string, values: Partial<PdfSelection>) {
    update((items) =>
      items.map((entry) => (entry.id === id ? { ...entry, ...values } : entry)),
    )
  }
  async function selectFiles(files: File[]) {
    const known = new Set(
      current.current.map((entry) => fileIdentity(entry.file)),
    )
    const added: PdfSelection[] = []
    let duplicates = 0
    let excess = 0
    for (const file of files) {
      const key = fileIdentity(file)
      if (known.has(key)) {
        duplicates++
        continue
      }
      if (current.current.length + added.length >= MAX_BATCH_FILES) {
        excess++
        continue
      }
      known.add(key)
      added.push({
        id: crypto.randomUUID(),
        file,
        title: file.name.replace(/\.pdf$/i, '').replaceAll('-', ' '),
        validation: 'checking',
        upload: 'idle',
        error: '',
      })
    }
    setNotice(
      [
        duplicates ? `${duplicates} archivos ya estaban adjuntados.` : '',
        excess
          ? `El lote admite ${MAX_BATCH_FILES} archivos. ${excess} quedaron fuera.`
          : '',
      ]
        .filter(Boolean)
        .join(' '),
    )
    update((items) => [...items, ...added])
    await runConcurrent(added, 4, async (entry) => {
      const error = await validatePdf(entry.file)
      patch(entry.id, {
        validation: error ? 'invalid' : 'ready',
        error: error ?? '',
      })
    })
  }
  function handleDrop(event: React.DragEvent<HTMLElement>) {
    event.preventDefault()
    setIsDragging(false)
    void selectFiles(Array.from(event.dataTransfer.files))
  }
  function remove(id: string) {
    update((items) => items.filter((entry) => entry.id !== id))
    setNotice('')
  }
  function clear() {
    update(() => [])
    setNotice('')
  }

  return {
    entries,
    notice,
    isDragging,
    setIsDragging,
    selectFiles,
    remove,
    clear,
    patch,
    handleDrop,
  }
}
