import { useEffect, useState } from 'react'
import { modelChoiceKey, providerKinds } from '#/lib/ai/providers'
import { fetchModels } from '#/lib/ai/client'
import type { ModelChoice, Run } from '#/lib/ai/client'
import {
  fetchMetrics,
  fetchMetricRuns,
  fetchEvaluations,
  startEvaluation,
  latencyLabel,
} from '#/lib/ai/metrics'
import type { MetricsResponse, EvaluationCatalog } from '#/lib/ai/metrics'
import { DashboardPage } from './dashboard-page'
import { selectClass } from './corpus-scope'
import { Button } from '#/components/ui/button'

const labels: Record<string, string> = {
  validating: 'Validación',
  retrieving: 'Recuperación',
  researching: 'Investigación',
  composing: 'Redacción',
  verifying: 'Verificación',
}

export function MetricsView() {
  const [data, setData] = useState<MetricsResponse | null>(null)
  const [evaluations, setEvaluations] = useState<EvaluationCatalog | null>(null)
  const [models, setModels] = useState<ModelChoice[]>([])
  const [runPage, setRunPage] = useState(0)
  const [runLoading, setRunLoading] = useState(false)
  const [hasMoreRuns, setHasMoreRuns] = useState(false)
  const [runs, setRuns] = useState<Run[]>([])
  const [days, setDays] = useState(7)
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [generation, setGeneration] = useState('')
  const [generationDraft, setGenerationDraft] = useState('')
  const [status, setStatus] = useState('')
  const [revision, setRevision] = useState(0)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [evaluationModel, setEvaluationModel] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setError('')
    void fetchMetrics(
      { days, provider, model, generation, status },
      controller.signal,
    )
      .then((value) => {
        if (!controller.signal.aborted) setData(value)
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError('No se pudieron cargar las métricas.')
      })
    void fetchEvaluations()
      .then(setEvaluations)
      .catch(() => {})
    void fetchModels(controller.signal)
      .then(setModels)
      .catch(() => {})
    return () => controller.abort()
  }, [days, provider, model, generation, status, revision])

  useEffect(() => {
    setRunPage(0)
  }, [days, provider, model, generation, status])
  useEffect(() => {
    const controller = new AbortController()
    setRunLoading(true)
    void fetchMetricRuns(
      { days, provider, model, generation, status },
      runPage,
      controller.signal,
    )
      .then((values) => {
        if (!controller.signal.aborted) {
          setRuns(values.slice(0, 20))
          setHasMoreRuns(values.length > 20)
        }
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError('No se pudieron cargar las ejecuciones filtradas.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setRunLoading(false)
      })
    return () => controller.abort()
  }, [days, provider, model, generation, status, revision, runPage])

  async function evaluate(datasetId: string) {
    const choice = models.find(
      (item) => modelChoiceKey(item) === evaluationModel,
    )
    if (!choice) {
      setError('Selecciona un modelo para evaluar.')
      return
    }
    setPending(true)
    try {
      await startEvaluation(
        datasetId,
        choice.provider,
        choice.model,
        choice.provider_config_id,
        choice.provider_revision,
      )
      setRevision((value) => value + 1)
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No se pudo iniciar la evaluación.',
      )
    } finally {
      setPending(false)
    }
  }
  const summary = data?.summary
  const maximum = Math.max(
    1,
    ...(data?.stages.map((stage) => stage.mean_ms || 0) || []),
  )

  return (
    <DashboardPage
      title="Métricas del RAG"
      description="Tiempos, uso y resultados vinculados a ejecuciones auditadas."
      action={
        <Button
          variant="outline"
          onClick={() => setRevision((value) => value + 1)}
        >
          Actualizar
        </Button>
      }
    >
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <label className="text-sm">
          Período
          <select
            className={selectClass}
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          >
            {[1, 7, 30, 90].map((day) => (
              <option key={day} value={day}>
                {day} días
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Proveedor
          <select
            className={selectClass}
            value={provider}
            onChange={(event) => {
              setProvider(event.target.value)
              setModel('')
            }}
          >
            <option value="">Todos</option>
            {providerKinds.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Modelo
          <select
            className={selectClass}
            value={model}
            onChange={(event) => setModel(event.target.value)}
          >
            <option value="">Todos</option>
            {models
              .filter((item) => !provider || item.provider === provider)
              .map((item) => (
                <option key={modelChoiceKey(item)} value={item.model}>
                  {item.model}
                </option>
              ))}
          </select>
        </label>
        <label className="text-sm">
          Generación del corpus
          <input
            className={selectClass}
            placeholder="UUID opcional"
            value={generationDraft}
            onChange={(event) => {
              const value = event.target.value
              setGenerationDraft(value)
              if (
                !value ||
                /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
                  value,
                )
              )
                setGeneration(value)
            }}
          />
        </label>
        <label className="text-sm">
          Estado
          <select
            className={selectClass}
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Todos</option>
            {['completed', 'failed', 'cancelled'].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
      </div>
      {!!data?.series.length && (
        <section className="mt-6 rounded-lg border border-border p-5">
          <h2 className="font-semibold">Consultas a lo largo del tiempo</h2>
          <svg
            role="img"
            aria-label="Consultas por intervalo; valores disponibles en la tabla"
            viewBox="0 0 720 140"
            className="mt-4 w-full max-w-3xl"
          >
            {data.series.map((point, index) => {
              const width = 700 / data.series.length
              const maximum = Math.max(
                1,
                ...data.series.map((value) => value.count),
              )
              return (
                <rect
                  key={point.hour}
                  x={index * width}
                  y={125 - (point.count / maximum) * 110}
                  width={Math.max(1, width - 2)}
                  height={(point.count / maximum) * 110}
                  fill="currentColor"
                  opacity="0.45"
                >
                  <title>
                    {point.hour}: {point.count} consultas
                  </title>
                </rect>
              )
            })}
          </svg>
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer">Ver valores</summary>
            <table className="mt-3 w-full text-left">
              <caption className="sr-only">
                Consultas y costo por intervalo
              </caption>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Consultas</th>
                  <th>Costo estimado US$</th>
                </tr>
              </thead>
              <tbody>
                {data.series.map((point) => (
                  <tr key={point.hour}>
                    <th className="font-normal">
                      {new Date(point.hour).toLocaleString()}
                    </th>
                    <td>{point.count}</td>
                    <td>{point.estimated_cost_usd.toFixed(5)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </section>
      )}
      {error && (
        <p role="alert" className="mb-5 text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['Consultas reales', summary?.count ?? 0],
          ['Tiempo promedio', latencyLabel(summary?.mean_ms ?? null)],
          [
            'Tokens usados',
            (summary?.input_tokens ?? 0) + (summary?.output_tokens ?? 0),
          ],
          [
            'Costo estimado',
            `US$ ${(summary?.estimated_cost_usd ?? 0).toFixed(5)}`,
          ],
        ].map(([title, value]) => (
          <section key={title} className="rounded-lg border border-border p-5">
            <h2 className="text-sm text-muted-foreground">{title}</h2>
            <p className="mt-3 text-2xl font-semibold">{value}</p>
          </section>
        ))}
      </div>
      <section className="mt-6 rounded-lg border border-border p-5">
        <h2 className="font-semibold">Tiempo por etapa</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Promedio y percentiles aproximados de histogramas horarios.
          Actualización cada 15 segundos.
        </p>
        {!data?.stages.length ? (
          <p className="mt-5 text-sm text-muted-foreground">
            Sin ejecuciones con tiempos registrados.
          </p>
        ) : (
          <>
            <svg
              role="img"
              aria-label="Promedio de duración por etapa; valores disponibles en la tabla"
              viewBox={`0 0 700 ${data.stages.length * 38}`}
              className="mt-5 w-full max-w-3xl"
            >
              {data.stages.map((stage, index) => (
                <g key={stage.stage} transform={`translate(0,${index * 38})`}>
                  <text x="0" y="22" fontSize="13" fill="currentColor">
                    {labels[stage.stage] || stage.stage}
                  </text>
                  <rect
                    x="150"
                    y="7"
                    width={Math.max(2, ((stage.mean_ms || 0) / maximum) * 380)}
                    height="22"
                    fill="currentColor"
                    opacity="0.35"
                  />
                  <text x="550" y="22" fontSize="13" fill="currentColor">
                    {latencyLabel(stage.mean_ms)}
                  </text>
                </g>
              ))}
            </svg>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">Duraciones por etapa</caption>
                <thead>
                  <tr className="border-b border-border">
                    <th className="py-2">Etapa</th>
                    <th>N</th>
                    <th>Promedio</th>
                    <th>p50 aprox.</th>
                    <th>p95 aprox.</th>
                  </tr>
                </thead>
                <tbody>
                  {data.stages.map((stage) => (
                    <tr key={stage.stage} className="border-b border-border/50">
                      <th className="py-2 font-medium">
                        {labels[stage.stage] || stage.stage}
                      </th>
                      <td>{stage.count}</td>
                      <td>{latencyLabel(stage.mean_ms)}</td>
                      <td>{latencyLabel(stage.p50_ms)}</td>
                      <td>{latencyLabel(stage.p95_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <p className="mt-5 text-sm text-muted-foreground">
          Abstenciones: {summary?.abstentions ?? 0} · Límites de cuota:{' '}
          {summary?.rate_limits ?? 0} · Timeouts: {summary?.timeouts ?? 0} · p95
          total: {latencyLabel(summary?.p95_ms ?? null)}
        </p>
      </section>
      <section className="mt-6 rounded-lg border border-border p-5">
        <h2 className="font-semibold">Calidad con etiquetas</h2>
        {data?.quality ? (
          <p className="mt-3 text-sm">
            Recall@4: {data.quality.recall_at_k.toFixed(3)} · Precision@4:{' '}
            {data.quality.precision_at_k.toFixed(3)} · MRR:{' '}
            {data.quality.mrr.toFixed(3)} · {data.quality.count} casos
          </p>
        ) : (
          <p className="mt-3 text-sm text-muted-foreground">
            Sin evaluación etiquetada vigente. Las consultas reales no permiten
            calcular recall.
          </p>
        )}
        <label className="mt-5 block max-w-md text-sm">
          Modelo para evaluar
          <select
            className={selectClass}
            value={evaluationModel}
            onChange={(event) => setEvaluationModel(event.target.value)}
          >
            <option value="">Selecciona un modelo</option>
            {models
              .filter((item) => item.available)
              .map((item) => (
                <option key={modelChoiceKey(item)} value={modelChoiceKey(item)}>
                  {item.connection_name || item.provider} · {item.model}
                </option>
              ))}
          </select>
        </label>
        {evaluations?.datasets.map((dataset) => (
          <div
            key={dataset.dataset_id}
            className="mt-3 flex flex-wrap items-center gap-3 text-sm"
          >
            <span>
              {dataset.dataset_id} · {dataset.version} · {dataset.cases} casos
            </span>
            <Button
              variant="outline"
              disabled={!dataset.available || pending || !evaluationModel}
              onClick={() => void evaluate(dataset.dataset_id)}
            >
              Evaluar
            </Button>
            {!dataset.available && (
              <span className="text-muted-foreground">
                Etiquetas sin coincidencia con las publicaciones actuales
              </span>
            )}
          </div>
        ))}
        {evaluations?.evaluations.map((evaluation) => (
          <p key={evaluation.id} className="mt-3 text-xs text-muted-foreground">
            {evaluation.dataset_id} {evaluation.dataset_version} ·{' '}
            {evaluation.model} · {evaluation.completed}/{evaluation.cases}{' '}
            completados · {evaluation.failed} fallidos · recall{' '}
            {evaluation.recall_at_k?.toFixed(3) ?? 'pendiente'}
          </p>
        ))}
      </section>
      <section className="mt-6 rounded-lg border border-border p-5">
        <h2 className="font-semibold">
          Ejecuciones de los filtros seleccionados
        </h2>
        <p className="mt-2 text-xs text-muted-foreground">
          Tráfico interactivo · página {runPage + 1}. Abre una ejecución para
          inspeccionar su evidencia y configuración.
        </p>
        {runLoading && (
          <p role="status" className="mt-3 text-sm">
            Cargando ejecuciones…
          </p>
        )}
        {!runLoading && !runs.length && (
          <p className="mt-3 text-sm text-muted-foreground">
            Sin ejecuciones para estos filtros.
          </p>
        )}
        <ul className="mt-4 space-y-2 text-sm">
          {runs.map((run) => (
            <li key={run.run_id}>
              <a
                className="underline"
                href={`/admin/chat?run_id=${run.run_id}`}
              >
                {run.run_id.slice(0, 8)} · {run.provider} {run.model} ·{' '}
                {run.status}
              </a>
            </li>
          ))}
        </ul>
        <div className="mt-5 flex gap-3">
          <Button
            variant="outline"
            disabled={runLoading || runPage === 0}
            onClick={() => setRunPage((value) => value - 1)}
          >
            Anterior
          </Button>
          <Button
            variant="outline"
            disabled={runLoading || !hasMoreRuns}
            onClick={() => setRunPage((value) => value + 1)}
          >
            Siguiente
          </Button>
        </div>
      </section>
    </DashboardPage>
  )
}
