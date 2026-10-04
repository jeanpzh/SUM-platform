import { createFileRoute } from '@tanstack/react-router'
import { JobsView } from '#/components/admin/jobs-view'

export const Route = createFileRoute('/admin/jobs')({
  validateSearch: (search: Record<string, unknown>): { job?: string } => ({
    job: typeof search.job === 'string' ? search.job.slice(0, 160) : undefined,
  }),
  component: JobsView,
})
