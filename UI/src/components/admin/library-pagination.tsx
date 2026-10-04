import { Button } from '#/components/ui/button'

export function LibraryPagination({
  total,
  offset,
  limit,
  busy,
  onChange,
}: {
  total: number
  offset: number
  limit: number
  busy: boolean
  onChange: (offset: number) => void
}) {
  if (total <= limit) return null
  return (
    <nav
      aria-label="Paginación"
      className="mt-5 flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground"
    >
      <span>
        {offset + 1}–{Math.min(offset + limit, total)} de {total}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          disabled={busy || offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          Anterior
        </Button>
        <Button
          variant="outline"
          disabled={busy || offset + limit >= total}
          onClick={() => onChange(offset + limit)}
        >
          Siguiente
        </Button>
      </div>
    </nav>
  )
}
