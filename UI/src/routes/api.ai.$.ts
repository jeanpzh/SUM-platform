import { createFileRoute } from '@tanstack/react-router'
import { proxyAi } from '#/lib/ai/proxy.server'

export const Route = createFileRoute('/api/ai/$')({
  server: { handlers: {
    GET: ({ request, params }) => proxyAi(request, params._splat ?? ''),
    POST: ({ request, params }) => proxyAi(request, params._splat ?? ''),
  } },
})
