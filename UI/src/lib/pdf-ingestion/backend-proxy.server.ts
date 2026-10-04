const uuid =
  '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
const idPath = new RegExp(
  `^(?:documents|jobs)/${uuid}(?:/(?:versions|chunks|reindex|cancel))?$`,
)
const exactPaths = new Set([
  'documents',
  'connection',
  'capabilities',
  'history',
  'admin/embedding-profile',
  'admin/reindex-stale',
])

export async function proxyBackend(request: Request, path: string) {
  const error = (mensaje: string, status: number) =>
    Response.json(
      { mensaje },
      { status, headers: { 'Cache-Control': 'no-store' } },
    )
  const validPath = exactPaths.has(path) || idPath.test(path)
  if (!validPath) return error('La ruta no existe.', 404)
  const connection = path === 'connection' && request.method === 'GET'
  const capabilities = path === 'capabilities' && request.method === 'GET'
  const history = path === 'history' && request.method === 'GET'
  const profile = path === 'admin/embedding-profile'
  const bulkReindex =
    path === 'admin/reindex-stale' && request.method === 'POST'
  const upload =
    (path === 'documents' || path.endsWith('/versions')) &&
    request.method === 'POST'
  const chunks = path.endsWith('/chunks') && request.method === 'GET'
  const documentReindex = path.endsWith('/reindex') && request.method === 'POST'
  const remove =
    path.startsWith('documents/') &&
    idPath.test(path) &&
    request.method === 'DELETE'
  const cancel = path.endsWith('/cancel') && request.method === 'POST'
  const jobRead =
    path.startsWith('jobs/') &&
    !path.endsWith('/cancel') &&
    !path.endsWith('/reindex') &&
    request.method === 'GET'
  const profileRead = profile && request.method === 'GET'
  const profileWrite = profile && request.method === 'PATCH'
  const documentList = path === 'documents' && request.method === 'GET'
  if (
    !connection &&
    !capabilities &&
    !history &&
    !profileRead &&
    !profileWrite &&
    !bulkReindex &&
    !upload &&
    !documentList &&
    !chunks &&
    !documentReindex &&
    !remove &&
    !cancel &&
    !jobRead
  )
    return error('El método no está permitido.', 405)
  const origin = request.headers.get('origin')
  if (
    request.headers.get('sec-fetch-site') === 'cross-site' ||
    (origin && origin !== new URL(request.url).origin)
  )
    return error('El origen de la solicitud no está permitido.', 403)
  const token = process.env.BACKEND_ADMIN_TOKEN ?? process.env.API_ADMIN_TOKEN
  if (!token?.trim())
    return error('El servicio de ingesta no está configurado.', 503)
  const headers = new Headers({ Authorization: 'Bearer ' + token.trim() })
  if (upload) {
    const type = request.headers.get('content-type') ?? ''
    if (!type.startsWith('multipart/form-data;'))
      return error('Se requiere una carga multipart.', 415)
    headers.set('Content-Type', type)
    headers.set('Idempotency-Key', request.headers.get('idempotency-key') ?? '')
  }
  if (remove || profileWrite) {
    headers.set('Content-Type', 'application/json')
  }
  const upstreamPath = connection
    ? 'indexing-jobs/00000000-0000-0000-0000-000000000000'
    : capabilities
      ? 'admin/capabilities'
      : history
        ? 'indexing-jobs'
        : profile
          ? 'admin/embedding-profile'
          : bulkReindex
            ? 'admin/reindex-stale'
            : path.startsWith('jobs/')
              ? path.replace(/^jobs\//, 'indexing-jobs/')
              : path === 'documents' ||
                  documentList ||
                  chunks ||
                  documentReindex ||
                  remove
                ? path
                : 'documents'
  try {
    const response = await fetch(
      (process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000').replace(
        /\/$/,
        '',
      ) +
        '/v1/' +
        upstreamPath +
        (['history', 'documents'].includes(path) || chunks
          ? new URL(request.url).search
          : ''),
      {
        method: request.method,
        headers,
        body: upload
          ? request.body
          : remove || profileWrite
            ? request.body
            : undefined,
        duplex: 'half',
        signal: AbortSignal.any([
          request.signal,
          AbortSignal.timeout(upload ? 120000 : 15000),
        ]),
        redirect: 'error',
      } as RequestInit & { duplex: 'half' },
    )
    if (connection && (response.status === 404 || response.ok))
      return Response.json(
        { estado: 'disponible' },
        { headers: { 'Cache-Control': 'no-store' } },
      )
    if (response.status === 401 || response.status === 403)
      return error(
        'La configuración del servicio de ingesta no permite esta operación.',
        503,
      )
    return new Response(response.body, {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
      },
    })
  } catch {
    return error(
      'No se pudo contactar al backend. Comprueba que el servicio esté disponible.',
      503,
    )
  }
}
