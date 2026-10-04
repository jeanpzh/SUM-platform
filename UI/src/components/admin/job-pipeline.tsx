import { useJobTimings } from '#/hooks/use-job-timings'
import { Check } from 'lucide-react'
import { pipelineStages } from '#/lib/admin-workspace/schema'
import type { IndexingJob } from '#/data/pdf-ingestion-jobs'

export function JobPipeline({ job }: { job: IndexingJob }) {
  const timing = useJobTimings(job)
  return (
    <ol
      aria-label="Etapas de indexación"
      className="grid grid-cols-3 gap-x-4 gap-y-4 border-t border-border pt-5 sm:grid-cols-6"
    >
      {pipelineStages.map((stage, index) => {
        const complete =
          job.status === 'published' ||
          (typeof job.stage === 'number' && index < job.stage)
        const current = job.status === 'processing' && index === job.stage
        return (
          <li
            key={stage}
            aria-current={current ? 'step' : undefined}
            className={`text-xs ${current ? 'text-primary' : complete ? 'text-success' : 'text-muted-foreground'}`}
          >
            <div className="mb-2 flex items-center gap-2">
              <span
                className={`grid size-6 place-items-center rounded-full border ${current ? 'border-primary bg-primary/10' : 'border-border'}`}
              >
                {complete ? <Check size={13} aria-hidden="true" /> : index + 1}
              </span>
              <span className="h-px flex-1 bg-border" aria-hidden="true" />
            </div>
            {stage}
            {job.source === 'backend' && (
              <span
                data-testid="stage-duration"
                className="mt-1 block text-[0.7rem] tabular-nums text-muted-foreground"
              >
                {timing.stages[index].duration}
                {timing.stages[index].attempts.length > 1 && (
                  <span className="block">
                    {timing.stages[index].attempts.length} intentos
                  </span>
                )}
                {timing.stages[index].incomplete && (
                  <span className="block">Incluye un intento sin cierre</span>
                )}
              </span>
            )}
            <span className="sr-only">
              {complete
                ? ', completa'
                : current
                  ? ', en curso'
                  : ', sin completar'}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
