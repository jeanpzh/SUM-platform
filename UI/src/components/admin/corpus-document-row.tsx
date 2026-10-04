import { Archive, FileText, RotateCcw } from 'lucide-react'
import { Button } from '#/components/ui/button'
import type { CorpusDocument } from '#/lib/admin-workspace/schema'

export function CorpusDocumentRow({
  document,
  selected,
  onSelect,
  onInspect,
  onArchive,
}: {
  document: CorpusDocument
  selected: boolean
  onSelect: () => void
  onInspect: () => void
  onArchive: () => void
}) {
  return (
    <article
      className={`flex items-start gap-3 border-b border-border px-4 py-5 last:border-0 sm:gap-4 sm:px-6 ${selected ? 'bg-primary/5' : ''}`}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={onSelect}
        aria-label={`Seleccionar ${document.title}`}
        className="mt-1 size-4 shrink-0 accent-primary"
      />
      <FileText
        size={22}
        strokeWidth={1.4}
        className="mt-1 hidden shrink-0 text-muted-foreground sm:block"
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1">
        <button
          type="button"
          onClick={onInspect}
          className="text-left font-semibold hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {document.title}
        </button>
        <p className="mt-1 break-all text-xs text-muted-foreground">
          {document.source}
        </p>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>{document.category}</span>
          <span>{document.chunks.length} fragmentos</span>
          <span>
            {document.chunks.filter((chunk) => chunk.vector).length} vectores
            importados
          </span>
          <span
            className={document.status === 'published' ? 'text-success' : ''}
          >
            {document.status === 'published' ? 'Publicado' : 'Archivado'}
          </span>
          {document.sample && <span>Muestra</span>}
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="size-11 shrink-0"
        aria-label={`${document.status === 'published' ? 'Archivar' : 'Restaurar'} ${document.title}`}
        onClick={onArchive}
      >
        {document.status === 'published' ? (
          <Archive size={16} />
        ) : (
          <RotateCcw size={16} />
        )}
      </Button>
    </article>
  )
}
