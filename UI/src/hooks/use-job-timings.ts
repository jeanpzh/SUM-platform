import { useMemo } from 'react'
import { backendStages, formatDuration } from '#/lib/pdf-ingestion/timings'
import type { IndexingJob } from '#/data/pdf-ingestion-jobs'

export function useJobTimings(job: IndexingJob) {
  return useMemo(
    () => ({
      total: formatDuration(job.timings?.total_ms),
      queue: formatDuration(job.timings?.cola_inicial_ms),
      active: job.timings?.intentos.length
        ? formatDuration(job.timings.activo_ms)
        : 'Sin medición',
      stages: backendStages.map((stage) => {
        const attempts =
          job.timings?.intentos.filter((attempt) => attempt.etapa === stage) ??
          []
        const running = attempts.find(
          (attempt) => attempt.resultado === 'en_curso',
        )
        const measured = attempts.filter(
          (attempt) => attempt.duracion_ms !== null,
        )
        const ms = measured.reduce(
          (sum, attempt) => sum + (attempt.duracion_ms ?? 0),
          0,
        )
        return {
          attempts,
          duration: running
            ? `${formatDuration(ms + (running.transcurrido_ms ?? 0))} · en curso`
            : measured.length
              ? formatDuration(ms)
              : attempts.length
                ? 'Medición incompleta'
                : 'Sin medición',
          incomplete: attempts.some(
            (attempt) => attempt.resultado === 'interrumpido',
          ),
        }
      }),
    }),
    [job.timings],
  )
}
