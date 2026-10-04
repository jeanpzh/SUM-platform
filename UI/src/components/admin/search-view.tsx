import { useState } from 'react'
import { Search, ArrowUpRight } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useRetrieval } from '#/hooks/use-retrieval'
import type { RetrievalHit } from '#/lib/admin-workspace/retrieval'
import { DashboardPage, EmptyState } from './dashboard-page'
import { CorpusScope } from './corpus-scope'
import { SourceCitation } from './source-citation'
import { DocumentDetails } from './document-details'

export function SearchView() {
  const retrieval = useRetrieval()
  const [inspected, setInspected] = useState<RetrievalHit | null>(null)
  return (
    <DashboardPage
      title="Encuentra el fragmento preciso"
      description="Inspecciona qué evidencia recupera cada consulta antes de construir una respuesta."
    >
      <form
        onSubmit={(event) => {
          event.preventDefault()
          retrieval.search()
        }}
        className="mb-8 rounded-lg border border-border bg-card p-5 sm:p-6"
      >
        <div className="grid gap-5 xl:grid-cols-[1fr_280px]">
          <div>
            <label
              htmlFor="retrieval-query"
              className="mb-2 block text-sm font-semibold"
            >
              Consulta de prueba
            </label>
            <div className="flex gap-2">
              <Input
                id="retrieval-query"
                value={retrieval.query}
                onChange={(event) => retrieval.setQuery(event.target.value)}
                placeholder="Ej. publicación de versiones"
                className="min-h-11"
                maxLength={2000}
                aria-invalid={!!retrieval.error}
                aria-describedby={
                  retrieval.error ? 'retrieval-error' : undefined
                }
              />
              <Button type="submit" className="min-h-11">
                <Search size={16} />
                <span className="hidden sm:inline">Buscar</span>
              </Button>
            </div>
            {retrieval.error && (
              <p
                id="retrieval-error"
                role="alert"
                className="mt-2 text-sm text-destructive"
              >
                {retrieval.error}
              </p>
            )}
          </div>
          <CorpusScope
            documents={retrieval.documents}
            value={retrieval.documentId}
            onChange={retrieval.setDocumentId}
          />
        </div>
        <div className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4 text-xs text-muted-foreground">
          <p>
            Coincidencia léxica local · máximo {retrieval.settings.topK}{' '}
            resultados · mínimo {Math.round(retrieval.settings.minMatch * 100)}%
            de términos
          </p>
          <Link to="/admin/settings" className="inline-flex items-center gap-1">
            Ajustar recuperación <ArrowUpRight size={13} />
          </Link>
        </div>
      </form>
      {!retrieval.submitted ? (
        <EmptyState title="Una consulta abre el contexto">
          <p>Busca palabras presentes en la biblioteca publicada.</p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {[
              'publicación de versiones',
              'fragmentos y trazabilidad',
              'reglamento',
            ].map((query) => (
              <Button
                key={query}
                variant="outline"
                onClick={() => retrieval.search(query)}
              >
                {query}
              </Button>
            ))}
          </div>
        </EmptyState>
      ) : retrieval.hits.length ? (
        <section aria-label="Resultados de recuperación">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="font-display text-2xl">Evidencia recuperada</h2>
            <span role="status" className="text-sm text-muted-foreground">
              {retrieval.hits.length} fragmentos
            </span>
          </div>
          <div className="space-y-4">
            {retrieval.hits.map((hit, index) => (
              <article
                key={hit.chunk.id}
                className="rounded-lg border border-border bg-card/50 p-5 sm:p-6"
              >
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-muted-foreground">
                    {String(index + 1).padStart(2, '0')} /{' '}
                    {hit.document.category}
                  </p>
                  <span className="text-xs text-success">
                    {Math.round(hit.score * 100)}% de términos coinciden
                  </span>
                </div>
                <h3 className="font-display text-xl">{hit.document.title}</h3>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted-foreground">
                  {hit.chunk.text}
                </p>
                <div className="mt-5">
                  <SourceCitation
                    hit={hit}
                    number={index + 1}
                    onInspect={() => setInspected(hit)}
                  />
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : (
        <EmptyState title="Sin evidencia suficiente">
          No hay fragmentos que superen el umbral. Prueba términos más
          concretos, otra fuente o un umbral menor.
        </EmptyState>
      )}
      <DocumentDetails
        document={inspected?.document ?? null}
        focusChunkId={inspected?.chunk.id}
        onClose={() => setInspected(null)}
      />
    </DashboardPage>
  )
}
