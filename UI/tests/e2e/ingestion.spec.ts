import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import path from 'node:path'

const originals = path.resolve('../sources/originals')
const fileOne = path.join(originals, 'Directiva-SUM-006-rectificacion.pdf')
const fileTwo = path.join(originals, 'RR-000046-2026-R-UNMSM.pdf')

async function ready(page: Page) {
  await expect(page.getByTestId('backend-status')).toContainText(
    'Servicio de ingesta disponible',
  )
  await expect(
    page.getByRole('button', { name: 'Conectar backend', exact: true }),
  ).toHaveCount(0)
  await expect(
    page.getByLabel('Credencial de administración', { exact: true }),
  ).toHaveCount(0)
}

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(
    page.getByRole('heading', {
      name: 'Documentos institucionales',
      exact: true,
    }),
  ).toBeVisible()
  await expect(
    page.getByText('Preferencias guardadas en este navegador', { exact: true }),
  ).toBeVisible()
  await ready(page)
})

test('selección múltiple, duplicados, validación individual y eliminación', async ({
  page,
}) => {
  const picker = page.getByLabel('Seleccionar archivos PDF', { exact: true })
  await picker.setInputFiles([fileOne, fileTwo])
  const rows = page.getByTestId('pdf-file-row')
  await expect(rows).toHaveCount(2)
  await expect(rows.first().getByRole('status')).toContainText(
    'Listo para cargar',
  )
  await picker.setInputFiles(fileOne)
  await expect(rows).toHaveCount(2)
  await expect(
    page.getByText('1 archivos ya estaban adjuntados.', { exact: true }),
  ).toBeVisible()
  await picker.setInputFiles({
    name: 'contenido-invalido.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('No es un PDF'),
  })
  await expect(rows).toHaveCount(3)
  await expect(rows.last().getByRole('alert')).toContainText(
    'cabecera PDF válida',
  )
  await rows
    .last()
    .getByRole('button', { name: 'Quitar contenido-invalido.pdf' })
    .click()
  await expect(rows).toHaveCount(2)
  await expect(
    page.getByRole('button', { name: 'Iniciar ingesta (2)', exact: true }),
  ).toBeEnabled()
  await page.getByRole('button', { name: 'Limpiar lista', exact: true }).click()
  await expect(rows).toHaveCount(0)
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true)
})

test('conexión automática al recargar, credencial solo en servidor y tema oscuro', async ({
  page,
}) => {
  const credentials: (string | undefined)[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/indexing/'))
      credentials.push(request.headers()['authorization'])
  })
  const response = await page.request.get('/api/indexing/connection')
  expect(response.ok()).toBe(true)
  expect(await response.json()).toEqual({ estado: 'disponible' })
  const token = process.env.E2E_ADMIN_TOKEN!
  expect(token).toBeTruthy()
  expect(await page.content()).not.toContain(token)
  const persisted = await page.evaluate(() =>
    JSON.stringify(window.localStorage),
  )
  expect(persisted).not.toContain(token)
  await page.reload()
  await ready(page)
  await page
    .getByRole('button', { name: 'Cambiar apariencia', exact: true })
    .first()
    .click()
  await page.getByRole('menuitem', { name: 'Oscuro', exact: true }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  expect(credentials.length).toBeGreaterThan(0)
  expect(credentials.every((value) => value === undefined)).toBe(true)
})

test('dos PDF reales, tiempos por etapa y publicación en Biblioteca', async ({
  page,
}, testInfo) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await page
    .getByLabel('Seleccionar archivos PDF', { exact: true })
    .setInputFiles([fileOne, fileTwo])
  const rows = page.getByTestId('pdf-file-row')
  await expect(rows.first().getByRole('status')).toContainText(
    'Listo para cargar',
  )
  await expect(rows.last().getByRole('status')).toContainText(
    'Listo para cargar',
  )
  const label = `E2E ${testInfo.project.name} ${Date.now()}`
  await rows
    .first()
    .getByLabel('Título del documento', { exact: true })
    .fill(label + ' rectificación')
  await rows
    .last()
    .getByLabel('Título del documento', { exact: true })
    .fill(label + ' resolución')
  await page
    .getByLabel('Tipo de documento', { exact: true })
    .selectOption('resolucion')
  await page
    .getByLabel('Origen oficial', { exact: true })
    .fill('https://sum.unmsm.edu.pe')
  await page
    .getByRole('button', { name: 'Iniciar ingesta (2)', exact: true })
    .click()
  await expect(rows.first().getByRole('link')).toBeVisible()
  await expect(rows.last().getByRole('link')).toBeVisible()
  const links = await rows
    .getByRole('link')
    .evaluateAll((elements) =>
      elements.map((element) => (element as HTMLAnchorElement).href),
    )
  const ids = links.map((url) => new URL(url).searchParams.get('job')!)
  expect(new Set(ids).size).toBe(2)
  await rows.first().getByRole('link').click()
  await expect(page).toHaveURL(new RegExp('job=' + ids[0]))
  const publishedDocuments: string[] = []
  for (const id of ids) {
    const job = page.locator(`[data-job-id="${id}"]`)
    await expect(job.getByText('Publicado', { exact: true })).toBeVisible({
      timeout: 150000,
    })
    await expect(
      job.getByLabel('Etapas de indexación').locator('li'),
    ).toHaveCount(6)
    await expect(
      job.getByLabel('Contadores reportados por el backend'),
    ).toBeVisible()
    await expect(
      job.getByRole('button', { name: 'Cancelar solicitud', exact: true }),
    ).toHaveCount(0)
    const confirmed = await page.request.get('/api/indexing/jobs/' + id)
    expect(confirmed.ok()).toBe(true)
    const result = await confirmed.json()
    expect(result.estado).toBe('completado')
    expect(result.progreso.paginas).toBe(2)
    expect(result.progreso.fragmentos).toBeGreaterThan(0)
    expect(result.progreso.vectores).toBe(result.progreso.fragmentos)
    publishedDocuments.push(result.documento_id as string)
    await expect
      .poll(async () => {
        const response = await page.request.get('/api/indexing/jobs/' + id)
        const data = await response.json()
        return (
          data.tiempos.intentos.length === 6 &&
          data.tiempos.intentos.every(
            (attempt: { resultado: string; duracion_ms: number | null }) =>
              attempt.resultado === 'completado' &&
              attempt.duracion_ms !== null &&
              attempt.duracion_ms >= 0,
          )
        )
      })
      .toBe(true)
    await expect(job.getByTestId('stage-duration')).toHaveCount(6)
    await expect(
      job.getByTestId('stage-duration').filter({ hasText: 'Sin medición' }),
    ).toHaveCount(0)
    await expect(job.getByLabel('Tiempos de indexación')).toContainText(
      'Tiempo total',
    )
  }
  expect(pageErrors).toEqual([])
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true)
  await testInfo.attach('indexacion-publicada', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
  await page.reload()
  await ready(page)
  await expect(page.getByTestId('stage-duration')).toHaveCount(12)
  await expect(
    page.getByTestId('stage-duration').filter({ hasText: 'Sin medición' }),
  ).toHaveCount(0)
  await page.goto('/admin/library')
  await ready(page)
  await page.getByLabel('Buscar documentos', { exact: true }).fill(label)
  const published = page.getByTestId('published-document')
  await expect(published).toHaveCount(2)
  const actualIds = await published.evaluateAll((rows) =>
    rows.map((row) => row.getAttribute('data-document-id')),
  )
  expect(new Set(actualIds)).toEqual(new Set(publishedDocuments))
  await published
    .filter({ hasText: label + ' rectificación' })
    .getByRole('button', { name: label + ' rectificación', exact: true })
    .click()
  await expect(page.getByTestId('published-chunk').first()).toBeVisible()
  const realChunks = await page.request.get(
    `/api/indexing/documents/${publishedDocuments[0]}/chunks`,
  )
  expect(realChunks.ok()).toBe(true)
  const chunks = await realChunks.json()
  expect(chunks.fragmentos.length).toBeGreaterThan(0)
  await expect(page.getByTestId('published-chunk').first()).toContainText(
    chunks.fragmentos[0].texto,
  )
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Close', exact: true })
    .click()
  // Published documents must also be visible without the local job history.
  await page.evaluate(() => localStorage.removeItem('sum-admin-workspace-v1'))
  await page.reload()
  await ready(page)
  await page.getByLabel('Buscar documentos', { exact: true }).fill(label)
  await expect(published).toHaveCount(2)
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true)
  await testInfo.attach('biblioteca-publicada', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

test('cancelación real y reintento como nueva versión del mismo documento', async ({
  page,
}) => {
  await page
    .getByLabel('Seleccionar archivos PDF', { exact: true })
    .setInputFiles(fileOne)
  await expect(
    page.getByTestId('pdf-file-row').getByRole('status'),
  ).toContainText('Listo para cargar')
  await page
    .getByRole('button', { name: 'Iniciar ingesta (1)', exact: true })
    .click()
  const link = page.getByTestId('pdf-file-row').getByRole('link')
  await expect(link).toBeVisible()
  const jobId = new URL(
    (await link.getAttribute('href'))!,
    'http://localhost',
  ).searchParams.get('job')!
  await link.click()
  const job = page.locator(`[data-job-id="${jobId}"]`)
  await job
    .getByRole('button', { name: 'Cancelar solicitud', exact: true })
    .click()
  await expect(job.getByText('Cancelado', { exact: true })).toBeVisible()
  await job.getByRole('button', { name: 'Reintentar', exact: true }).click()
  await expect(page.getByTestId('indexing-job')).toHaveCount(2)
  const oldDocumentId = await page.evaluate((id) => {
    const state = JSON.parse(localStorage.getItem('sum-admin-workspace-v1')!)
    return state.jobs.find((item: { id: string }) => item.id === id)
      .documentId as string
  }, jobId)
  const allDocumentIds = await page.evaluate(() => {
    const state = JSON.parse(localStorage.getItem('sum-admin-workspace-v1')!)
    return state.jobs.map(
      (item: { documentId: string }) => item.documentId,
    ) as string[]
  })
  expect(allDocumentIds).toEqual([oldDocumentId, oldDocumentId])
  const versions = await page.evaluate(() => {
    const state = JSON.parse(localStorage.getItem('sum-admin-workspace-v1')!)
    return state.jobs.map(
      (item: { versionId: string }) => item.versionId,
    ) as string[]
  })
  expect(new Set(versions).size).toBe(2)
  await expect(
    page
      .getByTestId('indexing-job')
      .first()
      .getByText('Publicado', { exact: true }),
  ).toBeVisible({ timeout: 150000 })
  await page.reload()
  await ready(page)
  await expect(
    job.getByRole('button', {
      name: 'Adjuntar original y reintentar',
      exact: true,
    }),
  ).toBeEnabled()
})

test('respuesta de carga perdida: reintento idempotente sin duplicar trabajo', async ({
  page,
}) => {
  const ids: string[] = []
  const keys: string[] = []
  page.on('response', async (response) => {
    if (!response.url().endsWith('/api/indexing/documents')) return
    keys.push(response.request().headers()['idempotency-key'])
    ids.push((await response.json()).trabajo_id as string)
  })
  // Let Chromium send the real multipart upload; lose its first confirmation
  // at the transport boundary. Route.fetch omits browser file-backed bytes.
  await page.evaluate(() => {
    const send = XMLHttpRequest.prototype.send
    let firstUpload = true
    XMLHttpRequest.prototype.send = function (body) {
      if (firstUpload && body instanceof FormData && body.has('archivo')) {
        firstUpload = false
        this.onload = () => {
          this.onerror?.(new ProgressEvent('error'))
        }
      }
      return send.call(this, body)
    }
  })
  await page
    .getByLabel('Seleccionar archivos PDF', { exact: true })
    .setInputFiles(fileTwo)
  await expect(
    page.getByTestId('pdf-file-row').getByRole('status'),
  ).toContainText('Listo para cargar')
  await page
    .getByRole('button', { name: 'Iniciar ingesta (1)', exact: true })
    .click()
  await expect(
    page.getByTestId('pdf-file-row').getByRole('alert'),
  ).toContainText('No se pudo confirmar')
  await page
    .getByRole('button', { name: 'Iniciar ingesta (1)', exact: true })
    .click()
  await expect(page.getByTestId('pdf-file-row').getByRole('link')).toBeVisible()
  await expect.poll(() => ids.length).toBe(2)
  expect(ids[0]).toMatch(/^[0-9a-f-]{36}$/)
  expect(ids[0]).toBe(ids[1])
  expect(keys[0]).toBe(keys[1])
  await page.getByTestId('pdf-file-row').getByRole('link').click()
  await expect(page.getByTestId('indexing-job')).toHaveCount(1)
})

test('servicio temporalmente no disponible: conserva archivos y se recupera automáticamente', async ({
  page,
}) => {
  let unavailable = true
  await page.route('**/api/indexing/connection', async (route) => {
    if (unavailable)
      await route.fulfill({
        status: 503,
        json: { mensaje: 'Servicio temporalmente no disponible.' },
      })
    else await route.continue()
  })
  await page.reload()
  await expect(page.getByTestId('backend-status')).toContainText(
    'Servicio de ingesta no disponible',
  )
  await page
    .getByLabel('Seleccionar archivos PDF', { exact: true })
    .setInputFiles(fileOne)
  await expect(
    page.getByTestId('pdf-file-row').getByRole('status'),
  ).toContainText('Listo para cargar')
  const submit = page.getByRole('button', {
    name: 'Iniciar ingesta (1)',
    exact: true,
  })
  await expect(submit).toBeDisabled()
  await expect(page.getByRole('alert')).toContainText(
    'Comprobaremos el servicio de nuevo automáticamente',
  )
  unavailable = false
  await ready(page)
  await expect(submit).toBeEnabled()
  await expect(page.getByTestId('pdf-file-row')).toHaveCount(1)
})
