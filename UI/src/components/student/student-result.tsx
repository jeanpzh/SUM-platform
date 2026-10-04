import {
  BookOpen,
  CheckCircle2,
  Download,
  Info,
  ListChecks,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import type { StudentResult } from '#/lib/student/contracts'
import {
  reasonLabels,
  toolLabels,
  validationLabels,
} from '#/lib/student/deterministic-results'

const contextLabels = {
  available: 'Contexto académico disponible',
  not_requested: 'Consulta sin expediente académico',
  missing: 'Falta una conexión académica',
  unavailable: 'Contexto académico no disponible',
  expired: 'Contexto académico vencido',
}
const outcomeLabels = {
  satisfied: 'Condición verificada',
  not_satisfied: 'Condición no satisfecha',
  unknown: 'Aplicabilidad no resuelta',
}

function Sources({ result }: { result: StudentResult }) {
  const indexed = new Map(result.evidence.map((item) => [item.chunk_id, item]))
  const sourceIds = new Set([
    ...result.citations.map((item) => item.chunk_id),
    ...(result.student_analysis?.deterministic_results.flatMap(
      (item) => item.result.citationIds,
    ) ?? []),
    ...(result.student_analysis?.checks.flatMap(
      (check) => check.citation_ids,
    ) ?? []),
  ])
  const sources = [...sourceIds].flatMap((id) => {
    const source = indexed.get(id)
    return source ? [source] : []
  })
  return (
    <section
      className="student-result-section"
      aria-label="Fuentes de la respuesta"
    >
      <h3>
        <BookOpen className="size-4" aria-hidden="true" /> Fuentes verificables{' '}
        <span>{sources.length}</span>
      </h3>
      {sources.length === 0 && (
        <p className="student-muted">
          Esta respuesta no aporta una conclusión normativa con citas.
        </p>
      )}
      {sources.map((citation, index) => (
        <details key={citation.chunk_id} className="student-source">
          <summary>
            <span className="student-source-number">{index + 1}</span>
            <span>
              {citation.locator || 'Documento institucional'}
              <small>Página {citation.page} · Ver fragmento</small>
            </span>
          </summary>
          <blockquote>
            {indexed.get(citation.chunk_id)?.text ??
              'El fragmento no está disponible.'}
          </blockquote>
          <p className="student-source-reference">
            Documento {citation.document_id}
            <br />
            Versión {citation.version_id}
            <br />
            Publicación {citation.generation_id}
          </p>
        </details>
      ))}
    </section>
  )
}

function ContextStatus({ result }: { result: StudentResult }) {
  const context = result.student_analysis?.context
  if (!context) return null
  return (
    <section
      className="student-context-note"
      aria-label="Disponibilidad del contexto académico"
    >
      <Info className="size-4 shrink-0" aria-hidden="true" />
      <div>
        <strong>{contextLabels[context.status]}</strong>
        {context.source === 'mock' && (
          <p>Datos simulados. No corresponden a un expediente SUM real.</p>
        )}
        {context.status !== 'available' && (
          <p>La orientación debe contrastarse con tu situación académica.</p>
        )}
        {context.missing_fields.length > 0 && (
          <p>
            Hay {context.missing_fields.length} campos académicos pendientes de
            verificar.
          </p>
        )}
      </div>
    </section>
  )
}

function RuleChecks({ result }: { result: StudentResult }) {
  const checks = result.student_analysis?.checks ?? []
  const computations = result.student_analysis?.deterministic_results ?? []
  return (
    <section className="student-result-section">
      <h3>
        <ListChecks className="size-4" aria-hidden="true" /> Comprobaciones
      </h3>
      {computations.map(({ tool, result: computation }) => (
        <div key={tool} className="student-rule">
          <strong>
            {toolLabels[tool]} · {validationLabels[computation.status]}
          </strong>
          {computation.reasons.map((reason) => (
            <p key={reason}>{reasonLabels[reason]}</p>
          ))}
          {computation.totalCredits !== null && (
            <p>
              {computation.totalCredits} créditos
              {computation.creditLimit !== null
                ? ` · límite ${computation.creditLimit}`
                : ''}
            </p>
          )}
          {computation.checks.map((check) => (
            <p key={check.courseCode}>
              {check.courseCode}: {validationLabels[check.status]}
              {check.missingPrerequisites.length
                ? ` · pendientes: ${check.missingPrerequisites.join(', ')}`
                : ''}
            </p>
          ))}
          {computation.conflicts.map((conflict, index) => (
            <p key={index}>
              {conflict.courseA} / {conflict.courseB}: cruce el{' '}
              {conflict.day.toLocaleLowerCase('es')}
            </p>
          ))}
          {computation.status === 'VALID' &&
            computation.alternatives.map((alternative, index) => (
              <p key={index}>
                Alternativa {index + 1}:{' '}
                {alternative.selections
                  .map((s) => `${s.courseCode}, sección ${s.section}`)
                  .join(' · ')}{' '}
                · {alternative.totalCredits} créditos ·{' '}
                {alternative.idleMinutes} minutos libres entre clases
              </p>
            ))}
          {tool === 'simulate_enrollment' && (
            <p className="student-muted">
              {computation.examinedCombinations} combinaciones revisadas.{' '}
              {computation.truncated ? 'Búsqueda parcial.' : ''} Esta simulación
              no realiza matrícula oficial.
            </p>
          )}
          {computation.ruleVersion && (
            <small>
              Regla {computation.ruleId} · Versión {computation.ruleVersion}
            </small>
          )}
        </div>
      ))}
      {checks.length === 0 && computations.length === 0 ? (
        <p className="student-muted">
          No se aplicó una regla institucional revisada a tu expediente.
        </p>
      ) : (
        checks.map((check) => (
          <div key={check.rule_id} className="student-rule">
            <strong>{outcomeLabels[check.outcome]}</strong>
            <p>{check.description}</p>
            <small>
              Regla {check.rule_id} · Versión {check.version}
            </small>
          </div>
        ))
      )}
    </section>
  )
}

function NextSteps({ result }: { result: StudentResult }) {
  const steps = result.student_analysis?.next_steps ?? []
  if (!steps.length) return null
  return (
    <section className="student-result-section">
      <h3>
        <CheckCircle2 className="size-4" aria-hidden="true" /> Cómo continuar
      </h3>
      <ul className="student-next-steps">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>
    </section>
  )
}

// A future MCP may return only these typed component names and validated data.
// It cannot supply JSX, HTML, JavaScript, URLs or additional business actions.
const components = {
  sources: Sources,
  context_status: ContextStatus,
  rule_checks: RuleChecks,
  next_steps: NextSteps,
}

export function StudentResultPanel({
  result,
  runId,
}: {
  result: StudentResult
  runId: string
}) {
  function download() {
    const blob = new Blob(
      [JSON.stringify({ run_id: runId, result }, null, 2)],
      { type: 'application/json' },
    )
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `consulta-${runId}.json`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return (
    <div className="student-result-panel">
      {result.limitations.length > 0 && (
        <div className="student-limitations">
          <strong>Alcance de esta orientación</strong>
          <ul>
            {result.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {[
        ...new Set(
          result.student_analysis?.components ?? (['sources'] as const),
        ),
      ].map((name) => {
        const Component = components[name]
        return <Component key={name} result={result} />
      })}
      <details className="student-audit-details">
        <summary>Trazabilidad de la consulta</summary>
        <dl>
          <dt>Consulta</dt>
          <dd>{runId}</dd>
          <dt>Traza</dt>
          <dd>{result.student_analysis?.trace_id ?? 'Registro local'}</dd>
          <dt>Modelo</dt>
          <dd>
            {result.provider} · {result.model}
          </dd>
          <dt>Tokens utilizados</dt>
          <dd>{result.usage.input_tokens + result.usage.output_tokens}</dd>
          <dt>Duración</dt>
          <dd>{Math.round((result.timings.total_ms ?? 0) / 1000)} s</dd>
        </dl>
        <Button variant="outline" onClick={download} className="student-button">
          <Download className="size-4" /> Descargar respuesta y fuentes
        </Button>
      </details>
    </div>
  )
}
