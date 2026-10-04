import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from '@tanstack/react-router'
import {
  ArrowDown,
  ArrowRight,
  BookOpen,
  Clock3,
  GraduationCap,
  LoaderCircle,
  Plus,
  Send,
  Square,
  Link2,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { useStudentChat } from '#/hooks/use-student-chat'
import { StudentShell } from './student-shell'
import { StudentResultPanel } from './student-result'
import type { StudentMessage } from '#/lib/student/contracts'

const suggestions = [
  {
    title: 'Matrícula y cursos',
    text: '¿Qué normas debo revisar antes de matricularme?',
    icon: BookOpen,
  },
  {
    title: 'Mi situación académica',
    text: 'Desaprobé un curso más de una vez. ¿Qué normativa debo revisar?',
    icon: GraduationCap,
  },
  {
    title: 'Trámites y plazos',
    text: '¿Cómo puedo revisar los requisitos de retiro de un curso?',
    icon: Clock3,
  },
]
const stageLabels: Record<string, string> = {
  validating: 'Validando tu consulta',
  planning: 'Identificando qué necesitas',
  collecting_context: 'Verificando el contexto académico',
  retrieving: 'Buscando fuentes institucionales',
  researching: 'Contrastando la evidencia',
  checking: 'Comprobando reglas revisadas',
  composing: 'Preparando la orientación',
  verifying: 'Validando las fuentes de la respuesta',
}

function ChatMessage({ message }: { message: StudentMessage }) {
  const result = message.parts.find((part) => part.type === 'data-result')
  const stages = message.parts.filter(
    (part) => part.type === 'data-audit' && part.data.stage,
  )
  const lastStage = stages.at(-1)
  return (
    <article className={`student-message student-message-${message.role}`}>
      <p className="student-message-author">
        {message.role === 'user' ? 'Tu consulta' : 'Asistente SUM'}
      </p>
      {message.parts
        .filter((part) => part.type === 'text')
        .map((part, index) => (
          <p key={index} className="student-answer-text">
            {part.text}
          </p>
        ))}
      {message.role === 'assistant' &&
        !result &&
        lastStage?.type === 'data-audit' && (
          <p role="status" className="student-progress">
            <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />{' '}
            {stageLabels[lastStage.data.stage ?? ''] ??
              'Procesando la consulta'}
          </p>
        )}
      {result?.type === 'data-result' && (
        <StudentResultPanel
          result={result.data}
          runId={message.metadata?.run_id ?? message.id}
        />
      )}
      {stages.length > 0 && (
        <details className="student-public-progress">
          <summary>Ver etapas de la consulta</summary>
          <ol>
            {stages
              .filter(
                (part, index) =>
                  part.type === 'data-audit' &&
                  stages.findIndex(
                    (other) =>
                      other.type === 'data-audit' &&
                      other.data.stage === part.data.stage,
                  ) === index,
              )
              .map(
                (part) =>
                  part.type === 'data-audit' && (
                    <li key={part.data.sequence}>
                      {stageLabels[part.data.stage ?? ''] ?? part.data.stage}
                    </li>
                  ),
              )}
          </ol>
        </details>
      )}
    </article>
  )
}

export function StudentView() {
  const params = useParams({ strict: false }) as { runId?: string }
  const navigate = useNavigate()
  const chat = useStudentChat(params.runId, (id) => {
    void navigate({
      to: '/assistant/$runId',
      params: { runId: id },
      replace: true,
    })
  })
  const [input, setInput] = useState('')
  const [course, setCourse] = useState('')
  const [useContext, setUseContext] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const busy =
    chat.status === 'submitted' || chat.status === 'streaming' || chat.loading
  const hasMessages = chat.messages.length > 0

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'instant', block: 'nearest' })
  }, [chat.messages.length])
  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (busy || chat.retrySeconds || input.trim().length < 3) return
    const question = input.trim()
    setInput('')
    await chat.send(question, {
      use_academic_context: useContext,
      course_hint: course.trim() || null,
    })
  }
  function choose(text: string) {
    setInput(text)
    inputRef.current?.focus()
  }
  function newConsultation() {
    chat.reset()
    setInput('')
    void navigate({ to: '/assistant' })
    inputRef.current?.focus()
  }
  const history = (
    <>
      <div className="student-history-heading">
        <p className="student-overline">Consultas recientes</p>
        <Button
          variant="ghost"
          size="icon"
          className="student-button"
          onClick={newConsultation}
          disabled={busy}
          aria-label="Nueva consulta"
        >
          <Plus className="size-4" />
        </Button>
      </div>
      {chat.historyLoading && (
        <p className="student-muted" role="status">
          Cargando historial…
        </p>
      )}
      {!chat.historyLoading && chat.history.length === 0 && (
        <p className="student-muted">
          Tus consultas aparecerán aquí al iniciar sesión.
        </p>
      )}
      <div className="student-history-list">
        {chat.history.map((run) => (
          <Link
            key={run.run_id}
            to="/assistant/$runId"
            params={{ runId: run.run_id }}
            aria-disabled={busy}
            onClick={(event) => {
              if (busy) event.preventDefault()
            }}
            data-active={chat.activeRun === run.run_id}
          >
            <span>{run.question}</span>
            <small>
              {run.status === 'completed'
                ? 'Finalizada'
                : run.status === 'failed'
                  ? 'Con error'
                  : run.status === 'cancelled'
                    ? 'Cancelada'
                    : 'En curso'}
            </small>
          </Link>
        ))}
      </div>
      <div className="student-history-pagination">
        <button
          disabled={busy || chat.historyLoading || chat.historyOffset === 0}
          onClick={() => {
            void chat.refreshHistory(Math.max(0, chat.historyOffset - 20))
          }}
        >
          Anteriores
        </button>
        <button
          disabled={busy || chat.historyLoading || chat.history.length < 20}
          onClick={() => {
            void chat.refreshHistory(chat.historyOffset + 20)
          }}
        >
          Más consultas
        </button>
      </div>
    </>
  )

  return (
    <StudentShell history={history}>
      <div className="student-page-heading">
        <div>
          <p className="student-overline">Asistente académico</p>
          <h1>
            {hasMessages
              ? 'Tu consulta, con contexto.'
              : 'Encuentra claridad para tu siguiente paso.'}
          </h1>
          <p className="student-lead">
            Consulta las normas de tu universidad y revisa las fuentes que
            respaldan cada orientación.
          </p>
        </div>
        {hasMessages && (
          <Button
            variant="outline"
            onClick={newConsultation}
            disabled={busy}
            className="student-button"
          >
            <Plus className="size-4" /> Nueva consulta
          </Button>
        )}
      </div>
      <div className="student-consultation-grid">
        <section className="student-chat" aria-label="Consulta al asistente">
          {!hasMessages && (
            <div className="student-welcome">
              <p className="student-welcome-label">¿Por dónde empezamos?</p>
              <div className="student-suggestions">
                {suggestions.map(({ title, text, icon: Icon }) => (
                  <button key={title} onClick={() => choose(text)}>
                    <Icon className="size-5" aria-hidden="true" />
                    <strong>{title}</strong>
                    <span>{text}</span>
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </button>
                ))}
              </div>
            </div>
          )}
          <div
            className="student-transcript"
            aria-label="Conversación"
            aria-busy={busy}
          >
            {chat.messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {chat.status === 'submitted' && (
              <p className="student-progress" role="status">
                <LoaderCircle className="size-4 animate-spin" /> Iniciando la
                consulta…
              </p>
            )}
            {chat.loading && (
              <p role="status" className="student-muted">
                Recuperando tu consulta…
              </p>
            )}
            <div ref={endRef} />
          </div>
          {(chat.error || chat.notice) && (
            <div role="alert" className="student-error">
              <p>{chat.error?.message ?? chat.notice}</p>
              <Link to="/login" search={{ mode: 'student' }}>
                Revisar mi sesión <ArrowRight className="size-4" />
              </Link>
              {chat.error && !chat.activeRun && !busy && (
                <Button
                  variant="outline"
                  className="student-button"
                  disabled={chat.retrySeconds > 0}
                  onClick={() => {
                    void chat.retry()
                  }}
                >
                  Reintentar consulta
                </Button>
              )}
              {chat.activeRun && !busy && (
                <Button
                  variant="outline"
                  className="student-button"
                  onClick={() => {
                    chat.clearError()
                    void chat.resumeStream()
                  }}
                >
                  Reconectar consulta
                </Button>
              )}
            </div>
          )}
          {chat.retrySeconds > 0 && (
            <p role="status" className="student-context-note">
              Puedes volver a consultar en {chat.retrySeconds} s.
            </p>
          )}
          <form onSubmit={submit} className="student-composer">
            <label htmlFor="student-question" className="sr-only">
              Tu consulta académica
            </label>
            <textarea
              ref={inputRef}
              id="student-question"
              rows={3}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Escribe tu duda sobre matrícula, cursos o normativa…"
              minLength={3}
              maxLength={2000}
              required
              disabled={busy}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
            />
            <div className="student-composer-footer">
              <span>
                {input.length}/2000{' '}
                <span className="student-key-hint">
                  · Ctrl + Enter para enviar
                </span>
              </span>
              {busy ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    void chat.cancel()
                  }}
                  disabled={!chat.activeRun}
                  className="student-button"
                >
                  <Square className="size-4" /> Cancelar
                </Button>
              ) : (
                <Button
                  type="submit"
                  className="student-button student-primary"
                  disabled={input.trim().length < 3 || chat.retrySeconds > 0}
                >
                  <Send className="size-4" /> Consultar
                </Button>
              )}
            </div>
          </form>
          <p className="student-composer-note">
            Cada consulta busca sus propias fuentes. Evita incluir contraseñas,
            códigos personales o datos sensibles.
          </p>
          {hasMessages && (
            <button
              className="student-scroll-link"
              onClick={() =>
                endRef.current?.scrollIntoView({ behavior: 'instant' })
              }
            >
              <ArrowDown className="size-4" /> Ir al final
            </button>
          )}
        </section>
        <aside
          className="student-context-rail"
          aria-label="Contexto de la consulta"
        >
          <section className="student-card">
            <p className="student-overline">Contexto académico</p>
            <h2>Una orientación para tu caso</h2>
            <p>
              Indica el curso si tu pregunta se refiere a uno en particular.
            </p>
            <label htmlFor="student-course">Curso (opcional)</label>
            <input
              id="student-course"
              value={course}
              onChange={(event) => setCourse(event.target.value)}
              maxLength={120}
              placeholder="Ej. Matemática básica"
              disabled={busy}
            />
            <label className="student-checkbox">
              <input
                type="checkbox"
                checked={useContext}
                onChange={(event) => setUseContext(event.target.checked)}
                disabled={busy}
              />
              <span>Autorizar contexto académico cuando esté disponible</span>
            </label>
            <p className="student-integration-status">
              <span /> Conexión SUM pendiente
            </p>
            <p>
              El expediente aún no está conectado. Si tu consulta lo necesita,
              verás qué datos faltan por verificar.
            </p>
            <Link to="/connections/sum" className="student-inline-link">
              <Link2 className="size-4" /> Ver mi conexión{' '}
              <ArrowRight className="size-4" />
            </Link>
          </section>
          <section className="student-guide">
            <p className="student-overline">Cómo funciona</p>
            <ol>
              <li>
                <span>01</span>
                <div>
                  <strong>Entiende tu consulta</strong>
                  <p>Identifica la información que necesitas.</p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <strong>Busca y contrasta</strong>
                  <p>Revisa las fuentes institucionales publicadas.</p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <strong>Te orienta con evidencia</strong>
                  <p>Muestra las citas y los límites de la respuesta.</p>
                </div>
              </li>
            </ol>
          </section>
        </aside>
      </div>
    </StudentShell>
  )
}
