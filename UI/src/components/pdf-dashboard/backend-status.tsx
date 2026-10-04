import { CircleCheck, CircleAlert, LoaderCircle } from 'lucide-react'
import { useWorkspace } from '#/components/admin/workspace-provider'

export function BackendStatus() {
  const status = useWorkspace((store) => store.backendStatus)
  const error = useWorkspace((store) => store.backendError)
  const Icon =
    status === 'ready'
      ? CircleCheck
      : status === 'checking'
        ? LoaderCircle
        : CircleAlert
  return (
    <span
      role="status"
      data-testid="backend-status"
      title={error || undefined}
      className={`inline-flex min-h-9 items-center gap-2 text-xs ${status === 'ready' ? 'text-success' : status === 'unavailable' ? 'text-warning' : 'text-muted-foreground'}`}
    >
      <Icon
        size={15}
        aria-hidden="true"
        className={
          status === 'checking' ? 'motion-safe:animate-spin' : undefined
        }
      />
      {status === 'ready'
        ? 'Servicio de ingesta disponible'
        : status === 'checking'
          ? 'Comprobando servicio…'
          : 'Servicio de ingesta no disponible'}
    </span>
  )
}
