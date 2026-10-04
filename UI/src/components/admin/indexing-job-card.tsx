import { useRef } from 'react'
import { RotateCcw, CircleSlash } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { JobStatusView } from '#/components/pdf-dashboard/job-status'
import type { IndexingJob } from '#/data/pdf-ingestion-jobs'
import { JobTimingSummary } from './job-timing-summary'
import { JobPipeline } from './job-pipeline'
import { DocumentActions } from './document-actions'

export function IndexingJobCard({
  job,
  focused,
  busy,
  connected,
  hasOriginal,
  monitoringError,
  onRetry,
  onCancel,
}: {
  job: IndexingJob
  focused: boolean
  busy: boolean
  connected: boolean
  hasOriginal: boolean
  monitoringError?: string
  onRetry: (file?: File) => void
  onCancel: () => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const backend = job.source === 'backend'
  const active = ['queued', 'processing'].includes(job.status)
  return (
    <article
      id={'job-' + job.id}
      data-testid="indexing-job"
      data-job-id={job.id}
      className={`scroll-mt-6 space-y-5 rounded-lg border bg-card/40 p-5 sm:p-6 ${focused ? 'border-primary ring-1 ring-primary/20' : 'border-border'}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-2 text-xs font-semibold text-muted-foreground">
            {backend ? 'BACKEND · ' + job.id : 'MUESTRA LOCAL'}
          </p>
          <h3 className="break-all text-sm font-semibold">{job.fileName}</h3>
          <p className="mt-1 break-all text-xs text-muted-foreground">
            {job.originUrl || 'Archivo local'} · {job.updatedAt}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {['failed', 'cancelled'].includes(job.status) && (
            <>
              <input
                ref={input}
                type="file"
                accept="application/pdf,.pdf"
                className="sr-only"
                aria-label={`Original para reintentar ${job.fileName}`}
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) onRetry(file)
                  event.target.value = ''
                }}
              />
              <Button
                variant="outline"
                disabled={busy || (backend && !connected)}
                onClick={() => {
                  if (backend && !hasOriginal) input.current?.click()
                  else onRetry()
                }}
              >
                <RotateCcw size={15} />
                {busy
                  ? 'Enviando…'
                  : backend && !hasOriginal
                    ? 'Adjuntar original y reintentar'
                    : 'Reintentar'}
              </Button>
            </>
          )}
          {active && (
            <Button
              variant="outline"
              disabled={busy || (backend && !connected)}
              onClick={onCancel}
            >
              <CircleSlash size={15} />
              {busy ? 'Cancelando…' : 'Cancelar solicitud'}
            </Button>
          )}
        </div>
      </div>
      <JobStatusView
        status={job.status}
        progress={job.progress}
        note={job.note}
      />
      {job.errorCode && (
        <p className="text-xs text-destructive">
          Código de error: {job.errorCode}
        </p>
      )}
      {backend && job.counts && (
        <dl
          className="flex flex-wrap gap-x-8 gap-y-3 text-xs text-muted-foreground"
          aria-label="Contadores reportados por el backend"
        >
          {(
            [
              ['paginas', 'Páginas'],
              ['fragmentos', 'Fragmentos'],
              ['vectores', 'Vectores'],
            ] as const
          ).map(([key, label]) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd className="mt-1 text-lg font-semibold tabular-nums text-foreground">
                {job.counts?.[key] ?? '—'}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {monitoringError && (
        <p role="alert" className="text-sm text-warning">
          No se pudo actualizar: {monitoringError} Se conserva el último estado
          confirmado.
        </p>
      )}
      {backend && !connected && active && (
        <p className="text-xs text-warning">
          El seguimiento se reanudará automáticamente cuando el servicio esté
          disponible.
        </p>
      )}
      {backend && <JobTimingSummary job={job} />}
      <JobPipeline job={job} />
      {backend && job.documentId && (
        <DocumentActions
          documentId={job.documentId}
          title={job.title ?? job.fileName.replace(/\.pdf$/i, '')}
          metadata={job.sourceMetadata}
          active={active}
        />
      )}
    </article>
  )
}
