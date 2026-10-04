import * as z from 'zod'

export const sourceMetadataSchema = z.object({
  originUrl: z.union([
    z.literal(''),
    z
      .url()
      .refine(
        (value) => /^https?:\/\//i.test(value),
        'Usa una URL HTTP o HTTPS.',
      ),
  ]),
  resolution: z.string().trim().max(2048),
  documentType: z.enum([
    'plan_estudios',
    'reglamento',
    'resolucion',
    'directiva',
    'otro',
  ]),
  priority: z.enum(['alta', 'normal', 'baja']),
  testDocument: z.boolean().default(false),
})

export type SourceMetadata = z.infer<typeof sourceMetadataSchema>
export type SourceMetadataInput = z.input<typeof sourceMetadataSchema>

export const defaultSourceMetadata: SourceMetadata = {
  originUrl: '',
  resolution: '',
  documentType: 'otro',
  priority: 'normal',
  testDocument: false,
}

export function toBackendMetadata(title: string, metadata: SourceMetadata) {
  return {
    titulo: title.trim(),
    tipo_documento: metadata.documentType,
    prioridad: metadata.priority,
    ...(metadata.testDocument ? { es_prueba: true } : {}),
    ...(metadata.originUrl ? { fuente_url: metadata.originUrl } : {}),
    ...(metadata.resolution ? { codigo_documento: metadata.resolution } : {}),
  }
}
