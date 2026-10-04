import { useState } from 'react'
import { modelChoiceKey } from '#/lib/ai/providers'
import { ArrowUp, RotateCcw, BookOpen } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { Button } from '#/components/ui/button'
import { useAiChat } from '#/hooks/use-ai-chat'
import { usePublishedLibrary } from '#/hooks/use-published-library'
import { useWorkspace } from '#/components/admin/workspace-provider'
import { DashboardPage } from './dashboard-page'
import { selectClass } from './corpus-scope'
import { ChatTurn } from './chat-turn'

export function ChatView() {
  const chat = useAiChat()
  const library = usePublishedLibrary()
  const topK = useWorkspace((store) => store.state.settings.topK)
  const published = library.data?.documentos || []
  const [scope, setScope] = useState('all')
  const [question, setQuestion] = useState('')
  const available = chat.models.filter((item) => item.available)
  const currentModel = available.find(
    (item) => modelChoiceKey(item) === chat.selected,
  )

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    const value = question.trim()
    if (value.length < 3 || value.length > 2000 || !currentModel) return
    await chat.submit(value, scope === 'all' ? [] : [scope], Math.min(topK, 10))
  }

  return (
    <DashboardPage
      title="Prueba RAG agente"
      description="Pregunta sobre publicaciones, revisa citas y sigue cada etapa de la ejecución."
      action={
        <Button
          variant="outline"
          disabled={!chat.run}
          onClick={() => {
            chat.clear()
            setQuestion('')
          }}
        >
          <RotateCcw size={15} />
          Nueva conversación
        </Button>
      }
    >
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
        <section
          className="min-w-0 overflow-hidden rounded-lg border border-border bg-card/40"
          aria-label="Conversación de prueba"
        >
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold">Mesa de consulta</h2>
            <span className="text-xs text-muted-foreground">
              AI Service · corpus publicado
            </span>
          </div>
          <div
            className="max-h-[65dvh] min-h-[330px] space-y-7 overflow-y-auto p-5 sm:p-6"
            aria-live="polite"
          >
            {chat.run ? (
              <ChatTurn
                question={chat.question}
                run={chat.run}
                trace={chat.trace}
              />
            ) : (
              <div className="py-8">
                <BookOpen
                  size={26}
                  strokeWidth={1.4}
                  className="mb-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <h3 className="max-w-sm font-display text-3xl leading-snug">
                  Pregunta. Contrasta. Sigue la fuente.
                </h3>
                <p className="mt-4 max-w-md text-sm leading-6 text-muted-foreground">
                  Cada respuesta conserva citas, versiones del corpus y una
                  traza auditable.
                </p>
              </div>
            )}
          </div>
          <form
            onSubmit={submit}
            className="border-t border-border bg-background p-5"
          >
            <label
              htmlFor="chat-question"
              className="mb-2 block text-sm font-semibold"
            >
              Tu pregunta
            </label>
            <div className="flex items-end gap-3">
              <textarea
                id="chat-question"
                disabled={!chat.ready}
                rows={2}
                minLength={3}
                maxLength={2000}
                required
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Escribe una pregunta sobre fuentes publicadas…"
                className="min-h-20 min-w-0 flex-1 resize-y rounded-md border border-input bg-background px-3 py-3 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              />
              <Button
                type="submit"
                size="icon"
                className="size-11 shrink-0"
                aria-label="Enviar pregunta"
                disabled={
                  !chat.ready || chat.busy || !currentModel || !published.length
                }
              >
                <ArrowUp size={19} />
              </Button>
            </div>
            {chat.error && (
              <p role="alert" className="mt-3 text-sm text-destructive">
                {chat.error}
              </p>
            )}
            {chat.busy && (
              <Button
                type="button"
                variant="outline"
                className="mt-3"
                onClick={() => void chat.cancel()}
              >
                Cancelar ejecución
              </Button>
            )}
            {!published.length && (
              <p className="mt-3 text-xs text-muted-foreground">
                {library.loading
                  ? 'Cargando publicaciones…'
                  : library.error || 'Publica un documento para probar RAG.'}
              </p>
            )}
          </form>
        </section>
        <aside className="space-y-6 rounded-lg border border-border bg-card p-5">
          <div>
            <label
              htmlFor="ai-model"
              className="mb-2 block text-sm font-semibold"
            >
              Proveedor y modelo
            </label>
            <select
              id="ai-model"
              className={selectClass}
              value={currentModel ? modelChoiceKey(currentModel) : ''}
              onChange={(event) => chat.setSelected(event.target.value)}
            >
              {available.length ? (
                available.map((item) => (
                  <option
                    key={modelChoiceKey(item)}
                    value={modelChoiceKey(item)}
                  >
                    {item.connection_name || item.provider} · {item.model}
                  </option>
                ))
              ) : (
                <option value="">Sin modelos disponibles</option>
              )}
            </select>
            {chat.models.some((item) => !item.available) && (
              <p className="mt-2 text-xs text-muted-foreground">
                Configura o habilita las conexiones en Settings.
              </p>
            )}
          </div>
          <label className="block text-sm font-semibold">
            Alcance de la consulta
            <select
              className={selectClass}
              value={scope}
              onChange={(event) => setScope(event.target.value)}
            >
              <option value="all">Todo el corpus publicado</option>
              {published.map((doc) => (
                <option key={doc.documento_id} value={doc.documento_id}>
                  {doc.metadatos.titulo}
                </option>
              ))}
            </select>
          </label>
          <div className="border-t border-border pt-5 text-sm">
            <h2 className="font-semibold">Corpus publicado</h2>
            <p className="mt-2 text-muted-foreground">
              {library.data?.total ?? 0} fuentes disponibles · máximo{' '}
              {Math.min(topK, 8)} fragmentos
            </p>
            <Link to="/admin/library" className="mt-3 inline-block underline">
              Administrar biblioteca
            </Link>
          </div>
          <p className="border-t border-border pt-5 text-xs leading-5 text-muted-foreground">
            El costo mostrado es una estimación. Las citas deben corresponder a
            la versión publicada.
          </p>
        </aside>
      </div>
    </DashboardPage>
  )
}
