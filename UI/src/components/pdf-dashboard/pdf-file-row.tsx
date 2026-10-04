import { Link } from '@tanstack/react-router'
import { FileText, X, Check, LoaderCircle } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Progress } from '#/components/ui/progress'
import type { PdfSelection } from '#/hooks/use-pdf-file-selection'
import { useWorkspace } from '#/components/admin/workspace-provider'
import { pipelineStages } from '#/lib/admin-workspace/schema'
import { JobStatusView } from './job-status'

export function PdfFileRow({
  entry,
  busy,
  onRemove,
  onTitleChange,
}: {
  entry: PdfSelection
  busy: boolean
  onRemove: () => void
  onTitleChange: (title: string) => void
}) {
  const job = useWorkspace((store) =>
    store.state.jobs.find((item) => item.id === entry.jobId),
  )
  const labels = {
    idle: 'Listo para cargar',
    waiting: 'Esperando turno de carga',
    uploading: 'Enviando al backend',
    accepted: 'Carga aceptada por el backend',
    error: 'La carga requiere un reintento',
  }
  return (
    <li
      className="rounded-md border border-border bg-background p-4"
      data-testid="pdf-file-row"
    >
      <div className="flex items-start gap-3">
        <FileText
          size={18}
          className="mt-1 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
        <div className="min-w-0 flex-1">
          <p className="break-all text-sm font-semibold">{entry.file.name}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {(entry.file.size / 1024 / 1024).toFixed(2)} MB
          </p>
        </div>
        <Button
          variant="ghost"
          type="button"
          size="icon"
          disabled={busy}
          onClick={onRemove}
          className="size-9 shrink-0"
          aria-label={`Quitar ${entry.file.name}`}
        >
          <X size={16} />
        </Button>
      </div>
      <div className="mt-3">
        <label
          htmlFor={'title-' + entry.id}
          className="mb-1 block text-xs text-muted-foreground"
        >
          Título del documento
        </label>
        <Input
          id={'title-' + entry.id}
          value={entry.title}
          onChange={(event) => onTitleChange(event.target.value)}
          disabled={busy || !!entry.request}
          maxLength={300}
          className="h-10 text-sm"
        />
      </div>
      <p
        className={`mt-3 flex items-center gap-2 text-xs ${entry.error ? 'text-destructive' : entry.upload === 'accepted' ? 'text-success' : 'text-muted-foreground'}`}
        role={entry.error ? 'alert' : 'status'}
      >
        {entry.upload === 'accepted' && <Check size={13} />}
        {(entry.validation === 'checking' || entry.upload === 'uploading') && (
          <LoaderCircle size={13} className="motion-safe:animate-spin" />
        )}
        {entry.error ||
          (entry.validation === 'checking'
            ? 'Validando PDF…'
            : labels[entry.upload])}
      </p>
      {entry.upload === 'uploading' && (
        <div className="mt-2">
          <Progress
            value={entry.progress ?? 0}
            aria-label={`Carga de ${entry.file.name}`}
            className="h-1.5"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            {entry.progress ?? 0}% transferido · aún no confirma indexación
          </p>
        </div>
      )}
      {entry.jobId && (
        <div className="mt-3 space-y-2 border-t border-border pt-3">
          {job && (
            <>
              <JobStatusView status={job.status} note={job.note} />
              {typeof job.stage === 'number' && (
                <p className="text-xs text-muted-foreground">
                  Etapa {job.stage + 1} de 6 · {pipelineStages[job.stage]}
                </p>
              )}
            </>
          )}
          <Link
            to="/admin/jobs"
            search={{ job: entry.jobId }}
            className="mt-3 inline-block text-xs font-semibold underline"
          >
            Ver indexación de este PDF →
          </Link>
        </div>
      )}
      {entry.upload === 'error' && (
        <p className="mt-2 text-xs text-muted-foreground">
          El reintento conserva el contenido, los metadatos y la misma clave de
          solicitud.
        </p>
      )}
    </li>
  )
}
