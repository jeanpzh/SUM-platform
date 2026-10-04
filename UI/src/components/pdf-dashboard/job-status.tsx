import {
  AlertCircle,
  Check,
  Clock3,
  LoaderCircle,
  CircleSlash,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Progress } from '#/components/ui/progress'
import type { JobStatus } from '#/data/pdf-ingestion-jobs'

type JobStatusProps = {
  status: JobStatus
  progress?: number
  note?: string
}

const statusPresentation: Record<
  JobStatus,
  { label: string; icon: typeof Clock3; className: string }
> = {
  queued: {
    label: 'En cola',
    icon: Clock3,
    className: 'text-muted-foreground',
  },
  processing: {
    label: 'Indexando',
    icon: LoaderCircle,
    className: 'text-primary',
  },
  published: {
    label: 'Publicado',
    icon: Check,
    className: 'text-success',
  },
  failed: {
    label: 'Indexación fallida',
    icon: AlertCircle,
    className: 'text-destructive',
  },
  cancelled: {
    label: 'Cancelado',
    icon: CircleSlash,
    className: 'text-muted-foreground',
  },
}

export function JobStatusView({ status, progress, note }: JobStatusProps) {
  const presentation = statusPresentation[status]
  const Icon = presentation.icon

  return (
    <div className="min-w-0">
      <div
        className={`flex items-center gap-2 text-sm font-semibold ${presentation.className}`}
      >
        <Icon
          size={17}
          strokeWidth={1.7}
          aria-hidden="true"
          className={
            status === 'processing'
              ? 'animate-spin [animation-duration:2.4s]'
              : ''
          }
        />
        <span>{presentation.label}</span>
        {status === 'processing' && typeof progress === 'number' && (
          <Badge
            variant="outline"
            className="h-5 rounded-full border-primary/40 bg-primary-soft px-2 text-[0.68rem] font-semibold text-primary"
          >
            {progress}%
          </Badge>
        )}
      </div>
      {status === 'processing' && typeof progress === 'number' && (
        <Progress
          value={progress}
          aria-label={`Indexando, ${progress}%`}
          className="mt-2 h-1.5 bg-muted [&_[data-slot=progress-indicator]]:bg-primary"
        />
      )}
      {note && (
        <p className="mb-0 mt-1 text-xs leading-5 text-muted-foreground">
          {note}
        </p>
      )}
    </div>
  )
}
