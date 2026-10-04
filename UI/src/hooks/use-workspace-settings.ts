import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useState } from 'react'
import { useWorkspace } from '#/components/admin/workspace-provider'
import { defaultSettings, settingsSchema } from '#/lib/admin-workspace/schema'
import type { WorkspaceSettings } from '#/lib/admin-workspace/schema'

export function useWorkspaceSettings() {
  const settings = useWorkspace((store) => store.state.settings)
  const loaded = useWorkspace((store) => store.loaded)
  const dispatch = useWorkspace((store) => store.dispatch)
  const [notice, setNotice] = useState('')
  const form = useForm<WorkspaceSettings>({
    resolver: zodResolver(settingsSchema),
    values: settings,
    resetOptions: { keepDirtyValues: true },
  })
  const save = form.handleSubmit((values) => {
    dispatch({ type: 'settings', settings: values })
    form.reset(values)
    setNotice('Configuración aplicada al espacio local.')
  })
  function restoreDefaults() {
    for (const [key, value] of Object.entries(defaultSettings)) {
      form.setValue(key as keyof WorkspaceSettings, value, {
        shouldDirty: true,
        shouldValidate: true,
      })
    }
    setNotice('Valores iniciales restaurados. Guarda para aplicarlos.')
  }
  return { form, save, restoreDefaults, loaded, notice }
}
