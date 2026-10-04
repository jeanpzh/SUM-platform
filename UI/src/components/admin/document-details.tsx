import { FileText, ArrowUpRight } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '#/components/ui/sheet'
import { Button } from '#/components/ui/button'
import type { CorpusDocument } from '#/lib/admin-workspace/schema'

export function DocumentDetails({
  document,
  onClose,
  focusChunkId,
}: {
  document: CorpusDocument | null
  onClose: () => void
  focusChunkId?: string
}) {
  return (
    <Sheet
      open={!!document}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-xl">
        <SheetHeader className="border-b border-border px-6 py-7 pr-12">
          <SheetTitle className="font-display text-2xl">
            {document?.title}
          </SheetTitle>
          <SheetDescription>
            {document?.sample
              ? 'Muestra local · localizadores de demostración.'
              : 'Documento importado · verifica el origen antes de usarlo.'}
          </SheetDescription>
        </SheetHeader>
        {document && (
          <div className="space-y-6 p-6">
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">Origen</dt>
                <dd className="mt-1 break-all">{document.source}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Colección</dt>
                <dd className="mt-1">{document.category}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">
                  Fragmentación declarada
                </dt>
                <dd className="mt-1">
                  {document.indexedChunkSize} / {document.indexedOverlap} tokens
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Vectores importados</dt>
                <dd className="mt-1">
                  {document.chunks.filter((chunk) => chunk.vector).length} de{' '}
                  {document.chunks.length}
                </dd>
              </div>
            </dl>
            {/^https?:\/\//i.test(document.source) && (
              <Button variant="outline" asChild>
                <a
                  href={document.source}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Abrir fuente <ArrowUpRight size={16} />
                </a>
              </Button>
            )}
            <h2 className="border-t border-border pt-5 text-sm font-semibold">
              Fragmentos del documento
            </h2>
            {[...document.chunks]
              .sort(
                (a, b) =>
                  Number(b.id === focusChunkId) - Number(a.id === focusChunkId),
              )
              .map((chunk) => (
                <article
                  key={chunk.id}
                  className={`rounded-md border p-4 ${chunk.id === focusChunkId ? 'border-primary bg-primary/5' : 'border-border bg-card'}`}
                >
                  <p className="mb-3 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
                    <FileText size={14} />
                    Página {chunk.page} · {chunk.id}
                  </p>
                  <p className="whitespace-pre-wrap text-sm leading-7">
                    {chunk.text}
                  </p>
                </article>
              ))}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
