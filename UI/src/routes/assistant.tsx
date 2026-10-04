import { createFileRoute, Outlet } from '@tanstack/react-router'
import { StudentView } from '#/components/student/student-view'

export const Route = createFileRoute('/assistant')({
  head: () => ({ meta: [{ title: 'Asistente académico · SUM' }] }),
  component: () => (
    <>
      <StudentView />
      <Outlet />
    </>
  ),
})
