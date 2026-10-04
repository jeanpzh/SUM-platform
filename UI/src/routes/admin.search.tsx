import { createFileRoute } from '@tanstack/react-router'
import { SearchView } from '#/components/admin/search-view'

export const Route = createFileRoute('/admin/search')({ component: SearchView })
