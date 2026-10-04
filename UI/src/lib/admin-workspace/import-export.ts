import * as z from 'zod'
import { corpusDocumentSchema, chunkSchema } from './schema'
import type { CorpusDocument, WorkspaceSettings } from './schema'

const recordSchema = z.object({
  title: z.string().trim().min(1).max(300),
  text: z.string().trim().min(1).max(20000),
  page: z.number().int().min(1).max(2000).default(1),
  source: z.string().max(2048).default('Importación local'),
  category: z.string().max(80).default('Importado'),
  vector: chunkSchema.shape.vector,
})

export type ImportPreview = {
  format: string
  documents: CorpusDocument[]
}

function object(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function readCsv(text: string): Record<string, string>[] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let quoted = false
  const input = text.replace(/^\uFEFF/, '')
  for (let index = 0; index < input.length; index++) {
    const char = input[index]
    if (char === '"') {
      if (quoted && input[index + 1] === '"') {
        field += '"'
        index++
      } else if (quoted || field === '') {
        quoted = !quoted
      } else
        throw new Error(
          'CSV inválido: comillas fuera de un campo entrecomillado.',
        )
    } else if (char === ',' && !quoted) {
      row.push(field)
      field = ''
    } else if ((char === '\n' || char === '\r') && !quoted) {
      if (char === '\r' && input[index + 1] === '\n') index++
      row.push(field)
      if (row.some(Boolean)) rows.push(row)
      row = []
      field = ''
    } else field += char
  }
  if (quoted)
    throw new Error('CSV inválido: falta cerrar un campo entrecomillado.')
  row.push(field)
  if (row.some(Boolean)) rows.push(row)
  const [headers, ...body] = rows
  if (
    rows.length === 0 ||
    !headers.includes('text') ||
    !headers.includes('title')
  ) {
    throw new Error(
      'El CSV necesita las columnas title y text; page, source y category son opcionales.',
    )
  }
  return body.map((cells, index) => {
    if (cells.length !== headers.length)
      throw new Error('CSV inválido en la fila ' + (index + 2) + '.')
    return Object.fromEntries(
      headers.map((header, column) => [header.trim(), cells[column]]),
    )
  })
}

function recordsToDocuments(
  records: unknown[],
  settings: WorkspaceSettings,
): CorpusDocument[] {
  if (records.length === 0 || records.length > 5000) {
    throw new Error('Importa entre 1 y 5000 fragmentos por archivo.')
  }
  const grouped = new Map<string, CorpusDocument>()
  records.forEach((value, index) => {
    const item = object(value)
    const metadata = object(item.metadata)
    const candidate = {
      title: item.title ?? metadata.title ?? metadata.docTitle,
      text: item.text ?? metadata.text,
      page:
        item.page != null
          ? Number(item.page)
          : metadata.page != null
            ? Number(metadata.page)
            : 1,
      source: item.source ?? metadata.source,
      category: item.category ?? metadata.category,
      vector: item.vector ?? item.values,
    }
    const result = recordSchema.safeParse(candidate)
    if (!result.success) {
      throw new Error(
        'Registro ' +
          (index + 1) +
          ': ' +
          result.error.issues[0].message +
          '. Los vectores, si existen, deben tener 768 dimensiones.',
      )
    }
    const record = result.data
    const key = JSON.stringify([record.title, record.source, record.category])
    let document = grouped.get(key)
    if (!document) {
      document = {
        id: 'import-' + grouped.size,
        title: record.title,
        fileName: record.title,
        source: record.source,
        category: record.category,
        status: 'published',
        sample: false,
        indexedChunkSize: settings.chunkSize,
        indexedOverlap: settings.overlap,
        chunks: [],
      }
      grouped.set(key, document)
    }
    document.chunks.push({
      id: 'import-chunk-' + index,
      text: record.text,
      page: record.page,
      ...(record.vector ? { vector: record.vector } : {}),
    })
  })
  return z
    .array(corpusDocumentSchema)
    .max(200)
    .parse([...grouped.values()])
}

export function parseCorpusImport(
  text: string,
  fileName: string,
  settings: WorkspaceSettings,
): ImportPreview {
  let records: unknown[]
  let format = 'JSON'
  if (fileName.toLowerCase().endsWith('.csv')) {
    format = 'CSV'
    records = readCsv(text)
  } else if (fileName.toLowerCase().endsWith('.jsonl')) {
    format = 'JSONL'
    records = text
      .split(/\r?\n/)
      .filter((line) => line.trim())
      .map((line, index) => {
        try {
          return JSON.parse(line) as unknown
        } catch {
          throw new Error('JSONL inválido en la línea ' + (index + 1) + '.')
        }
      })
  } else {
    const parsed: unknown = JSON.parse(text)
    const root = object(parsed)
    if (root.format === 'sum-corpus-v1') {
      const documents = z
        .array(corpusDocumentSchema)
        .min(1)
        .max(200)
        .parse(root.documents)
      return { format: 'SUM JSON', documents }
    }
    if (root.vectors) {
      format = 'Pinecone JSON'
      records = Array.isArray(root.vectors)
        ? root.vectors
        : Object.values(object(root.vectors))
    } else if (Array.isArray(root.documents) && Array.isArray(root.ids)) {
      format = 'ChromaDB JSON'
      const texts = root.documents
      const metadata = Array.isArray(root.metadatas) ? root.metadatas : []
      const vectors = Array.isArray(root.embeddings) ? root.embeddings : []
      if (
        root.ids.length !== texts.length ||
        (vectors.length > 0 && vectors.length !== texts.length)
      ) {
        throw new Error(
          'ChromaDB: las listas de IDs, documentos y vectores deben tener la misma longitud.',
        )
      }
      records = texts.map((content, index) => ({
        ...object(metadata[index]),
        text: content,
        vector: vectors[index] ?? undefined,
      }))
    } else {
      records = Array.isArray(parsed)
        ? parsed
        : Array.isArray(root.records)
          ? root.records
          : [parsed]
    }
  }
  return { format, documents: recordsToDocuments(records, settings) }
}

function csvCell(value: string) {
  const safe = /^[=+@-]/.test(value) ? "'" + value : value
  return '"' + safe.replaceAll('"', '""') + '"'
}

export function serializeCorpus(
  documents: CorpusDocument[],
  format: 'json' | 'csv',
) {
  if (format === 'json') {
    return JSON.stringify({ format: 'sum-corpus-v1', documents }, null, 2)
  }
  return [
    ['title', 'text', 'page', 'source', 'category'].map(csvCell).join(','),
    ...documents.flatMap((doc) =>
      doc.chunks.map((chunk) =>
        [doc.title, chunk.text, String(chunk.page), doc.source, doc.category]
          .map(csvCell)
          .join(','),
      ),
    ),
  ].join('\r\n')
}

export function downloadCorpus(
  documents: CorpusDocument[],
  format: 'json' | 'csv',
) {
  const content = serializeCorpus(documents, format)
  const blob = new Blob([content], {
    type: format === 'json' ? 'application/json' : 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'sum-corpus.' + format
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
