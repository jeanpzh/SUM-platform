import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { z } from 'zod'
import {
  dataSchemas,
  optionsSchema,
  studentFetch,
  studentRunSchema,
} from '#/lib/student/contracts'
import type {
  StudentMessage,
  StudentOptions,
  StudentRun,
} from '#/lib/student/contracts'

export function useStudentChat(
  runId: string | undefined,
  onRun: (id: string) => void,
) {
  const activeRef = useRef<string | undefined>(runId)
  const cursorRef = useRef(0)
  const loadingRef = useRef<string | undefined>(undefined)
  const pendingKey = useRef({ question: '', options: '', key: '' })
  const lastOptions = useRef<StudentOptions | undefined>(undefined)
  const [activeRun, setActiveRun] = useState(runId)
  const [history, setHistory] = useState<StudentRun[]>([])
  const [historyOffset, setHistoryOffset] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [retryAt, setRetryAt] = useState(0)
  const [now, setNow] = useState(0)
  const onRunRef = useRef(onRun)
  onRunRef.current = onRun

  const transport = useMemo(
    () =>
      new DefaultChatTransport<StudentMessage>({
        api: '/api/student/ai/chat',
        credentials: 'same-origin',
        prepareSendMessagesRequest: ({ messages, body }) => {
          const latest = messages
            .filter((message) => message.role === 'user')
            .at(-1)
          const question =
            latest?.parts
              .filter((part) => part.type === 'text')
              .map((part) => part.text)
              .join('\n') ?? ''
          const options = optionsSchema.parse(body?.options)
          const canonical = JSON.stringify(options)
          if (
            pendingKey.current.question !== question ||
            pendingKey.current.options !== canonical ||
            !pendingKey.current.key
          )
            pendingKey.current = {
              question,
              options: canonical,
              key: crypto.randomUUID(),
            }
          return {
            body: { question, options },
            headers: { 'Idempotency-Key': pendingKey.current.key },
          }
        },
        prepareReconnectToStreamRequest: () => ({
          api: `/api/student/ai/runs/${z.uuid().parse(activeRef.current)}/stream?after=${cursorRef.current}`,
        }),
        fetch: async (input, init) => {
          const response = await fetch(input, init)
          if (!response.ok) {
            if (response.status === 429) {
              const raw = Number(response.headers.get('retry-after'))
              const seconds =
                Number.isFinite(raw) && raw > 0 ? Math.min(raw, 86400) : 60
              setRetryAt(Date.now() + seconds * 1000)
              setNow(Date.now())
            }
            const message =
              response.status === 401
                ? 'Inicia sesión para consultar al asistente.'
                : response.status === 429
                  ? 'Alcanzaste tu límite de uso. Espera antes de realizar otra consulta.'
                  : 'No se pudo completar la consulta. Puedes reintentar o reabrirla desde tu historial.'
            return new Response(message, {
              status: response.status,
              headers: response.headers,
            })
          }
          return response
        },
      }),
    [],
  )

  const refreshHistory = useCallback(async (offset = 0) => {
    setHistoryLoading(true)
    try {
      const values = z
        .array(studentRunSchema)
        .parse(await studentFetch(`runs?limit=20&offset=${offset}`))
      setHistory(values)
      setHistoryOffset(offset)
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : 'No se pudo cargar el historial.',
      )
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  const chat = useChat<StudentMessage>({
    transport,
    dataPartSchemas: dataSchemas,
    messageMetadataSchema: z.object({ run_id: z.uuid() }),
    onData: (part) => {
      if (part.type === 'data-run') {
        activeRef.current = part.data.run_id
        loadingRef.current = part.data.run_id
        setActiveRun(part.data.run_id)
        onRunRef.current(part.data.run_id)
      }
      if (part.type === 'data-audit')
        cursorRef.current = Math.max(cursorRef.current, part.data.sequence)
    },
    onFinish: ({ isError, isAbort, isDisconnect }) => {
      if (!isError && !isAbort && !isDisconnect) pendingKey.current.key = ''
      void refreshHistory()
    },
  })
  const { setMessages, resumeStream } = chat

  useEffect(() => {
    void refreshHistory()
  }, [refreshHistory])
  useEffect(() => {
    if (!retryAt) return
    const timer = setInterval(() => {
      setNow(Date.now())
      if (Date.now() >= retryAt) setRetryAt(0)
    }, 1000)
    return () => clearInterval(timer)
  }, [retryAt])

  useEffect(() => {
    if (!runId || loadingRef.current === runId) return
    const controller = new AbortController()
    loadingRef.current = runId
    activeRef.current = runId
    cursorRef.current = 0
    setActiveRun(runId)
    setLoading(true)
    setNotice('')
    void (async () => {
      try {
        const run = studentRunSchema.parse(
          await studentFetch(`runs/${z.uuid().parse(runId)}`, {
            signal: controller.signal,
          }),
        )
        if (controller.signal.aborted) return
        const messages: StudentMessage[] = [
          {
            id: `${runId}:question`,
            role: 'user',
            parts: [{ type: 'text', text: run.question ?? '' }],
          },
        ]
        if (run.result)
          messages.push({
            id: runId,
            role: 'assistant',
            metadata: { run_id: runId },
            parts: [
              { type: 'text', text: run.result.answer },
              { type: 'data-result', data: run.result },
            ],
          })
        setMessages(messages)
        if (run.status === 'queued' || run.status === 'running')
          await resumeStream()
        if (run.status === 'failed' || run.status === 'cancelled')
          setNotice(
            run.status === 'cancelled'
              ? 'Esta consulta fue cancelada.'
              : `La consulta terminó con un error: ${run.error_code ?? 'AI_FAILED'}`,
          )
      } catch (error) {
        if (!controller.signal.aborted)
          setNotice(
            error instanceof Error
              ? error.message
              : 'No se pudo abrir la consulta.',
          )
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    })()
    return () => controller.abort()
  }, [runId, resumeStream, setMessages])

  async function send(question: string, options: StudentOptions) {
    setNotice('')
    chat.clearError()
    cursorRef.current = 0
    lastOptions.current = options
    activeRef.current = undefined
    setActiveRun(undefined)
    await chat.sendMessage({ text: question.trim() }, { body: { options } })
  }

  async function retry() {
    if (!lastOptions.current) return
    chat.clearError()
    await chat.regenerate({ body: { options: lastOptions.current } })
  }

  async function cancel() {
    if (!activeRef.current) return
    try {
      await studentFetch(`runs/${activeRef.current}/cancel`, { method: 'POST' })
      await chat.stop()
      setNotice('Consulta cancelada. Puedes iniciar una nueva.')
      void refreshHistory()
    } catch {
      setNotice(
        'No se pudo cancelar. La consulta puede haber terminado; reabre su enlace para ver el estado.',
      )
    }
  }

  function reset() {
    setMessages([])
    setNotice('')
    chat.clearError()
    activeRef.current = undefined
    loadingRef.current = undefined
    pendingKey.current.key = ''
    lastOptions.current = undefined
    cursorRef.current = 0
    setActiveRun(undefined)
  }

  return {
    ...chat,
    send,
    retry,
    cancel,
    reset,
    activeRun,
    history,
    historyOffset,
    refreshHistory,
    historyLoading,
    notice,
    loading,
    retrySeconds: Math.max(0, Math.ceil((retryAt - now) / 1000)),
  }
}
