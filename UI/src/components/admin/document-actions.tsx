import { useId, useState } from 'react'
import { RefreshCw, Trash2 } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useDocumentAdministration } from '#/hooks/use-document-administration'
import type { SourceMetadata } from '#/lib/pdf-ingestion/schema'
import { useWorkspace } from './workspace-provider'

export function DocumentActions({
  documentId,
  title,
  metadata,
  active = false,
  reindex = false,
}: {
  documentId: string
  title: string
  metadata?: SourceMetadata
  active?: boolean
  reindex?: boolean
}) {
  const actions = useDocumentAdministration(documentId, title, metadata)
  const development = useWorkspace((store) => store.envMode === 'DEVELOPMENT')
  const ready = useWorkspace((store) => store.backendStatus === 'ready')
  const [confirming, setConfirming] = useState(false)
  const [confirmation, setConfirmation] = useState('')
  const id = useId()
  if (!reindex && !development) return null
  return (
    <div className="w-full space-y-3 border-t border-border pt-3">
      <div className="flex flex-wrap items-center gap-2">
        {reindex && (
          <Button
            variant="outline"
            disabled={!ready || active || actions.busy}
            onClick={() => void actions.reindex()}
          >
            <RefreshCw size={14} />{' '}
            {actions.busy ? 'Procesando…' : 'Reindexar con modelo actual'}
          </Button>
        )}
        {development && (
          <Button
            variant="ghost"
            className="text-destructive"
            disabled={!ready || active || actions.busy}
            onClick={() => setConfirming(!confirming)}
          >
            <Trash2 size={14} /> Eliminar registro de prueba
          </Button>
        )}
        {development && active && (
          <p className="text-xs text-muted-foreground">
            Espera o cancela el trabajo antes de eliminarlo.
          </p>
        )}
      </div>
      {development && confirming && (
        <div className="space-y-3 rounded-md border border-destructive/30 p-4">
          <label htmlFor={id} className="block text-xs leading-6">
            Se eliminarán el PDF, todas sus versiones, fragmentos e historial.
            Escribe el título para confirmar:{' '}
            <strong className="break-all">{title}</strong>
          </label>
          <div className="flex flex-wrap gap-2">
            <Input
              id={id}
              className="min-w-0 flex-1"
              autoComplete="off"
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
            />
            <Button
              variant="destructive"
              disabled={confirmation !== title || actions.busy || !ready}
              onClick={() => void actions.remove(confirmation)}
            >
              Eliminar definitivamente
            </Button>
            <Button
              variant="outline"
              onClick={() => setConfirming(false)}
              disabled={actions.busy}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}
      {actions.error && (
        <p role="alert" className="text-sm text-destructive">
          {actions.error}
        </p>
      )}
      {actions.notice && (
        <p role="status" className="text-sm text-success">
          {actions.notice}
        </p>
      )}
    </div>
  )
}
