import test from 'node:test'
import assert from 'node:assert/strict'
import {
  validatePdf,
  fileIdentity,
  MAX_PDF_BYTES,
  runConcurrent,
} from '../../src/lib/pdf-ingestion/files.ts'
import {
  backendJobSchema,
  mapBackendJob,
} from '../../src/lib/pdf-ingestion/backend.ts'
import {
  defaultSourceMetadata,
  sourceMetadataSchema,
  toBackendMetadata,
} from '../../src/lib/pdf-ingestion/schema.ts'
import { workspaceReducer } from '../../src/lib/admin-workspace/reducer.ts'

test('PDF header required even with a PDF extension and MIME type', async () => {
  assert.match(
    await validatePdf(
      new File(['plain text'], 'fake.pdf', { type: 'application/pdf' }),
    ),
    /cabecera/,
  )
  assert.equal(await validatePdf(new File(['%PDF-1.7\n'], 'valid.PDF')), null)
  assert.match(await validatePdf(new File([], 'empty.pdf')), /vacío/)
})

test('oversized files rejected before reading binary content', async () => {
  let read = false
  const file = {
    size: MAX_PDF_BYTES + 1,
    slice() {
      read = true
    },
  }
  assert.match(await validatePdf(file), /32 MB/)
  assert.equal(read, false)
})

test('file identity distinguishes same-name files with different sizes', () => {
  const first = { name: 'plan.pdf', size: 10, lastModified: 123 }
  assert.equal(fileIdentity(first), fileIdentity({ ...first }))
  assert.notEqual(fileIdentity(first), fileIdentity({ ...first, size: 20 }))
})

test('batch workers stay within concurrency limit and process each file once', async () => {
  let active = 0
  let peak = 0
  const completed = []
  await runConcurrent([0, 1, 2, 3, 4, 5, 6], 3, async (item) => {
    active++
    peak = Math.max(peak, active)
    await new Promise((resolve) => setImmediate(resolve))
    completed.push(item)
    active--
  })
  assert.equal(peak, 3)
  assert.deepEqual(completed.sort(), [0, 1, 2, 3, 4, 5, 6])
})

test('metadata uses actual backend names and omits absent optional fields', () => {
  assert.deepEqual(toBackendMetadata(' Plan ', defaultSourceMetadata), {
    titulo: 'Plan',
    tipo_documento: 'otro',
    prioridad: 'normal',
  })
  assert.equal(
    sourceMetadataSchema.safeParse({
      ...defaultSourceMetadata,
      originUrl: 'file:///source.pdf',
    }).success,
    false,
  )
})

const previous = {
  id: 'old',
  fileName: 'plan.pdf',
  originUrl: '',
  resolution: '',
  applicability: '',
  status: 'processing',
  updatedAt: 'Antes',
  progress: 75,
}
const response = {
  trabajo_id: 'f4a85fb6-c3e2-4c4e-9cff-caf2d5d817f7',
  documento_id: '3bc2425b-aa8a-4213-b3b4-79de4e8139e3',
  version_id: '2ca19fd6-e1b6-4aad-8b8c-15a05944a85a',
  estado: 'procesando',
  etapa: 'fragmentando',
  mensaje: 'Fragmentando',
  secuencia: 5,
  progreso: { paginas: 2 },
}

test('backend counters and stages preserved without inventing percentage progress', () => {
  const job = mapBackendJob(backendJobSchema.parse(response), previous)
  assert.equal(job.stage, 2)
  assert.equal(job.progress, undefined)
  assert.deepEqual(job.counts, { paginas: 2 })
  assert.equal(job.counts.vectores, undefined)
  assert.equal(
    backendJobSchema.safeParse({ ...response, estado: 'published' }).success,
    false,
  )
})

test('only backend completion maps to published; failure code retained', () => {
  assert.equal(
    mapBackendJob({ ...response, estado: 'completado' }, previous).status,
    'published',
  )
  const failed = mapBackendJob(
    { ...response, estado: 'fallido', codigo_error: 'REINTENTOS_AGOTADOS' },
    previous,
  )
  assert.equal(failed.status, 'failed')
  assert.equal(failed.errorCode, 'REINTENTOS_AGOTADOS')
})

test('late poll cannot overwrite a newer cancellation response', () => {
  const job = mapBackendJob(
    { ...response, estado: 'cancelado', secuencia: 8 },
    previous,
  )
  const state = { version: 1, settings: {}, documents: [], jobs: [job] }
  const late = mapBackendJob(response, previous)
  assert.equal(
    workspaceReducer(state, { type: 'upsert-job', job: late }),
    state,
  )
  const updated = workspaceReducer(state, {
    type: 'upsert-job',
    job: { ...job, sequence: 9 },
  })
  assert.equal(updated.jobs.length, 1)
  assert.equal(updated.jobs[0].sequence, 9)
})
