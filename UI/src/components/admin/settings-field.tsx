import { useId } from 'react'
import type { UseFormReturn } from 'react-hook-form'
import { Input } from '#/components/ui/input'
import type { WorkspaceSettings } from '#/lib/admin-workspace/schema'

export function SettingsField({
  form,
  name,
  label,
  hint,
  min,
  max,
  step = 1,
}: {
  form: UseFormReturn<WorkspaceSettings>
  name: Exclude<keyof WorkspaceSettings, 'workspaceName'>
  label: string
  hint: string
  min: number
  max: number
  step?: number
}) {
  const id = useId()
  const error = form.formState.errors[name]?.message
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">
        {label}
      </label>
      <Input
        id={id}
        type="number"
        min={min}
        max={max}
        step={step}
        className="min-h-11 bg-background"
        {...form.register(name, { valueAsNumber: true })}
        aria-invalid={!!error}
        aria-describedby={id + '-help'}
      />
      <p
        id={id + '-help'}
        className={`mt-2 text-xs leading-5 ${error ? 'text-destructive' : 'text-muted-foreground'}`}
      >
        {error ?? hint}
      </p>
    </div>
  )
}

export function SettingsSection({
  number,
  title,
  description,
  children,
}: {
  number: string
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <section className="grid gap-6 border-b border-border py-7 first:pt-0 md:grid-cols-[220px_1fr]">
      <div>
        <p className="mb-2 text-xs text-muted-foreground">{number}</p>
        <h2 className="font-display text-2xl">{title}</h2>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          {description}
        </p>
      </div>
      <div className="grid content-start gap-5 sm:grid-cols-2">{children}</div>
    </section>
  )
}
