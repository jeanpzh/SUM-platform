import { Link, createFileRoute } from '@tanstack/react-router'
import { ArrowRight, Link2, LockKeyhole } from 'lucide-react'
import { StudentShell } from '#/components/student/student-shell'

export const Route = createFileRoute('/connections/sum')({
  head: () => ({ meta: [{ title: 'Mi conexión académica · SUM' }] }),
  component: ConnectionView,
})

function ConnectionView() {
  return (
    <StudentShell>
      <div className="student-page-heading">
        <div>
          <p className="student-overline">Mi conexión SUM</p>
          <h1>Tu información, bajo tu control.</h1>
          <p className="student-lead">
            El contexto académico permite orientar una consulta según tu
            situación.
          </p>
        </div>
      </div>
      <div className="student-connection-grid">
        <section className="student-card">
          <Link2 className="size-6" aria-hidden="true" />
          <h2>Conexión académica pendiente</h2>
          <p>
            El adaptador de SUM todavía no está integrado. Puedes consultar la
            normativa institucional y recibir orientación general.
          </p>
          <p className="student-integration-status">
            <span /> Expediente sin conectar
          </p>
          <Link to="/assistant" className="student-inline-link">
            Consultar al asistente <ArrowRight className="size-4" />
          </Link>
        </section>
        <section className="student-card">
          <LockKeyhole className="size-6" aria-hidden="true" />
          <h2>Solo el contexto necesario</h2>
          <p>
            Cuando la integración esté disponible, podrás autorizar el uso de
            datos académicos para una consulta y revocar tu conexión.
          </p>
          <ul className="student-next-steps">
            <li>Se solicitarán únicamente los campos necesarios.</li>
            <li>El contexto tendrá fecha de consulta y vencimiento.</li>
            <li>Las contraseñas no forman parte de una conversación.</li>
            <li>
              Las fuentes normativas y el contexto académico se conservarán por
              separado.
            </li>
          </ul>
        </section>
      </div>
    </StudentShell>
  )
}
