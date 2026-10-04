import test from 'node:test'
import assert from 'node:assert/strict'
import { fetchMetricRuns } from '../../src/lib/ai/metrics.ts'

test('metric drilldown forwards filters and pagination', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url) => {
    const params = new URL(url, 'http://localhost').searchParams
    assert.equal(params.get('provider'), 'groq')
    assert.equal(params.get('status'), 'failed')
    assert.equal(params.get('days'), '7')
    assert.equal(params.get('offset'), '20')
    assert.equal(params.get('limit'), '21')
    return Response.json([])
  })
  assert.deepEqual(await fetchMetricRuns({ days: 7, provider: 'groq', status: 'failed' }, 1), [])
})
