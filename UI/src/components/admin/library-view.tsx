import { useState } from 'react'
import { RefreshCw, Search } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { usePublishedLibrary } from '#/hooks/use-published-library'
import type { PublishedDocument } from '#/lib/pdf-ingestion/library'
import { DashboardPage, EmptyState, MetricStrip } from './dashboard-page'
import { BackendStatus } from '#/components/pdf-dashboard/backend-status'
import { PublishedDocumentRow } from './published-document-row'
import { PublishedDocumentDetails } from './published-document-details'
import { LibraryPagination } from './library-pagination'

export function LibraryView() {
  const library = usePublishedLibrary()
  const [inspected, setInspected] = useState<PublishedDocument | null>(null)
  return (
    <DashboardPage
      title="Una biblioteca, todas las fuentes"
      description="Consulta los documentos publicados y revisa el texto de cada fragmento indexado."
      action={<BackendStatus />}
    >
      <MetricStrip
        items={[
          {
            label: 'Documentos publicados',
            value: library.data?.total ?? '—',
            detail: 'Catálogo del backend',
          },
          {
            label: 'Fragmentos indexados',
            value: library.data?.fragmentos ?? '—',
            detail: 'En los documentos encontrados',
          },
          {
            label: 'Actualización',
            value: '10 s',
            detail: 'Automática al publicar y al volver',
          },
        ]}
      />
      <div className="mb-5 flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1">
          <label
            htmlFor="library-search"
            className="mb-2 block text-sm font-semibold"
          >
            Buscar documentos
          </label>
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-3.5 size-4 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="library-search"
              className="min-h-11 pl-9"
              placeholder="Título, origen o tipo"
              value={library.query}
              onChange={(event) => library.setQuery(event.target.value)}
            />
          </div>
        </div>
        <Button
          variant="outline"
          disabled={!library.ready || library.loading}
          onClick={library.refresh}
        >
          <RefreshCw
            size={15}
            className={library.loading ? 'animate-spin' : ''}
          />
          Actualizar
        </Button>
      </div>
      {library.error && (
        <p
          role="alert"
          className="mb-4 rounded-md border border-destructive/30 p-4 text-sm text-destructive"
        >
          No se pudo actualizar: {library.error} Se conserva la última lectura
          confirmada.
        </p>
      )}
      {!library.ready && (
        <p role="status" className="mb-4 text-sm text-muted-foreground">
          Esperando al servicio. La biblioteca se actualizará automáticamente al
          conectar.
        </p>
      )}
      {library.data && (
        <p role="status" className="mb-4 text-xs text-muted-foreground">
          {library.data.total} resultados
          {library.loading ? ' · Actualizando…' : ''}
        </p>
      )}
      {library.data?.documentos.length ? (
        <div
          aria-busy={library.loading}
          className="overflow-hidden rounded-lg border border-border bg-card/40"
        >
          {library.data.documentos.map((document) => (
            <PublishedDocumentRow
              key={document.documento_id}
              document={document}
              onInspect={() => setInspected(document)}
            />
          ))}
        </div>
      ) : !library.data || library.loading || library.error ? (
        <p role="status" className="py-8 text-sm text-muted-foreground">
          {library.loading
            ? 'Cargando biblioteca…'
            : 'El catálogo todavía no está disponible.'}
        </p>
      ) : (
        <EmptyState
          title={
            library.query
              ? 'No encontramos documentos'
              : 'Todavía no hay documentos publicados'
          }
        >
          {library.query ? (
            'Prueba otro título, origen o tipo de documento.'
          ) : (
            <span>
              Publica un PDF desde{' '}
              <Link to="/" className="text-primary underline">
                Ingesta de PDF
              </Link>
              ; aparecerá aquí cuando termine la indexación.
            </span>
          )}
        </EmptyState>
      )}
      {library.data && (
        <LibraryPagination
          total={library.data.total}
          offset={library.data.offset}
          limit={library.data.limite}
          busy={library.loading}
          onChange={library.setOffset}
        />
      )}
      <p className="mt-5 text-xs leading-5 text-muted-foreground">
        Solo se muestran versiones publicadas. Una nueva ingesta conserva la
        versión anterior hasta completar su publicación.
      </p>
      <PublishedDocumentDetails
        document={inspected}
        onClose={() => setInspected(null)}
      />
    </DashboardPage>
  )
}
