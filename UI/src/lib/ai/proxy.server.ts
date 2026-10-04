import { createHash, createHmac } from 'node:crypto'
import type { AdminIdentity } from './admin-auth.server'

const uuid =
  '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
const runPath = new RegExp(`^runs/${uuid}(?:/(?:events|cancel))?$`)

function allowed(path: string, method: string): boolean {
  if (path === 'models' || path === 'metrics' || path === 'evaluations')
    return method === 'GET' || (path === 'evaluations' && method === 'POST')
  if (path === 'providers') return method === 'GET' || method === 'POST'
  if (path === 'providers/pricing') return method === 'GET'
  if (path === 'providers/test') return method === 'POST'
  if (new RegExp(`^providers/${uuid}$`).test(path)) return method === 'POST'
  if (path === 'runs') return method === 'GET' || method === 'POST'
  if (runPath.test(path))
    return method === (path.endsWith('/cancel') ? 'POST' : 'GET')
  return false
}

const error = (message: string, status: number) =>
  Response.json(
    { code: 'AI_PROXY_ERROR', message },
    { status, headers: { 'Cache-Control': 'no-store' } },
  )

export async function proxyAi(
  request: Request,
  path: string,
  sessionResolver?: (request: Request) => Promise<AdminIdentity | null>,
): Promise<Response> {
  if (!allowed(path, request.method))
    return error('Ruta o método no permitido.', 404)
  const origin = request.headers.get('origin')
  if (
    request.headers.get('sec-fetch-site') === 'cross-site' ||
    (origin && origin !== new URL(request.url).origin)
  )
    return error('Origen no permitido.', 403)
  let identity: AdminIdentity | null
  try {
    if (sessionResolver) identity = await sessionResolver(request)
    // Temporary identity for the admin panel while user authentication is disabled.
    else identity = { id: 'local-admin', email: 'local-admin@localhost' }
  } catch (caught) {
    if (caught instanceof Response)
      return error('Acceso administrativo denegado.', caught.status)
    return error('No se pudo verificar la sesión.', 503)
  }
  if (!identity) return error('Se requiere iniciar sesión.', 401)
  const token = process.env.BACKEND_ADMIN_TOKEN ?? process.env.API_ADMIN_TOKEN
  const secret = process.env.AI_IDENTITY_SECRET
  if (!token || !secret || secret.length < 24)
    return error('Servicio de IA sin configurar.', 503)
  const body = request.method === 'POST' ? await request.text() : ''
  if (body.length > 16_384) return error('Solicitud demasiado grande.', 413)
  const upstreamPath = `/v1/admin/ai/${path}`
  const claims = {
    sub: identity.id,
    role: 'admin',
    exp: Math.floor(Date.now() / 1000) + 60,
    method: request.method,
    path: upstreamPath,
    body_sha256: createHash('sha256').update(body).digest('hex'),
  }
  const payload = Buffer.from(JSON.stringify(claims))
  const assertion = `${payload.toString('hex')}.${createHmac('sha256', secret).update(payload).digest('hex')}`
  const headers = new Headers({
    Authorization: `Bearer ${token}`,
    'X-Admin-Assertion': assertion,
  })
  if (body) headers.set('Content-Type', 'application/json')
  const key = request.headers.get('idempotency-key')
  if (key) headers.set('Idempotency-Key', key)
  const lastEvent = request.headers.get('last-event-id')
  if (lastEvent) headers.set('Last-Event-ID', lastEvent)
  const url = `${(process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')}${upstreamPath}${new URL(request.url).search}`
  try {
    const response = await fetch(url, {
      method: request.method,
      headers,
      body: body || undefined,
      signal: AbortSignal.any([
        request.signal,
        AbortSignal.timeout(
          path.endsWith('/events')
            ? 70_000
            : path === 'providers/test'
              ? 15_000
              : 10_000,
        ),
      ]),
      redirect: 'error',
    })
    return new Response(response.body, {
      status: response.status,
      headers: {
        'Content-Type':
          response.headers.get('content-type') ?? 'application/json',
        'Cache-Control': 'no-store',
        ...(response.headers.get('retry-after')
          ? { 'Retry-After': response.headers.get('retry-after')! }
          : {}),
      },
    })
  } catch {
    return error('AI Service no disponible.', 503)
  }
}
