import { useJobTimings } from '#/hooks/use-job-timings'
import { formatDuration } from '#/lib/pdf-ingestion/timings'
import { pipelineStages } from '#/lib/admin-workspace/schema'
import type { IndexingJob } from '#/data/pdf-ingestion-jobs'

export function JobTimingSummary({ job }: { job: IndexingJob }) {
  const timing = useJobTimings(job)
  const outcomes = {
    completado: 'Completado',
    fallido: 'Fallido',
    cancelado: 'Cancelado',
    interrumpido: 'Interrumpido',
    en_curso: 'En curso',
  }
  return (
    <section
      aria-label="Tiempos de indexación"
      className="rounded-md border border-border bg-background/50 p-4"
    >
      <dl className="grid grid-cols-3 gap-3 text-xs text-muted-foreground">
        {[
          ['Tiempo total', timing.total],
          ['Ejecución de etapas', timing.active],
          ['Espera inicial', timing.queue],
        ].map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className="mt-1 text-base font-semibold tabular-nums text-foreground">
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">
        El total incluye las esperas entre etapas y reintentos. Las etapas
        muestran la suma de sus intentos medidos.
      </p>
      {!!job.timings?.intentos.length && (
        <details className="mt-3 text-xs">
          <summary className="min-h-7 cursor-pointer font-semibold text-primary">
            Ver tiempos por intento
          </summary>
          <ul className="mt-2 space-y-2">
            {timing.stages.flatMap((stage, index) =>
              stage.attempts.map((attempt, number) => (
                <li
                  key={attempt.intento_id}
                  className="flex flex-wrap justify-between gap-2 border-t border-border pt-2"
                >
                  <span>
                    {pipelineStages[index]} · intento {number + 1} ·{' '}
                    {outcomes[attempt.resultado]}
                  </span>
                  <span className="tabular-nums">
                    {formatDuration(
                      attempt.duracion_ms ?? attempt.transcurrido_ms,
                    )}
                  </span>
                </li>
              )),
            )}
          </ul>
        </details>
      )}
    </section>
  )
}
