import { useRef, useState } from 'react'
import { useWorkspace } from '#/components/admin/workspace-provider'
import { parseCorpusImport } from '#/lib/admin-workspace/import-export'
import type { ImportPreview } from '#/lib/admin-workspace/import-export'

export function useVectorTransfer() {
  const documents = useWorkspace((store) => store.state.documents)
  const settings = useWorkspace((store) => store.state.settings)
  const dispatch = useWorkspace((store) => store.dispatch)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [fileName, setFileName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const request = useRef(0)

  function reset() {
    request.current++
    setPreview(null)
    setFileName('')
    setError('')
    setBusy(false)
  }

  async function readFile(file?: File) {
    if (!file) return
    const currentRequest = ++request.current
    setPreview(null)
    setError('')
    setFileName(file.name)
    if (file.size > 4 * 1024 * 1024) {
      setError('El archivo supera el límite local de 4 MB.')
      setBusy(false)
      return
    }
    setBusy(true)
    try {
      const result = parseCorpusImport(await file.text(), file.name, settings)
      if (request.current === currentRequest) setPreview(result)
    } catch (cause) {
      if (request.current === currentRequest)
        setError(
          cause instanceof Error
            ? cause.message
            : 'No se pudo leer el archivo.',
        )
    } finally {
      if (request.current === currentRequest) setBusy(false)
    }
  }

  function commit() {
    if (!preview) return false
    if (documents.length + preview.documents.length > 200) {
      setError(
        'El espacio local admite hasta 200 documentos. Reduce la importación o elimina documentos.',
      )
      return false
    }
    dispatch({
      type: 'import',
      documents: preview.documents.map((doc) => ({
        ...doc,
        id: crypto.randomUUID(),
        chunks: doc.chunks.map((chunk) => ({
          ...chunk,
          id: crypto.randomUUID(),
        })),
      })),
    })
    reset()
    return true
  }

  return { preview, fileName, error, busy, readFile, reset, commit }
}
