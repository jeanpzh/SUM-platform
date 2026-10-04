import test from 'node:test'
import assert from 'node:assert/strict'
import { proxyAi } from '../../src/lib/ai/proxy.server.ts'

const session = async () => ({ id: 'user-1', email: 'admin@example.test' })

function configure(t) {
  const previous = { ...process.env }
  process.env.BACKEND_API_URL = 'http://backend.test:8000'
  process.env.BACKEND_ADMIN_TOKEN = 'test-backend-token'
  process.env.AI_IDENTITY_SECRET = 'test-signing-secret-with-adequate-length'
  t.after(() => {
    for (const key of ['BACKEND_API_URL', 'BACKEND_ADMIN_TOKEN', 'AI_IDENTITY_SECRET']) {
      if (previous[key] === undefined) delete process.env[key]
      else process.env[key] = previous[key]
    }
  })
}

test('no session and cross-site request never reach backend', async (t) => {
  configure(t)
  const fetch = t.mock.method(globalThis, 'fetch', async () => { throw new Error('must not fetch') })
  const request = new Request('http://ui.test/api/ai/models')
  assert.equal((await proxyAi(request, 'models', async () => null)).status, 401)
  assert.equal((await proxyAi(new Request(request.url, { headers: { Origin: 'https://elsewhere.test' } }), 'models', session)).status, 403)
  assert.equal(fetch.mock.callCount(), 0)
})

test('admin request forwards once with scoped assertion', async (t) => {
  configure(t)
  const fetch = t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, 'http://backend.test:8000/v1/admin/ai/runs')
    assert.equal(options.headers.get('authorization'), 'Bearer test-backend-token')
    assert.ok(options.headers.get('x-admin-assertion'))
    assert.equal(options.headers.get('idempotency-key'), 'one')
    return Response.json({ run_id: 'ok' }, { status: 202 })
  })
  const response = await proxyAi(new Request('http://ui.test/api/ai/runs', {
    method: 'POST', headers: { Origin: 'http://ui.test', 'Idempotency-Key': 'one', 'Content-Type': 'application/json' }, body: '{}'
  }), 'runs', session)
  assert.equal(response.status, 202)
  assert.equal(fetch.mock.callCount(), 1)
})
