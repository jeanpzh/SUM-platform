import { ArrowUpRight, FileText } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '#/components/ui/sheet'
import { Button } from '#/components/ui/button'
import { usePublishedChunks } from '#/hooks/use-published-chunks'
import type { PublishedDocument } from '#/lib/pdf-ingestion/library'
import { LibraryPagination } from './library-pagination'

function PublishedChunks({ document }: { document: PublishedDocument }) {
  const chunks = usePublishedChunks(document)
  return (
    <div className="space-y-5 p-6">
      <dl className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-muted-foreground">Tipo</dt>
          <dd className="mt-1">{document.metadatos.tipo_documento}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Fragmentos publicados</dt>
          <dd className="mt-1">{document.fragmentos}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-muted-foreground">Modelo de embeddings</dt>
          <dd className="mt-1 break-all">
            {document.perfil.model} · {document.perfil.dimension} dimensiones
          </dd>
        </div>
        <div className="col-span-2">
          <dt className="text-muted-foreground">Versión publicada</dt>
          <dd className="mt-1 break-all text-xs">{document.version_id}</dd>
        </div>
      </dl>
      {document.metadatos.fuente_url &&
        /^https?:\/\//i.test(document.metadatos.fuente_url) && (
          <Button variant="outline" asChild>
            <a
              href={document.metadatos.fuente_url}
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
      {chunks.error ? (
        <div role="alert" className="space-y-3 text-sm text-destructive">
          <p>{chunks.error}</p>
          <Button variant="outline" onClick={chunks.retry}>
            Reintentar lectura
          </Button>
        </div>
      ) : chunks.loading ? (
        <p role="status" className="text-sm text-muted-foreground">
          Cargando fragmentos…
        </p>
      ) : (
        chunks.data?.fragmentos.map((chunk) => (
          <article
            data-testid="published-chunk"
            key={chunk.id}
            className="rounded-md border border-border bg-card p-4"
          >
            <p className="mb-3 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <FileText size={14} />
              Página {chunk.pagina} · {chunk.tokens} tokens
            </p>
            <p className="mb-3 text-xs text-muted-foreground">
              {chunk.ubicacion}
            </p>
            <p className="whitespace-pre-wrap break-words text-sm leading-7">
              {chunk.texto}
            </p>
          </article>
        ))
      )}
      {chunks.data && (
        <LibraryPagination
          total={chunks.data.total}
          offset={chunks.offset}
          limit={chunks.data.limite}
          busy={chunks.loading}
          onChange={chunks.setOffset}
        />
      )}
    </div>
  )
}
export function PublishedDocumentDetails({
  document,
  onClose,
}: {
  document: PublishedDocument | null
  onClose: () => void
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
          <SheetTitle className="break-words font-display text-2xl">
            {document?.metadatos.titulo}
          </SheetTitle>
          <SheetDescription>
            Versión publicada · texto y localizadores leídos desde el backend.
          </SheetDescription>
        </SheetHeader>
        {document && (
          <PublishedChunks key={document.version_id} document={document} />
        )}
      </SheetContent>
    </Sheet>
  )
}
