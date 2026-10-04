import test from 'node:test'
import assert from 'node:assert/strict'
import { fetchModels, createRun, getRun, AiHttpError } from '../../src/lib/ai/client.ts'

const model = { provider: 'ollama', model: 'llama3.2', available: true,
  supports_tools: true, supports_structured_output: true, pricing_date: '2026-10-03',
  input_usd_per_million: 0, output_usd_per_million: 0 }

test('catalog rejects malformed responses and accepts configured providers', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json([model]))
  assert.equal((await fetchModels())[0].provider, 'ollama')
  globalThis.fetch.mock.restore()
  t.mock.method(globalThis, 'fetch', async () => Response.json([{ provider: 'unknown' }]))
  await assert.rejects(fetchModels())
})

test('createRun forwards idempotency and parses run', async (t) => {
  t.mock.method(globalThis, 'fetch', async (_url, options) => {
    assert.equal(options.headers['Idempotency-Key'], 'stable')
    return Response.json({ run_id: '2ca19fd6-e1b6-4aad-8b8c-15a05944a85a', status: 'queued',
      sequence: 0 }, { status: 202 })
  })
  const run = await createRun({ question: 'Una pregunta', provider: 'ollama', model: 'llama3.2', top_k: 4, document_ids: [] }, 'stable')
  assert.equal(run.status, 'queued')
})

test('rate limit retains retry-after without exposing upstream body', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response('sensitive', { status: 429,
    headers: { 'Retry-After': '12' } }))
  await assert.rejects(getRun('2ca19fd6-e1b6-4aad-8b8c-15a05944a85a'),
    (error) => error instanceof AiHttpError && error.retryAfter === 12 && !error.message.includes('sensitive'))
})
