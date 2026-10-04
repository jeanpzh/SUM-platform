import { useId } from 'react'
import { Link } from '@tanstack/react-router'
import { FileText, RotateCcw } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { NativeSelect, NativeSelectOption } from '#/components/ui/native-select'
import { Separator } from '#/components/ui/separator'
import type { IndexingJob, JobFilter } from '#/data/pdf-ingestion-jobs'
import { JobStatusView } from './job-status'

type RecentJobsProps = {
  jobs: IndexingJob[]
  filter: JobFilter
  onFilterChange: (filter: JobFilter) => void
  onRetry: (jobId: string) => void
}

function readableFileName(fileName: string) {
  return fileName.replace(/\.pdf$/i, '').replaceAll('-', ' ')
}

export function RecentJobs({
  jobs,
  filter,
  onFilterChange,
  onRetry,
}: RecentJobsProps) {
  const filterId = useId()

  return (
    <section
      id="trabajos"
      aria-labelledby="recent-jobs-heading"
      className="mt-9 sm:mt-12"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-1 text-[0.68rem] font-semibold tracking-[0.16em] text-muted-foreground uppercase">
            Actividad
          </p>
          <h2
            id="recent-jobs-heading"
            className="m-0 font-display text-[1.65rem] leading-tight font-medium tracking-[-0.025em] text-foreground sm:text-[1.85rem]"
          >
            Trabajos recientes
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <label htmlFor={filterId} className="text-sm text-muted-foreground">
            Estado
          </label>
          <NativeSelect
            id={filterId}
            value={filter}
            onChange={(event) =>
              onFilterChange(event.currentTarget.value as JobFilter)
            }
            className="h-10 min-w-36 rounded-md border-input bg-background px-3 pr-9 text-sm shadow-none focus-visible:border-primary focus-visible:ring-primary/15"
          >
            <NativeSelectOption value="all">Todos</NativeSelectOption>
            <NativeSelectOption value="active">En proceso</NativeSelectOption>
            <NativeSelectOption value="published">
              Publicados
            </NativeSelectOption>
            <NativeSelectOption value="failed">Con errores</NativeSelectOption>
            <NativeSelectOption value="cancelled">
              Cancelados
            </NativeSelectOption>
          </NativeSelect>
        </div>
      </div>

      <div className="mt-5 hidden grid-cols-[minmax(0,1.4fr)_minmax(190px,1fr)_minmax(100px,.55fr)_auto] gap-5 border-b border-border px-1 pb-3 text-[0.67rem] font-semibold tracking-[0.12em] text-muted-foreground uppercase md:grid">
        <span>Documento</span>
        <span>Estado</span>
        <span>Actualizado</span>
        <span className="sr-only">Acciones</span>
      </div>

      <div role="list" aria-label="Trabajos de indexación" className="mt-1">
        {jobs.map((job, index) => (
          <div key={job.id} role="listitem">
            <div className="grid gap-3 py-4 md:grid-cols-[minmax(0,1.4fr)_minmax(190px,1fr)_minmax(100px,.55fr)_auto] md:items-center md:gap-5 md:px-1">
              <div className="flex min-w-0 items-start gap-3">
                <FileText
                  size={19}
                  strokeWidth={1.5}
                  className="mt-0.5 shrink-0 text-muted-foreground"
                  aria-hidden="true"
                />
                <div className="min-w-0">
                  <p className="mb-0 break-words text-sm font-semibold text-foreground">
                    {readableFileName(job.fileName)}
                  </p>
                  <p className="mb-0 mt-1 break-all text-xs text-muted-foreground">
                    {job.fileName}
                  </p>
                </div>
              </div>

              <JobStatusView
                status={job.status}
                progress={job.progress}
                note={job.note}
              />

              <span className="pl-8 text-xs text-muted-foreground md:pl-0">
                {job.updatedAt}
              </span>

              <div className="flex justify-end pl-8 md:pl-0">
                {job.source === 'backend' && (
                  <Button
                    asChild
                    variant="outline"
                    className="mr-2 h-10 text-xs"
                  >
                    <Link to="/admin/jobs" search={{ job: job.id }}>
                      Ver proceso
                    </Link>
                  </Button>
                )}
                {job.source !== 'backend' &&
                  (job.status === 'failed' || job.status === 'cancelled') && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => onRetry(job.id)}
                      className="h-10 border-border bg-transparent px-3 text-xs font-semibold text-primary hover:border-primary hover:bg-primary-soft"
                    >
                      <RotateCcw
                        size={14}
                        strokeWidth={1.6}
                        aria-hidden="true"
                      />
                      Reintentar
                    </Button>
                  )}
              </div>
            </div>
            {index < jobs.length - 1 && <Separator className="bg-border" />}
          </div>
        ))}

        {jobs.length === 0 && (
          <div className="py-10 text-center">
            <p className="mb-1 text-sm font-semibold text-foreground">
              No hay trabajos en este estado
            </p>
            <p className="m-0 text-sm text-muted-foreground">
              Elige otro filtro para ver más documentos.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
