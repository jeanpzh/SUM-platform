import { createFileRoute } from '@tanstack/react-router'
import { MetricsView } from '#/components/admin/metrics-view'

export const Route = createFileRoute('/admin/metrics')({ component: MetricsView })
