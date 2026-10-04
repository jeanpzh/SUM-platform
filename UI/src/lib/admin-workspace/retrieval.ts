import type { CorpusChunk, CorpusDocument, WorkspaceSettings } from './schema'

export type RetrievalHit = {
  document: CorpusDocument
  chunk: CorpusChunk
  score: number
}

const stopWords = new Set([
  'que',
  'como',
  'cuando',
  'donde',
  'cual',
  'cuales',
  'para',
  'por',
  'con',
  'del',
  'los',
  'las',
  'una',
  'uno',
  'unos',
  'unas',
  'este',
  'esta',
  'son',
  'es',
  'el',
  'la',
  'de',
  'en',
  'se',
  'un',
  'y',
  'al',
  'lo',
  'a',
])

function tokens(text: string) {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((word) => word.length > 2 && !stopWords.has(word))
}

export function retrieveChunks(
  query: string,
  documents: CorpusDocument[],
  settings: Pick<WorkspaceSettings, 'topK' | 'minMatch'>,
  documentId = 'all',
): RetrievalHit[] {
  const terms = [...new Set(tokens(query))]
  if (terms.length === 0) return []

  return documents
    .filter(
      (doc) =>
        doc.status === 'published' &&
        (documentId === 'all' || doc.id === documentId),
    )
    .flatMap((document) =>
      document.chunks.map((chunk) => {
        const content = new Set(tokens(chunk.text + ' ' + document.title))
        const matched = terms.filter((term) => content.has(term)).length
        return { document, chunk, score: matched / terms.length }
      }),
    )
    .filter((hit) => hit.score > 0 && hit.score >= settings.minMatch)
    .sort((a, b) => b.score - a.score || a.chunk.page - b.chunk.page)
    .slice(0, settings.topK)
}
