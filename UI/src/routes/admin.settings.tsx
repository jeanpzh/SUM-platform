import { createFileRoute } from '@tanstack/react-router'
import { SettingsView } from '#/components/admin/settings-view'

export const Route = createFileRoute('/admin/settings')({
  component: SettingsView,
})
