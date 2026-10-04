import * as z from 'zod'

export const backendStages = [
  'validando',
  'extrayendo',
  'fragmentando',
  'generando_vectores',
  'guardando',
  'publicando',
] as const
export const jobTimingsSchema = z.object({
  total_ms: z.number().nonnegative().nullable(),
  cola_inicial_ms: z.number().nonnegative().nullable(),
  activo_ms: z.number().nonnegative(),
  intentos: z.array(
    z.object({
      intento_id: z.uuid(),
      etapa: z.enum(backendStages),
      inicio: z.string(),
      fin: z.string().nullable(),
      duracion_ms: z.number().nonnegative().nullable(),
      transcurrido_ms: z.number().nonnegative().nullable(),
      resultado: z.enum([
        'en_curso',
        'completado',
        'fallido',
        'cancelado',
        'interrumpido',
      ]),
    }),
  ),
})
export type JobTimings = z.infer<typeof jobTimingsSchema>

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return 'Sin medición'
  if (ms < 1000) return `${Math.round(ms)} ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} s`
  const seconds = Math.floor(ms / 1000)
  return `${Math.floor(seconds / 60)} min ${seconds % 60} s`
}
