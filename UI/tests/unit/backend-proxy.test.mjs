import test from 'node:test'
import assert from 'node:assert/strict'
import { proxyBackend } from '../../src/lib/pdf-ingestion/backend-proxy.server.ts'

function serverConfig(t) {
  const previous = { ...process.env }
  process.env.BACKEND_ADMIN_TOKEN = 'server-only-test-credential'
  process.env.BACKEND_API_URL = 'http://backend.test:8000'
  t.after(() => {
    for (const key of [
      'BACKEND_ADMIN_TOKEN',
      'BACKEND_API_URL',
      'API_ADMIN_TOKEN',
    ]) {
      if (previous[key] === undefined) delete process.env[key]
      else process.env[key] = previous[key]
    }
  })
}

test('automatic connection uses server credential and never returns it', async (t) => {
  serverConfig(t)
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(
      url,
      'http://backend.test:8000/v1/indexing-jobs/00000000-0000-0000-0000-000000000000',
    )
    assert.equal(
      options.headers.get('authorization'),
      'Bearer server-only-test-credential',
    )
    return Response.json({ mensaje: 'Trabajo inexistente' }, { status: 404 })
  })
  const response = await proxyBackend(
    new Request('http://ui.test/api/indexing/connection', {
      headers: { Authorization: 'Bearer client-credential-must-be-ignored' },
    }),
    'connection',
  )
  assert.equal(response.status, 200)
  assert.deepEqual(await response.json(), { estado: 'disponible' })
})

test('missing server configuration rejects requests without calling backend', async (t) => {
  serverConfig(t)
  delete process.env.BACKEND_ADMIN_TOKEN
  delete process.env.API_ADMIN_TOKEN
  const fetch = t.mock.method(globalThis, 'fetch', () => {
    throw new Error('must not fetch')
  })
  const response = await proxyBackend(
    new Request('http://ui.test/api/indexing/connection'),
    'connection',
  )
  assert.equal(response.status, 503)
  assert.equal(fetch.mock.callCount(), 0)
})

test('cross-site requests and unsupported routes never reach administrative backend', async (t) => {
  serverConfig(t)
  const fetch = t.mock.method(globalThis, 'fetch', () => {
    throw new Error('must not fetch')
  })
  const crossSite = await proxyBackend(
    new Request('http://ui.test/api/indexing/documents', {
      method: 'POST',
      headers: { Origin: 'https://other-site.test' },
    }),
    'documents',
  )
  assert.equal(crossSite.status, 403)
  assert.equal(
    (
      await proxyBackend(
        new Request('http://ui.test/api/indexing/internal'),
        'internal',
      )
    ).status,
    404,
  )
  assert.equal(
    (
      await proxyBackend(
        new Request('http://ui.test/api/indexing/documents', {
          method: 'DELETE',
        }),
        'documents',
      )
    ).status,
    405,
  )
  assert.equal(fetch.mock.callCount(), 0)
})

test('same-origin PDF upload streams multipart and retains idempotency key', async (t) => {
  serverConfig(t)
  const body = new FormData()
  body.append(
    'archivo',
    new File(['%PDF-1.7'], 'document.pdf', { type: 'application/pdf' }),
  )
  body.append(
    'metadatos',
    JSON.stringify({ titulo: 'Plan', tipo_documento: 'otro' }),
  )
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, 'http://backend.test:8000/v1/documents')
    assert.equal(options.headers.get('idempotency-key'), 'stable-request')
    assert.equal(
      options.headers.get('authorization'),
      'Bearer server-only-test-credential',
    )
    const forwarded = await new Response(options.body).text()
    assert.match(forwarded, /%PDF-1.7/)
    assert.match(forwarded, /"tipo_documento":"otro"/)
    return Response.json({ trabajo_id: 'accepted' }, { status: 202 })
  })
  const response = await proxyBackend(
    new Request('http://ui.test/api/indexing/documents', {
      method: 'POST',
      body,
      headers: {
        Origin: 'http://ui.test',
        'Idempotency-Key': 'stable-request',
      },
    }),
    'documents',
  )
  assert.equal(response.status, 202)
})

test('upstream authentication failure reports configuration problem without leaking credentials', async (t) => {
  serverConfig(t)
  t.mock.method(globalThis, 'fetch', async () =>
    Response.json({ mensaje: 'Unauthorized' }, { status: 401 }),
  )
  const response = await proxyBackend(
    new Request('http://ui.test/api/indexing/connection'),
    'connection',
  )
  assert.equal(response.status, 503)
  assert.equal(
    (await response.text()).includes('server-only-test-credential'),
    false,
  )
})

test('published catalogue and chunks preserve search, pagination and version query', async (t) => {
  serverConfig(t)
  const id = '2ca19fd6-e1b6-4aad-8b8c-15a05944a85a'
  const seen = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    seen.push(url)
    assert.equal(
      options.headers.get('authorization'),
      'Bearer server-only-test-credential',
    )
    return Response.json({ documentos: [] })
  })
  for (const path of [
    'documents?q=matr%C3%ADcula&limit=25&offset=25',
    `documents/${id}/chunks?limit=20&offset=20&version_id=${id}`,
  ]) {
    const response = await proxyBackend(
      new Request('http://ui.test/api/indexing/' + path),
      path.split('?')[0],
    )
    assert.equal(response.status, 200)
    assert.equal(response.headers.get('cache-control'), 'no-store')
  }
  assert.equal(
    seen[0],
    'http://backend.test:8000/v1/documents?q=matr%C3%ADcula&limit=25&offset=25',
  )
  assert.equal(
    seen[1],
    `http://backend.test:8000/v1/documents/${id}/chunks?limit=20&offset=20&version_id=${id}`,
  )
})
