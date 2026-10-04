import {
  HeadContent,
  Scripts,
  createRootRoute,
  useRouterState,
} from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'
import Footer from '../components/Footer'
import Header from '../components/Header'
import { ThemeProvider } from '../components/theme-provider'
import { WorkspaceProvider } from '../components/admin/workspace-provider'

import StoreDevtools from '../lib/demo-store-devtools'

import appCss from '../styles.css?url'
import studentCss from '../student.css?url'

const THEME_INIT_SCRIPT = `(function(){try{var stored=window.localStorage.getItem('theme');var mode=(stored==='light'||stored==='dark'||stored==='system')?stored:'system';var prefersDark=window.matchMedia('(prefers-color-scheme: dark)').matches;var resolved=mode==='system'?(prefersDark?'dark':'light'):mode;var root=document.documentElement;root.classList.remove('light','dark');root.classList.add(resolved);if(mode==='system'){root.removeAttribute('data-theme')}else{root.setAttribute('data-theme',mode)}root.style.colorScheme=resolved;}catch(e){}})();`

export const Route = createRootRoute({
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        title: 'Documentos institucionales · SUM',
      },
    ],
    links: [
      {
        rel: 'stylesheet',
        href: appCss,
      },
      { rel: 'stylesheet', href: studentCss },
    ],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  const isPdfDashboard = useRouterState({
    select: (state) =>
      state.location.pathname === '/' ||
      state.location.pathname.startsWith('/admin') ||
      state.location.pathname.startsWith('/assistant') ||
      state.location.pathname.startsWith('/connections') ||
      state.location.pathname === '/login',
  })

  return (
    <html lang={isPdfDashboard ? 'es' : 'en'} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <HeadContent />
      </head>
      <body
        className={`${isPdfDashboard ? 'pdf-dashboard-body selection:bg-[#F3D7C9]' : 'selection:bg-[rgba(79,184,178,0.24)]'} font-sans antialiased [overflow-wrap:anywhere]`}
      >
        <ThemeProvider>
          <WorkspaceProvider>
            {!isPdfDashboard && <Header />}
            {children}
            {!isPdfDashboard && <Footer />}
            {!isPdfDashboard && (
              <TanStackDevtools
                config={{
                  position: 'bottom-right',
                }}
                plugins={[
                  {
                    name: 'Tanstack Router',
                    render: <TanStackRouterDevtoolsPanel />,
                  },
                  StoreDevtools,
                ]}
              />
            )}
            <Scripts />
          </WorkspaceProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
