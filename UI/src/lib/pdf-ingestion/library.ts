import * as z from 'zod'

export const publishedDocumentSchema = z.object({
  documento_id: z.uuid(),
  version_id: z.uuid(),
  trabajo_id: z.uuid(),
  metadatos: z
    .object({
      titulo: z.string(),
      tipo_documento: z.string(),
      fuente_url: z.string().nullable().optional(),
      codigo_documento: z.string().nullable().optional(),
      institucion: z.string().optional(),
    })
    .passthrough(),
  publicado_en: z.string(),
  tamano_bytes: z.number().nonnegative(),
  fragmentos: z.number().int().nonnegative(),
  perfil: z.object({
    model: z.string(),
    revision: z.string(),
    dimension: z.number().int(),
    max_tokens: z.number().int(),
  }),
  pipeline_version: z.string(),
})
export const publishedCatalogueSchema = z.object({
  documentos: z.array(publishedDocumentSchema),
  total: z.number().int().nonnegative(),
  fragmentos: z.number().int().nonnegative(),
  limite: z.number().int(),
  offset: z.number().int(),
})
export const publishedChunksSchema = z.object({
  documento: publishedDocumentSchema,
  total: z.number().int().nonnegative(),
  limite: z.number().int(),
  offset: z.number().int(),
  fragmentos: z.array(
    z.object({
      id: z.string(),
      ordinal: z.number().int(),
      pagina: z.number().int(),
      ubicacion: z.string(),
      texto: z.string(),
      tokens: z.number().int(),
      metadatos: z.record(z.string(), z.unknown()),
    }),
  ),
})
export type PublishedDocument = z.infer<typeof publishedDocumentSchema>
export type PublishedCatalogue = z.infer<typeof publishedCatalogueSchema>
export type PublishedChunks = z.infer<typeof publishedChunksSchema>

async function readPublished(
  path: string,
  signal?: AbortSignal,
): Promise<unknown> {
  const response = await fetch('/api/indexing/' + path, { signal })
  const data: unknown = await response.json()
  if (!response.ok) {
    const error = z.object({ mensaje: z.string() }).safeParse(data)
    throw new Error(
      error.success
        ? error.data.mensaje
        : 'No se pudo leer la biblioteca publicada.',
    )
  }
  return data
}
export async function fetchPublishedDocuments(
  query: string,
  offset: number,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    q: query,
    offset: String(offset),
    limit: '25',
  })
  return publishedCatalogueSchema.parse(
    await readPublished('documents?' + params, signal),
  )
}
export async function fetchPublishedChunks(
  document: PublishedDocument,
  offset: number,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: '20',
    version_id: document.version_id,
  })
  return publishedChunksSchema.parse(
    await readPublished(
      `documents/${document.documento_id}/chunks?${params}`,
      signal,
    ),
  )
}
