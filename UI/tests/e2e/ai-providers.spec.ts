import { expect, test } from '@playwright/test'

const id = 'b81c1981-b01a-40bd-ac1f-c798727c756b'
test('Settings guarda Groq, edita sin devolver la clave y lo selecciona en RAG', async ({
  page,
}) => {
  let stored: Record<string, any> | null = null
  await page.route('**/api/indexing/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/capabilities'))
      return route.fulfill({
        json: {
          env_mode: 'DEVELOPMENT',
          embedding_profile: {
            provider: 'tei',
            model: 'fixture',
            revision: 'v1',
            dimension: 768,
            max_tokens: 512,
          },
          stale_documents: 0,
        },
      })
    if (path.endsWith('/documents'))
      return route.fulfill({
        json: {
          documentos: [],
          total: 0,
          fragmentos: 0,
          limite: 25,
          offset: 0,
        },
      })
    return route.fulfill({ json: [] })
  })
  await page.route('**/api/ai/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/providers/pricing'))
      return route.fulfill({
        json: {
          input_usd_per_million: 1,
          output_usd_per_million: 2,
          pricing_date: '2026-10-03',
          source: 'litellm-bundled',
        },
      })
    if (path.endsWith('/providers/test')) {
      const payload = route.request().postDataJSON()
      expect(payload.model).toBe('openai/gpt-oss-20b')
      expect(payload.api_key).toBe(stored ? '' : 'fixture-secret')
      return route.fulfill({
        json: {
          success: true,
          code: 'AI_CONNECTION_OK',
          latency_ms: 100,
          tools_supported: true,
          input_tokens: 10,
          output_tokens: 5,
        },
      })
    }
    if (path.endsWith('/models'))
      return route.fulfill({
        json: stored
          ? [
              {
                ...stored.models[0],
                provider: 'groq',
                available: stored.enabled,
                supports_tools: true,
                supports_structured_output: true,
                provider_config_id: id,
                provider_revision: stored.revision,
                connection_name: stored.name,
              },
            ]
          : [],
      })
    if (route.request().method() === 'POST') {
      const payload = route.request().postDataJSON()
      expect(payload.provider).toBe('groq')
      expect(payload.base_url).toBe('https://api.groq.com/openai/v1')
      expect(payload.models[0].model).toBe('openai/gpt-oss-20b')
      if (stored) {
        expect(payload.api_key).toBe('')
        expect(payload.expected_revision).toBe(1)
      } else expect(payload.api_key).toBe('fixture-secret')
      const { api_key: _key, expected_revision: _revision, ...safe } = payload
      stored = {
        ...safe,
        id,
        revision: stored ? 2 : 1,
        has_api_key: true,
        created_at: '2026-10-03T00:00:00Z',
      }
      return route.fulfill({ json: stored })
    }
    return route.fulfill({ json: stored ? [stored] : [] })
  })
  await page.goto('/admin/settings')
  await page
    .getByRole('button', { name: 'Añadir conexión', exact: true })
    .click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await dialog.getByLabel('Proveedor', { exact: true }).selectOption('groq')
  await dialog.getByLabel('API key', { exact: true }).fill('fixture-secret')
  await dialog.getByLabel('Modelo', { exact: true }).fill('openai/gpt-oss-20b')
  await dialog
    .getByRole('button', { name: 'Probar conexión', exact: true })
    .click()
  await expect(
    dialog.getByText('Conexión y llamada de herramienta verificadas.'),
  ).toBeVisible()
  await dialog
    .getByRole('button', { name: 'Añadir modelo', exact: true })
    .click()
  await dialog.getByText('Opciones avanzadas', { exact: true }).click()
  await dialog
    .getByLabel('Nombre de la conexión', { exact: true })
    .fill('Groq · admin')
  await dialog
    .getByRole('button', { name: 'Guardar conexión', exact: true })
    .click()
  await expect(dialog).not.toBeVisible()
  await expect(
    page.getByRole('status').filter({ hasText: 'revisión 1' }),
  ).toBeVisible()
  await page.reload()
  await page
    .getByRole('button', { name: 'Editar y probar Groq · admin', exact: true })
    .click()
  await expect(dialog.getByLabel('API key', { exact: true })).toHaveValue('')
  await dialog
    .getByRole('button', { name: 'Probar conexión', exact: true })
    .click()
  await expect(
    dialog.getByText('Conexión y llamada de herramienta verificadas.'),
  ).toBeVisible()
  await dialog.getByText('Opciones avanzadas', { exact: true }).click()
  await dialog.getByLabel('Prioridad', { exact: true }).selectOption('high')
  await dialog
    .getByRole('button', { name: 'Guardar conexión', exact: true })
    .click()
  await expect(dialog).not.toBeVisible()
  await page.goto('/admin/chat')
  await expect(page.getByLabel('Proveedor y modelo')).toHaveValue(
    `${id}:2:openai/gpt-oss-20b`,
  )
  await expect(page.getByLabel('Proveedor y modelo')).toContainText(
    'Groq · admin',
  )
})
