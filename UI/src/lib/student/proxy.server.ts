import { createHash, createHmac } from 'node:crypto'

const uuid =
  '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
const detail = new RegExp(`^runs/${uuid}(?:/(?:stream|cancel))?$`)

export async function proxyStudent(
  request: Request,
  path: string,
): Promise<Response> {
  const allowed =
    (path === 'chat' && request.method === 'POST') ||
    (path === 'runs' && request.method === 'GET') ||
    (detail.test(path) &&
      request.method === (path.endsWith('/cancel') ? 'POST' : 'GET'))
  const error = (message: string, status: number) =>
    new Response(message, { status, headers: { 'Cache-Control': 'no-store' } })
  if (!allowed) return error('Ruta no permitida.', 404)
  const origin = request.headers.get('origin')
  if (
    request.headers.get('sec-fetch-site') === 'cross-site' ||
    (origin && origin !== new URL(request.url).origin)
  )
    return error('Origen no permitido.', 403)
  let subject: string
  try {
    const { auth } = await import('#/lib/auth')
    const session = await auth.api.getSession({ headers: request.headers })
    if (!session?.user)
      return error('Inicia sesión para consultar al asistente.', 401)
    if (session.user.banned) return error('La cuenta no está habilitada.', 403)
    subject = session.user.id
  } catch {
    return error('No se pudo verificar la sesión.', 503)
  }
  const token = process.env.BACKEND_ADMIN_TOKEN ?? process.env.API_ADMIN_TOKEN
  const secret = process.env.AI_IDENTITY_SECRET
  if (!token || !secret || secret.length < 24)
    return error('El asistente todavía no está configurado.', 503)
  const body = request.method === 'POST' ? await request.text() : ''
  if (Buffer.byteLength(body) > 16384)
    return error('La consulta es demasiado larga.', 413)
  const upstreamPath = `/v1/student/ai/${path}`
  const claims = {
    sub: subject,
    role: 'student',
    exp: Math.floor(Date.now() / 1000) + 60,
    method: request.method,
    path: upstreamPath,
    body_sha256: createHash('sha256').update(body).digest('hex'),
  }
  const payload = Buffer.from(JSON.stringify(claims))
  const headers = new Headers({
    Authorization: `Bearer ${token}`,
    'X-Student-Assertion': `${payload.toString('hex')}.${createHmac('sha256', secret).update(payload).digest('hex')}`,
  })
  if (body) headers.set('Content-Type', 'application/json')
  const key = request.headers.get('idempotency-key')
  if (key) headers.set('Idempotency-Key', key)
  const base = (process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000').replace(
    /\/$/,
    '',
  )
  try {
    const upstream = await fetch(
      `${base}${upstreamPath}${new URL(request.url).search}`,
      {
        method: request.method,
        headers,
        body: body || undefined,
        signal: request.signal,
      },
    )
    const responseHeaders = new Headers({
      'Cache-Control': 'no-store',
      'X-Accel-Buffering': 'no',
    })
    for (const name of [
      'content-type',
      'retry-after',
      'x-vercel-ai-ui-message-stream',
      'x-run-id',
    ]) {
      const value = upstream.headers.get(name)
      if (value) responseHeaders.set(name, value)
    }
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    })
  } catch {
    return error('El servicio del asistente no está disponible.', 503)
  }
}
