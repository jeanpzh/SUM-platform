import { createFileRoute } from '@tanstack/react-router'
import { DashboardShell } from '#/components/pdf-dashboard/dashboard-shell'
import { DocumentUploadCard } from '#/components/pdf-dashboard/document-upload-card'
import { RecentJobs } from '#/components/pdf-dashboard/recent-jobs'
import { useIndexingJobs } from '#/hooks/use-indexing-jobs'
import { DashboardPage } from '#/components/admin/dashboard-page'
import { BackendStatus } from '#/components/pdf-dashboard/backend-status'
import { useBackendJobHistory } from '#/hooks/use-backend-job-history'
import { useWorkspaceApi } from '#/components/admin/workspace-provider'

export const Route = createFileRoute('/')({ component: PdfIngestionDashboard })

function PdfIngestionDashboard() {
  const { filter, setFilter, retry, actionError } = useIndexingJobs()
  const history = useBackendJobHistory(useWorkspaceApi(), filter)

  return (
    <DashboardShell>
      <DashboardPage
        title="Documentos institucionales"
        description="Carga varios PDF a la vez y revisa el proceso de indexación de cada documento."
        action={<BackendStatus />}
      >
        <DocumentUploadCard />
        {actionError && (
          <p role="alert" className="mt-4 text-sm text-destructive">
            {actionError}
          </p>
        )}

        <RecentJobs
          jobs={history.jobs}
          filter={filter}
          onFilterChange={setFilter}
          onRetry={retry}
        />
        {history.loading && (
          <p role="status" className="mt-3 text-xs text-muted-foreground">
            Actualizando trabajos desde el backend…
          </p>
        )}
        {history.error && (
          <p role="alert" className="mt-3 text-sm text-destructive">
            No se pudo recuperar el historial: {history.error}
          </p>
        )}

        <p className="mb-0 mt-6 border-t border-border pt-4 text-xs leading-5 text-muted-foreground">
          Cada respuesta conserva la referencia a su fuente y página. Las
          versiones vigentes siguen disponibles mientras se indexa una
          actualización.
        </p>
      </DashboardPage>
    </DashboardShell>
  )
}
