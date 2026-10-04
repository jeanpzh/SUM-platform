import { createFileRoute } from '@tanstack/react-router'
import type {} from '@tanstack/react-start'
import { proxyStudent } from '#/lib/student/proxy.server'

export const Route = createFileRoute('/api/student/ai/$')({
  server: {
    handlers: {
      GET: ({ request, params }) => proxyStudent(request, params._splat ?? ''),
      POST: ({ request, params }) => proxyStudent(request, params._splat ?? ''),
    },
  },
})
