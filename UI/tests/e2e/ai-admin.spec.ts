import { test, expect } from '@playwright/test'

const runId = '2ca19fd6-e1b6-4aad-8b8c-15a05944a85a'
const doc = 'e5a1b5dd-696c-4f0d-827c-6c1899e2e041'
const chunk = '8a4dafbf-2c3c-4a34-a316-d46fed6d8818'
const generation = '30ec3e04-30f1-4f87-a146-cd8af0e00327'
const version = '720f6f80-2c35-4961-85b8-77ba7a45f604'
const model = { provider: 'ollama', model: 'fixture', available: true, supports_tools: true,
  supports_structured_output: true, input_usd_per_million: 0, output_usd_per_million: 0,
  pricing_date: '2026-10-03' }
const evidence = { chunk_id: chunk, document_id: doc, version_id: version,
  generation_id: generation, page: 1, locator: 'p. 1', text: 'La publicación vigente permanece disponible.', rank: 1, score: 0.1 }
const { text: _text, rank: _rank, score: _score, ...citation } = evidence
const final = { run_id: runId, status: 'completed', stage: 'verifying', sequence: 2,
  question: '¿Qué publicación se consulta?', provider: 'ollama', model: 'fixture',
  result: { answer: 'Se consulta la publicación vigente.', citations: [citation], evidence: [evidence],
    provider: 'ollama', model: 'fixture', usage: { input_tokens: 180, output_tokens: 40, estimated_cost_usd: 0, pricing_date: '2026-10-03' },
    timings: { retrieving: 30 }, tool_trace: [], limitations: [], abstained: false, evaluation: null } }

test('admin pregunta, recibe SSE e inspecciona citas del backend', async ({ page }) => {
  await page.route('**/api/indexing/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    let body: unknown = []
    if (path.endsWith('/capabilities')) body = { env_mode: 'DEVELOPMENT', embedding_profile: { provider: 'tei', model: 'fixture-vector', revision: 'fixture-v1', dimension: 768, max_tokens: 512 }, stale_documents: 0 }
    if (path.endsWith('/documents')) body = { documentos: [{ documento_id: doc, version_id: version, trabajo_id: runId,
      metadatos: { titulo: 'Norma publicada', tipo_documento: 'otro' }, publicado_en: '2026-10-03T00:00:00Z', tamano_bytes: 100,
      fragmentos: 1, perfil: { model: 'fixture-vector', revision: 'fixture-v1', dimension: 768, max_tokens: 512 }, pipeline_version: 'v1' }], total: 1, fragmentos: 1, limite: 25, offset: 0 }
    if (path.endsWith('/indexing-jobs')) body = { trabajos: [], total: 0, limite: 25, offset: 0, estados: { queued: 0, processing: 0, published: 0, failed: 0, cancelled: 0 } }
    await route.fulfill({ json: body })
  })
  await page.route('**/api/ai/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/models')) return route.fulfill({ json: [model] })
    if (path.endsWith('/events')) return route.fulfill({ contentType: 'text/event-stream', body: 'id: 2\nevent: audit\ndata: ' + JSON.stringify({ sequence: 2, operation_id: 'run:completed', kind: 'completed', stage: 'verifying', payload: {}, created_at: '2026-10-03T00:00:00Z' }) + '\n\n' })
    if (route.request().method() === 'POST') {
      expect(route.request().postDataJSON().provider).toBe('ollama')
      expect(route.request().headers()['idempotency-key']).toBeTruthy()
      return route.fulfill({ status: 202, json: { run_id: runId, status: 'queued', sequence: 0 } })
    }
    return route.fulfill({ json: final })
  })
  await page.goto('/admin/chat')
  await expect(page).toHaveURL(/\/admin\/chat/)
  await expect(page.getByLabel('Tu pregunta')).toBeEnabled({ timeout: 45000 })
  await page.getByLabel('Tu pregunta').fill('¿Qué publicación se consulta?')
  await page.getByRole('button', { name: 'Enviar pregunta' }).click()
  await expect(page.getByText('Se consulta la publicación vigente.', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: /Documento .* página 1/ }).click()
  await expect(page.getByText(evidence.text, { exact: true })).toBeVisible()
  await expect(page.getByText(/Fragmento .* versión .* generación/)).toBeVisible()
  await expect(page.getByText(/Ejecución:/)).toBeVisible()
})
