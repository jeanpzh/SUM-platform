import type { AuditEvent, Run } from '#/lib/ai/client'

const stageLabels: Record<string, string> = {
  validating: 'Validando',
  retrieving: 'Recuperando',
  researching: 'Investigando',
  composing: 'Redactando',
  verifying: 'Verificando',
}

export function ChatTurn({
  question,
  run,
  trace,
}: {
  question: string
  run: Run
  trace: AuditEvent[]
}) {
  const result = run.result
  return (
    <article className="space-y-6">
      <div className="ml-auto max-w-[90%] rounded-lg border border-border bg-muted/50 p-4">
        <p className="text-xs font-semibold text-muted-foreground">
          Tu consulta
        </p>
        <p className="mt-2 text-sm leading-6">{question}</p>
      </div>
      <div className="space-y-4 rounded-lg border border-border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">Respuesta del AI Service</h2>
          <span className="text-xs text-muted-foreground">
            {stageLabels[run.stage || ''] || run.status}
          </span>
        </div>
        {result ? (
          <>
            <p className="whitespace-pre-wrap text-sm leading-7">
              {result.answer}
            </p>
            {result.abstained && (
              <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-900">
                Abstención: la evidencia disponible no permite una respuesta
                citada.
              </p>
            )}
            {result.citations.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Citas verificadas
                </h3>
                <ol className="mt-3 space-y-2 text-sm">
                  {result.citations.map((citation, index) => (
                    <li key={citation.chunk_id}>
                      <a
                        className="underline underline-offset-2"
                        href={`#evidence-${citation.chunk_id}`}
                        onClick={() => {
                          const evidence = document.getElementById(
                            `evidence-${citation.chunk_id}`,
                          )
                          const panel = evidence?.closest('details')
                          if (panel) panel.open = true
                        }}
                      >
                        [{index + 1}] Documento{' '}
                        {citation.document_id.slice(0, 8)} · página{' '}
                        {citation.page} · {citation.locator}
                      </a>
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {result.evidence.length > 0 && (
              <details className="border-t border-border pt-4">
                <summary className="cursor-pointer text-sm font-medium">
                  Inspeccionar evidencia ({result.evidence.length})
                </summary>
                <div className="mt-3 space-y-3">
                  {result.evidence.map((item) => (
                    <section
                      key={item.chunk_id}
                      id={`evidence-${item.chunk_id}`}
                      className="rounded border border-border p-3 text-sm"
                    >
                      <h4 className="font-medium">
                        Página {item.page} · {item.locator}
                      </h4>
                      <p className="mt-2 whitespace-pre-wrap leading-6">
                        {item.text}
                      </p>
                      <p className="mt-2 break-all text-xs text-muted-foreground">
                        Fragmento {item.chunk_id} · versión {item.version_id} ·
                        generación {item.generation_id}
                      </p>
                    </section>
                  ))}
                </div>
              </details>
            )}
            {result.limitations.length > 0 && (
              <ul className="list-disc pl-5 text-sm text-muted-foreground">
                {result.limitations.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            )}
            {result.tool_trace.length > 0 && (
              <details>
                <summary className="cursor-pointer text-sm font-medium">
                  Herramientas utilizadas
                </summary>
                <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-all text-xs">
                  {JSON.stringify(result.tool_trace, null, 2)}
                </pre>
              </details>
            )}
            <dl className="grid gap-3 border-t border-border pt-4 text-xs text-muted-foreground sm:grid-cols-3">
              <div>
                <dt>Tokens de entrada</dt>
                <dd className="font-medium text-foreground">
                  {result.usage.input_tokens}
                </dd>
              </div>
              <div>
                <dt>Tokens de salida</dt>
                <dd className="font-medium text-foreground">
                  {result.usage.output_tokens}
                </dd>
              </div>
              <div>
                <dt>Costo estimado</dt>
                <dd className="font-medium text-foreground">
                  US$ {result.usage.estimated_cost_usd.toFixed(5)}
                </dd>
              </div>
            </dl>
          </>
        ) : (
          <p className="text-sm text-muted-foreground" role="status">
            {run.status === 'failed'
              ? `La ejecución falló (${run.error_code || 'AI_RUN_FAILED'}).`
              : run.status === 'cancelled'
                ? 'Ejecución cancelada.'
                : 'La consulta se está procesando…'}
          </p>
        )}
        {run.retrieval_audit && (
          <details className="border-t border-border pt-4">
            <summary className="cursor-pointer text-sm font-medium">
              Recuperación inicial conservada ·{' '}
              {run.retrieval_audit.evidence.length} fragmentos
            </summary>
            <p className="mt-3 break-all text-xs text-muted-foreground">
              Corpus SHA-256: {run.retrieval_audit.corpus_sha256}
            </p>
            {run.retrieval_audit.evidence.map((item) => (
              <div
                key={item.chunk_id}
                className="mt-3 rounded border border-border p-3 text-xs"
              >
                <p className="whitespace-pre-wrap leading-6">{item.text}</p>
                <p className="mt-2 break-all text-muted-foreground">
                  Fragmento {item.chunk_id} · generación {item.generation_id} ·
                  página {item.page}
                </p>
              </div>
            ))}
          </details>
        )}
        <div className="border-t border-border pt-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Traza auditable
          </h3>
          {run.configuration && (
            <details className="my-3 text-xs">
              <summary className="cursor-pointer font-medium">
                Configuración de esta ejecución · {run.configuration.name} · v
                {run.configuration.revision}
              </summary>
              <p className="mt-2 break-all text-muted-foreground">
                {run.configuration.base_url}
              </p>
              {run.configuration.models
                .filter((item) => item.model === run.model)
                .map((item) => (
                  <p key={item.model} className="mt-2 text-muted-foreground">
                    {item.model} · entrada US$ {item.input_usd_per_million}/M ·
                    salida US$ {item.output_usd_per_million}/M · tarifa{' '}
                    {item.pricing_date}
                  </p>
                ))}
            </details>
          )}
          <ol className="mt-2 space-y-1 text-xs text-muted-foreground">
            {trace.map((event) => (
              <li key={event.sequence}>
                #{event.sequence} ·{' '}
                {stageLabels[event.stage || ''] || event.kind}
                {event.code ? ` · ${event.code}` : ''}
              </li>
            ))}
          </ol>
          <p className="mt-3 break-all text-xs text-muted-foreground">
            Ejecución: {run.run_id}
          </p>
        </div>
      </div>
    </article>
  )
}
