import test from 'node:test'
import assert from 'node:assert/strict'
import { fetchMetrics, latencyLabel } from '../../src/lib/ai/metrics.ts'

test('filters are encoded and missing labeled quality remains null', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url) => {
    assert.match(url, /days=7/)
    assert.match(url, /provider=openai/)
    return Response.json({ days: 7, summary: { count: 0, mean_ms: null, p50_ms: null, p95_ms: null,
      percentiles_approximate: true, statuses: {}, abstentions: 0, rate_limits: 0, timeouts: 0,
      input_tokens: 0, output_tokens: 0, estimated_cost_usd: 0, tool_calls: 0 }, stages: [], series: [], quality: null })
  })
  const data = await fetchMetrics({ days: 7, provider: 'openai' })
  assert.equal(data.quality, null)
  assert.equal(latencyLabel(null), 'Sin datos')
  assert.equal(latencyLabel(1000), '1.00 s')
})
