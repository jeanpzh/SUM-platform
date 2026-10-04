import { FileText } from 'lucide-react'
import type { RetrievalHit } from '#/lib/admin-workspace/retrieval'

export function SourceCitation({
  hit,
  number,
  onInspect,
}: {
  hit: RetrievalHit
  number: number
  onInspect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onInspect}
      className="flex max-w-full items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      <FileText size={14} className="shrink-0" aria-hidden="true" />
      <span>
        [{number}] {hit.document.title} · p. {hit.chunk.page}
      </span>
    </button>
  )
}
