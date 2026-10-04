import { Check, ChevronDown, Monitor, Moon, Sun } from 'lucide-react'
import { Button } from '#/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '#/components/ui/dropdown-menu'
import type { Theme } from './theme-provider'
import { useTheme } from './theme-provider'

const themes: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Claro', icon: Sun },
  { value: 'dark', label: 'Oscuro', icon: Moon },
  { value: 'system', label: 'Sistema', icon: Monitor },
]

type ModeToggleProps = {
  compact?: boolean
}

export function ModeToggle({ compact = false }: ModeToggleProps) {
  const { theme, ready, setTheme } = useTheme()
  const currentTheme = themes.find((option) => option.value === theme)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size={compact ? 'icon' : 'default'}
          aria-label="Cambiar apariencia"
          disabled={!ready}
          className={
            compact
              ? 'size-10 border-border bg-background text-foreground'
              : 'h-11 w-full justify-between border-border bg-background px-3 text-foreground hover:bg-accent'
          }
        >
          <span className="flex items-center gap-2.5">
            <Sun className="size-4 dark:hidden" aria-hidden="true" />
            <Moon className="hidden size-4 dark:block" aria-hidden="true" />
            {compact ? (
              <span className="sr-only">Cambiar apariencia</span>
            ) : (
              <span className="text-sm font-medium">Apariencia</span>
            )}
          </span>
          {!compact && (
            <span className="flex items-center gap-2 text-xs text-muted-foreground">
              {currentTheme?.label}
              <ChevronDown className="size-3.5" aria-hidden="true" />
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        {themes.map(({ value, label, icon: Icon }) => (
          <DropdownMenuItem
            key={value}
            onSelect={() => setTheme(value)}
            aria-current={theme === value ? 'true' : undefined}
            className="justify-between"
          >
            <span className="flex items-center gap-2.5">
              <Icon
                className="size-4 text-muted-foreground"
                aria-hidden="true"
              />
              {label}
            </span>
            {theme === value && (
              <Check className="size-4 text-primary" aria-hidden="true" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
