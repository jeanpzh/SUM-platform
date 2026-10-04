import { useEffect, useState } from 'react'
import { modelChoiceKey } from '#/lib/ai/providers'
import {
  cancelRun,
  createRun,
  fetchModels,
  fetchRunEvents,
  getRun,
  watchRun,
} from '#/lib/ai/client'
import type { AuditEvent, ModelChoice, Run } from '#/lib/ai/client'

export function useAiChat() {
  const [ready, setReady] = useState(false)
  const [models, setModels] = useState<ModelChoice[]>([])
  const [selected, setSelected] = useState('')
  const [run, setRun] = useState<Run | null>(null)
  const [trace, setTrace] = useState<AuditEvent[]>([])
  const [question, setQuestion] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    setReady(true)
    void fetchModels(controller.signal)
      .then((choices) => {
        setModels(choices)
        setSelected(
          (current) =>
            current ||
            (choices.find((item) => item.available)
              ? modelChoiceKey(choices.find((item) => item.available)!)
              : ''),
        )
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError('No se pudo cargar el catálogo de modelos.')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('run_id')
    if (!id) return
    const controller = new AbortController()
    void getRun(id, controller.signal)
      .then(async (value) => {
        if (controller.signal.aborted) return
        setRun(value)
        setQuestion(value.question || 'Consulta guardada')
        setBusy(['queued', 'running'].includes(value.status))
        if (['completed', 'failed', 'cancelled'].includes(value.status)) {
          const events = await fetchRunEvents(id, controller.signal)
          if (!controller.signal.aborted) setTrace(events)
        }
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError('No se pudo abrir la ejecución.')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!run || ['completed', 'failed', 'cancelled'].includes(run.status))
      return
    return watchRun(
      run.run_id,
      run.sequence,
      (event) => {
        setTrace((current) =>
          current.some((entry) => entry.sequence === event.sequence)
            ? current
            : [...current, event],
        )
        if (['completed', 'failed', 'cancelled'].includes(event.kind)) {
          void getRun(run.run_id)
            .then(setRun)
            .catch(() => setError('No se pudo cargar el resultado.'))
          setBusy(false)
        } else
          setRun((current) =>
            current
              ? {
                  ...current,
                  sequence: event.sequence,
                  status: 'running',
                  stage: event.stage || current.stage,
                }
              : current,
          )
      },
      () => {
        setBusy(false)
        setError(
          'Se interrumpió el seguimiento. Abre la ejecución para consultar su estado.',
        )
      },
    )
  }, [run?.run_id, run?.status])

  async function submit(
    question: string,
    documentIds: string[] = [],
    topK = 4,
  ) {
    const choice = models.find(
      (item) => modelChoiceKey(item) === selected && item.available,
    )
    if (!choice) {
      setError('Selecciona un modelo disponible.')
      return
    }
    setBusy(true)
    setError('')
    setTrace([])
    setQuestion(question)
    try {
      const result = await createRun(
        {
          question,
          provider: choice.provider,
          model: choice.model,
          document_ids: documentIds,
          top_k: topK,
          ...(choice.provider_config_id
            ? {
                provider_config_id: choice.provider_config_id,
                provider_revision: choice.provider_revision!,
              }
            : {}),
        },
        crypto.randomUUID(),
      )
      setRun(result)
    } catch (cause) {
      setBusy(false)
      setError(
        cause instanceof Error
          ? cause.message
          : 'No se pudo crear la ejecución.',
      )
    }
  }

  async function cancel() {
    if (!run) return
    try {
      setRun(await cancelRun(run.run_id))
      setBusy(false)
    } catch {
      setError('No se pudo cancelar la ejecución.')
    }
  }

  return {
    ready,
    models,
    selected,
    setSelected,
    run,
    trace,
    question,
    error,
    busy,
    submit,
    cancel,
    clear: () => {
      setRun(null)
      setTrace([])
      setQuestion('')
      setError('')
      setBusy(false)
    },
  }
}
