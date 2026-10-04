import { createFileRoute } from '@tanstack/react-router'
import { proxyBackend } from '#/lib/pdf-ingestion/backend-proxy.server'

export const Route = createFileRoute('/api/indexing/$')({
  server: {
    handlers: {
      GET: ({ request, params }) => proxyBackend(request, params._splat ?? ''),
      POST: ({ request, params }) => proxyBackend(request, params._splat ?? ''),
      PATCH: ({ request, params }) =>
        proxyBackend(request, params._splat ?? ''),
      DELETE: ({ request, params }) =>
        proxyBackend(request, params._splat ?? ''),
    },
  },
})
