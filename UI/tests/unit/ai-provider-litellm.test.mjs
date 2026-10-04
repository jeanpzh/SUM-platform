import test from 'node:test'
import assert from 'node:assert/strict'
import {
  fetchModelPricing,
  probeMessage,
  testProvider,
} from '../../src/lib/ai/providers.ts'
import { proxyAi } from '../../src/lib/ai/proxy.server.ts'

test('automatic pricing preserves unknown rates instead of inventing zero', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url) => {
    const query = new URL(url, 'http://localhost').searchParams
    assert.equal(query.get('provider'), 'groq')
    assert.equal(query.get('model'), 'unknown')
    return Response.json({
      input_usd_per_million: null,
      output_usd_per_million: null,
      pricing_date: '2026-10-03',
      source: 'litellm-bundled',
    })
  })
  assert.equal(
    (await fetchModelPricing('groq', 'unknown')).input_usd_per_million,
    null,
  )
})

test('connection probe forwards a draft with retained-key revision and reads safe result', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/ai/providers/test')
    const data = JSON.parse(options.body)
    assert.equal(data.api_key, '')
    assert.equal(data.expected_revision, 2)
    return Response.json({
      success: false,
      code: 'AI_PROVIDER_AUTH_FAILED',
      latency_ms: 50,
      tools_supported: false,
      input_tokens: 0,
      output_tokens: 0,
    })
  })
  const result = await testProvider({
    provider: 'groq',
    model: 'openai/gpt-oss-20b',
    base_url: 'https://api.groq.com/openai/v1',
    api_key: '',
    config_id: 'b81c1981-b01a-40bd-ac1f-c798727c756b',
    expected_revision: 2,
  })
  assert.equal(result.success, false)
  assert.match(probeMessage(result), /API key/)
})

test('AI proxy allows exact probe and pricing routes with scoped assertions', async (t) => {
  const names = ['BACKEND_API_URL', 'BACKEND_ADMIN_TOKEN', 'AI_IDENTITY_SECRET']
  const previous = Object.fromEntries(
    names.map((name) => [name, process.env[name]]),
  )
  Object.assign(process.env, {
    BACKEND_API_URL: 'http://backend.test',
    BACKEND_ADMIN_TOKEN: 'test-token',
    AI_IDENTITY_SECRET: 'test-secret-with-sufficient-length',
  })
  t.after(() => {
    for (const name of names) {
      if (previous[name] === undefined) delete process.env[name]
      else process.env[name] = previous[name]
    }
  })
  const session = async () => ({ id: 'admin', email: 'admin@example.test' })
  const mocked = t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.ok(options.headers.get('x-admin-assertion'))
    return Response.json({ ok: true })
  })
  const post = new Request('http://ui.test/api/ai/providers/test', {
    method: 'POST',
    body: '{}',
  })
  assert.equal((await proxyAi(post, 'providers/test', session)).status, 200)
  const get = new Request(
    'http://ui.test/api/ai/providers/pricing?provider=groq&model=fixture',
  )
  assert.equal((await proxyAi(get, 'providers/pricing', session)).status, 200)
  assert.equal(
    (
      await proxyAi(
        new Request('http://ui.test/api/ai/providers/test'),
        'providers/test',
        session,
      )
    ).status,
    404,
  )
  assert.equal(mocked.mock.callCount(), 2)
})
