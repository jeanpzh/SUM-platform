import { createContext, useContext, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark' | 'system'

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

type ThemeProviderState = {
  theme: Theme
  ready: boolean
  setTheme: (theme: Theme) => void
}

const ThemeProviderContext = createContext<ThemeProviderState | null>(null)

function readStoredTheme(storageKey: string, fallback: Theme): Theme {
  try {
    const stored = window.localStorage.getItem(storageKey)
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored
    }
    // Keep preferences saved by the previous theme toggle working.
    if (stored === 'auto') {
      window.localStorage.setItem(storageKey, 'system')
      return 'system'
    }
  } catch {
    // Storage can be disabled; the system preference still works.
  }
  return fallback
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  const systemIsDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const resolvedTheme =
    theme === 'system' ? (systemIsDark ? 'dark' : 'light') : theme

  root.classList.remove('light', 'dark')
  root.classList.add(resolvedTheme)
  root.style.colorScheme = resolvedTheme

  if (theme === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', theme)
  }
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'theme',
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(defaultTheme)
  const [themeLoaded, setThemeLoaded] = useState(false)

  useEffect(() => {
    setThemeState(readStoredTheme(storageKey, defaultTheme))
    setThemeLoaded(true)
  }, [defaultTheme, storageKey])

  useEffect(() => {
    if (!themeLoaded) return
    applyTheme(theme)
    if (theme !== 'system') return

    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => applyTheme('system')
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [theme, themeLoaded])

  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key === storageKey) {
        setThemeState(readStoredTheme(storageKey, defaultTheme))
      }
    }

    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [defaultTheme, storageKey])

  function setTheme(nextTheme: Theme) {
    try {
      window.localStorage.setItem(storageKey, nextTheme)
    } catch {
      // Keep the in-memory selection usable when storage is unavailable.
    }
    setThemeState(nextTheme)
  }

  return (
    <ThemeProviderContext.Provider
      value={{ theme, ready: themeLoaded, setTheme }}
    >
      {children}
    </ThemeProviderContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeProviderContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
