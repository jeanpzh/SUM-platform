import { FileText, ArrowUpRight } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import type { PublishedDocument } from '#/lib/pdf-ingestion/library'
import { sourceMetadataSchema } from '#/lib/pdf-ingestion/schema'
import { DocumentActions } from './document-actions'

export function PublishedDocumentRow({
  document,
  onInspect,
}: {
  document: PublishedDocument
  onInspect: () => void
}) {
  return (
    <article
      data-testid="published-document"
      data-document-id={document.documento_id}
      className="flex flex-wrap items-center justify-between gap-4 border-b border-border px-4 py-5 last:border-0 sm:px-6"
    >
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <FileText
          size={20}
          strokeWidth={1.5}
          className="mt-1 shrink-0 text-primary"
          aria-hidden="true"
        />
        <div className="min-w-0">
          <button
            onClick={onInspect}
            className="text-left text-sm font-semibold leading-6 text-foreground underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
          >
            {document.metadatos.titulo}
          </button>
          <p className="mt-1 break-all text-xs text-muted-foreground">
            {document.metadatos.fuente_url || 'Origen no indicado'}
            {document.metadatos.codigo_documento
              ? ` · ${document.metadatos.codigo_documento}`
              : ''}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            {document.metadatos.tipo_documento} · {document.fragmentos}{' '}
            fragmentos · {(document.tamano_bytes / 1024).toFixed(1)} KB
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant="outline" className="border-success/30 text-success">
          Publicado
        </Badge>
        <Button
          variant="ghost"
          onClick={onInspect}
          aria-label={`Ver fragmentos de ${document.metadatos.titulo}`}
        >
          <ArrowUpRight size={16} />
          <span className="sm:sr-only">Fragmentos</span>
        </Button>
      </div>
      <DocumentActions
        documentId={document.documento_id}
        title={document.metadatos.titulo}
        metadata={sourceMetadataSchema.parse({
          originUrl: document.metadatos.fuente_url ?? '',
          resolution: document.metadatos.codigo_documento ?? '',
          documentType: document.metadatos.tipo_documento,
          priority: document.metadatos.prioridad ?? 'normal',
          testDocument: document.metadatos.es_prueba === true,
        })}
        reindex
      />
    </article>
  )
}
