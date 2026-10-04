import { createFileRoute } from '@tanstack/react-router'
import { LibraryView } from '#/components/admin/library-view'

export const Route = createFileRoute('/admin/library')({
  component: LibraryView,
})
