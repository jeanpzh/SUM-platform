import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { DashboardShell } from '#/components/pdf-dashboard/dashboard-shell'

export const Route = createFileRoute('/admin')({
  beforeLoad: ({ location }) => {
    if (location.pathname === '/admin' || location.pathname === '/admin/')
      throw redirect({ to: '/admin/library' })
  },
  component: AdminLayout,
})

function AdminLayout() {
  return (
    <DashboardShell>
      <Outlet />
    </DashboardShell>
  )
}
