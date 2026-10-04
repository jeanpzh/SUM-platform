import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  BookOpenText,
  BriefcaseBusiness,
  Menu,
  Settings2,
  X,
  Library,
  Search,
  MessagesSquare,
  ChartColumn,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ModeToggle } from '#/components/ModeToggle'
import { BrandMark } from './brand-mark'
import { useWorkspace } from '#/components/admin/workspace-provider'

type DashboardShellProps = {
  children: React.ReactNode
}

function DashboardNavigation({ onNavigate }: { onNavigate?: () => void }) {
  const items = [
    { to: '/', label: 'Ingesta de PDF', icon: BookOpenText },
    { to: '/admin/library', label: 'Biblioteca', icon: Library },
    { to: '/admin/search', label: 'Explorar fragmentos', icon: Search },
    { to: '/admin/chat', label: 'Probar respuestas', icon: MessagesSquare },
    { to: '/admin/metrics', label: 'Métricas RAG', icon: ChartColumn },
    { to: '/admin/jobs', label: 'Trabajos', icon: BriefcaseBusiness },
    { to: '/admin/settings', label: 'Configuración', icon: Settings2 },
  ] as const
  return (
    <>
      <nav aria-label="Navegación principal" className="space-y-1.5">
        {items.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            onClick={onNavigate}
            activeOptions={{ exact: true }}
            activeProps={{
              className:
                'border-primary bg-primary/10 font-semibold text-primary',
              'aria-current': 'page',
            }}
            inactiveProps={{
              className: 'border-transparent text-muted-foreground',
            }}
            className="flex min-h-11 items-center gap-3 rounded-md border-l-[3px] px-3 text-sm no-underline transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            <Icon size={18} strokeWidth={1.6} aria-hidden="true" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="flex items-center gap-3 border-t border-border pt-5 text-sm text-muted-foreground">
        <span className="size-1.5 rounded-full bg-warning" aria-hidden="true" />
        Administración de fuentes
      </div>
    </>
  )
}

export function DashboardShell({ children }: DashboardShellProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const workspaceName = useWorkspace(
    (store) => store.state.settings.workspaceName,
  )

  return (
    <div className="pdf-dashboard min-h-dvh bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-10 hidden w-64 flex-col border-r border-border bg-background px-5 py-7 lg:flex">
        <BrandMark />
        <div className="mt-12 flex-1">
          <DashboardNavigation />
        </div>
        <div className="mb-4 border-t border-border pt-4">
          <ModeToggle />
        </div>
        <div className="flex items-center gap-3 border-t border-border pt-5">
          <div className="grid size-9 place-items-center rounded-full bg-muted text-muted-foreground">
            <span className="text-xs font-semibold">AD</span>
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-foreground">
              Administrador
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {workspaceName}
            </p>
          </div>
        </div>
      </aside>

      <div className="min-w-0 lg:ml-64">
        <header className="flex min-h-16 items-center justify-between border-b border-border px-4 sm:px-6 lg:hidden">
          <BrandMark />
          <div className="flex items-center gap-2">
            <ModeToggle compact />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={mobileNavOpen ? 'Cerrar menú' : 'Abrir menú'}
              aria-expanded={mobileNavOpen}
              aria-controls="mobile-dashboard-navigation"
              onClick={() => setMobileNavOpen((open) => !open)}
              className="size-11 text-muted-foreground hover:bg-accent"
            >
              {mobileNavOpen ? (
                <X strokeWidth={1.6} />
              ) : (
                <Menu strokeWidth={1.6} />
              )}
            </Button>
          </div>
        </header>

        {mobileNavOpen && (
          <div
            id="mobile-dashboard-navigation"
            className="space-y-5 border-b border-border bg-background px-4 py-4 lg:hidden"
          >
            <DashboardNavigation onNavigate={() => setMobileNavOpen(false)} />
            <div className="flex items-center gap-3 border-t border-border pt-4 text-sm text-muted-foreground">
              <span className="grid size-9 place-items-center rounded-full bg-muted text-xs font-semibold">
                AD
              </span>
              Administrador
            </div>
          </div>
        )}

        {children}
      </div>
    </div>
  )
}
