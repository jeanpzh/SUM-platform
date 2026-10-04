import { useEffect } from 'react'
import { Link, useSearch } from '@tanstack/react-router'
import { Plus, RefreshCw } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { BackendStatus } from '#/components/pdf-dashboard/backend-status'
import { useIndexingJobs } from '#/hooks/use-indexing-jobs'
import type { JobFilter } from '#/data/pdf-ingestion-jobs'
import { useWorkspace, useWorkspaceApi } from './workspace-provider'
import { useBackendJobHistory } from '#/hooks/use-backend-job-history'
import { LibraryPagination } from './library-pagination'
import { DashboardPage, EmptyState, MetricStrip } from './dashboard-page'
import { IndexingJobCard } from './indexing-job-card'
import { selectClass } from './corpus-scope'

export function JobsView() {
  const jobs = useIndexingJobs()
  const history = useBackendJobHistory(useWorkspaceApi(), jobs.filter)
  const focused = useSearch({ from: '/admin/jobs' }).job
  const connected = useWorkspace((store) => store.backendStatus === 'ready')
  const originals = useWorkspace((store) => store.originals)
  const errors = useWorkspace((store) => store.monitoringErrors)
  useEffect(() => {
    if (focused)
      document
        .getElementById('job-' + focused)
        ?.scrollIntoView({ block: 'center' })
  }, [focused, history.jobs.length])
  return (
    <DashboardPage
      title="Cada documento tiene un recorrido"
      description="Sigue las seis etapas de la ingesta y gestiona las solicitudes que necesitan atención."
      action={
        <div className="flex flex-wrap gap-3">
          <BackendStatus />
          <Button asChild className="min-h-11">
            <Link to="/">
              <Plus size={16} />
              Cargar PDF
            </Link>
          </Button>
        </div>
      }
    >
      <MetricStrip
        items={[
          {
            label: 'En cola',
            value: history.counts.queued,
          },
          {
            label: 'En proceso',
            value: history.counts.processing,
          },
          {
            label: 'Publicados',
            value: history.counts.published,
          },
          {
            label: 'Con errores',
            value: history.counts.failed,
          },
        ]}
      />
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl">Historial de ingesta</h2>
          <p className="mt-2 text-xs text-muted-foreground">
            {connected
              ? 'Historial persistente del backend · seguimiento de etapas cada 2 segundos.'
              : 'Comprobando el servicio automáticamente. Se conserva el último estado confirmado.'}
          </p>
        </div>
        <div className="flex w-full flex-wrap items-end gap-3 sm:w-auto">
          <Button
            variant="outline"
            disabled={!connected || history.loading}
            onClick={history.refresh}
          >
            <RefreshCw
              size={15}
              className={history.loading ? 'animate-spin' : undefined}
            />
            Actualizar historial
          </Button>
          <div className="w-full sm:w-44">
            <label
              htmlFor="jobs-status"
              className="mb-2 block text-sm font-semibold"
            >
              Estado
            </label>
            <select
              id="jobs-status"
              className={selectClass}
              value={jobs.filter}
              onChange={(event) =>
                jobs.setFilter(event.target.value as JobFilter)
              }
            >
              <option value="all">Todos</option>
              <option value="active">Activos</option>
              <option value="published">Publicados</option>
              <option value="failed">Con errores</option>
              <option value="cancelled">Cancelados</option>
            </select>
          </div>
        </div>
      </div>
      {history.error && (
        <p
          role="alert"
          className="mb-5 rounded-md border border-destructive/30 p-3 text-sm text-destructive"
        >
          No se pudo recuperar el historial: {history.error}
        </p>
      )}
      {jobs.actionError && (
        <p role="alert" className="mb-5 text-sm text-destructive">
          {jobs.actionError}
        </p>
      )}
      {history.loading && history.jobs.length === 0 ? (
        <p
          role="status"
          className="rounded-md border border-border p-8 text-center text-sm text-muted-foreground"
        >
          Cargando trabajos desde el backend…
        </p>
      ) : history.jobs.length ? (
        <div className="space-y-4" aria-live="polite">
          {history.jobs.map((job) => (
            <IndexingJobCard
              key={job.id}
              job={job}
              focused={job.id === focused}
              busy={jobs.busyIds.includes(job.id)}
              connected={connected}
              hasOriginal={originals.has(job.id)}
              monitoringError={errors[job.id]}
              onRetry={(file) => {
                void jobs.retry(job.id, file)
              }}
              onCancel={() => {
                void jobs.cancel(job.id)
              }}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="La cola está despejada">
          {history.error
            ? 'El backend no confirmó el historial. Reintenta la consulta.'
            : 'No hay trabajos registrados con este filtro. Los trabajos aparecerán aquí tras ser aceptados por el backend.'}
        </EmptyState>
      )}
      <LibraryPagination
        total={history.total}
        offset={history.offset}
        limit={25}
        busy={history.loading}
        onChange={history.setOffset}
      />
      <p className="mt-6 border-t border-border pt-4 text-xs leading-5 text-muted-foreground">
        Reintentar un trabajo fallido o cancelado carga una nueva versión del
        documento. El original se conserva en memoria durante esta sesión;
        después de recargar tendrás que adjuntarlo nuevamente.
      </p>
    </DashboardPage>
  )
}
