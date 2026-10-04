import { useWorkspace } from './workspace-provider'

export function DashboardPage({
  title,
  description,
  action,
  children,
}: {
  title: string
  description: string
  action?: React.ReactNode
  children: React.ReactNode
}) {
  const error = useWorkspace((store) => store.persistenceError)
  const loaded = useWorkspace((store) => store.loaded)
  return (
    <main className="mx-auto w-full max-w-[1200px] px-4 pb-12 pt-8 motion-safe:animate-[dashboard-rise-in_450ms_ease-out_both] sm:px-7 lg:px-8 lg:pt-10">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-[0.17em] text-muted-foreground">
            Base de conocimiento / Administración
          </p>
          <h1 className="font-display text-4xl font-medium leading-tight tracking-[-0.035em] sm:text-[2.75rem]">
            {title}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-6 text-muted-foreground">
            {description}
          </p>
        </div>
        {action}
      </header>
      <div className="mb-7 flex flex-wrap items-start justify-between gap-2 border-y border-border py-3 text-xs leading-5 text-muted-foreground">
        <p>
          Ingesta, seguimiento y biblioteca conectados al backend. Consultas de
          IA: muestra local sin validez académica.
        </p>
        <span>
          {loaded
            ? 'Preferencias guardadas en este navegador'
            : 'Cargando espacio…'}
        </span>
      </div>
      {error && (
        <p
          role="alert"
          className="mb-5 rounded-md border border-warning/40 bg-warning/5 p-4 text-sm text-warning"
        >
          {error}
        </p>
      )}
      {children}
    </main>
  )
}

export function MetricStrip({
  items,
}: {
  items: { label: string; value: React.ReactNode; detail?: string }[]
}) {
  return (
    <dl className="mb-8 grid grid-cols-2 gap-y-6 border-b border-border pb-7 sm:flex sm:divide-x sm:divide-border">
      {items.map((item) => (
        <div key={item.label} className="pr-6 sm:flex-1 sm:px-6 sm:first:pl-0">
          <dt className="text-sm text-muted-foreground">{item.label}</dt>
          <dd className="mt-1 font-display text-3xl tabular-nums">
            {item.value}
          </dd>
          {item.detail && (
            <p className="mt-1 text-xs text-muted-foreground">{item.detail}</p>
          )}
        </div>
      ))}
    </dl>
  )
}

export function EmptyState({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-dashed border-border px-6 py-14 text-center">
      <h2 className="font-display text-2xl">{title}</h2>
      <div className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">
        {children}
      </div>
    </div>
  )
}
