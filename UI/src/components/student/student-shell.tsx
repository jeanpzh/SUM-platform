import { Link, useLocation } from '@tanstack/react-router'
import {
  BookOpen,
  GraduationCap,
  Link2,
  MessageSquare,
  ShieldCheck,
} from 'lucide-react'
import { ModeToggle } from '#/components/ModeToggle'
import type { ReactNode } from 'react'

export function StudentShell({
  children,
  history,
}: {
  children: ReactNode
  history?: ReactNode
}) {
  const location = useLocation()
  const connected = location.pathname.startsWith('/connections')
  return (
    <div className="student-workspace">
      <a href="#student-content" className="student-skip">
        Saltar al contenido
      </a>
      <aside className="student-sidebar" aria-label="Espacio del estudiante">
        <Link to="/assistant" className="student-brand">
          <GraduationCap aria-hidden="true" className="size-7" />
          <span>
            <strong>SUM</strong>
            <small>Orientación académica</small>
          </span>
        </Link>
        <p className="student-overline">Mi espacio</p>
        <nav className="student-nav" aria-label="Navegación estudiantil">
          <Link
            to="/assistant"
            data-active={!connected}
            aria-current={!connected ? 'page' : undefined}
          >
            <MessageSquare className="size-4" aria-hidden="true" /> Asistente
          </Link>
          <Link
            to="/connections/sum"
            data-active={connected}
            aria-current={connected ? 'page' : undefined}
          >
            <Link2 className="size-4" aria-hidden="true" /> Mi conexión SUM
          </Link>
        </nav>
        {history && (
          <section
            className="student-history"
            aria-label="Historial de consultas"
          >
            <div className="student-history-desktop">{history}</div>
            <details className="student-history-mobile">
              <summary>Mis consultas recientes</summary>
              {history}
            </details>
          </section>
        )}
        <div className="student-sidebar-foot">
          <div className="student-privacy">
            <ShieldCheck className="size-4" aria-hidden="true" />
            <p>
              Tus consultas son privadas.
              <br />
              <span>Las respuestas conservan sus fuentes.</span>
            </p>
          </div>
          <ModeToggle />
        </div>
      </aside>
      <div className="student-main">
        <header className="student-topbar">
          <span className="flex items-center gap-2">
            <BookOpen className="size-4" aria-hidden="true" /> Portal del
            estudiante
          </span>
          <Link
            to="/login"
            search={{ mode: 'student' }}
            className="student-session-link"
          >
            Mi sesión
          </Link>
        </header>
        <main id="student-content" className="student-content">
          {children}
        </main>
      </div>
    </div>
  )
}
