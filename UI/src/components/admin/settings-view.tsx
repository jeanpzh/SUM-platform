import { Save, RotateCcw } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ModeToggle } from '#/components/ModeToggle'
import { useWorkspaceSettings } from '#/hooks/use-workspace-settings'
import { DashboardPage } from './dashboard-page'
import { SettingsField, SettingsSection } from './settings-field'
import { AiProviderSettings } from './ai-provider-settings'
import { EmbeddingSettings } from './embedding-settings'

export function SettingsView() {
  const settings = useWorkspaceSettings()
  const { form } = settings
  return (
    <DashboardPage
      title="Un espacio a tu medida"
      description="Ajusta la recuperación, define el perfil de ingesta y elige cómo trabajar."
    >
      <form onSubmit={settings.save} noValidate>
        <SettingsSection
          number="01"
          title="Espacio de trabajo"
          description="Nombre visible en la navegación y apariencia de este navegador."
        >
          <div>
            <label
              htmlFor="workspace-name"
              className="mb-2 block text-sm font-semibold"
            >
              Nombre del espacio
            </label>
            <Input
              id="workspace-name"
              className="min-h-11"
              {...form.register('workspaceName')}
              aria-invalid={!!form.formState.errors.workspaceName}
              aria-describedby="workspace-name-error"
            />
            {form.formState.errors.workspaceName && (
              <p
                id="workspace-name-error"
                className="mt-2 text-xs text-destructive"
              >
                {form.formState.errors.workspaceName.message}
              </p>
            )}
          </div>
          <div>
            <p className="mb-2 text-sm font-semibold">Apariencia</p>
            <ModeToggle />
          </div>
        </SettingsSection>
        <SettingsSection
          number="02"
          title="Recuperación"
          description="Estos controles se aplican inmediatamente a las consultas locales después de guardar."
        >
          <SettingsField
            form={form}
            name="topK"
            label="Máximo de fragmentos"
            hint="Entre 1 y 10 resultados por consulta."
            min={1}
            max={10}
          />
          <SettingsField
            form={form}
            name="minMatch"
            label="Coincidencia mínima"
            hint="0 a 1: proporción de términos de la consulta presentes en el texto. No es similitud vectorial."
            min={0}
            max={1}
            step={0.05}
          />
        </SettingsSection>
        <SettingsSection
          number="03"
          title="Fragmentación"
          description="Preferencias de fragmentación de la muestra local. El backend usa los valores configurados en el servidor."
        >
          <SettingsField
            form={form}
            name="chunkSize"
            label="Tamaño objetivo · tokens"
            hint="64 a 480 tokens. Reserva margen dentro del límite del modelo."
            min={64}
            max={480}
          />
          <SettingsField
            form={form}
            name="overlap"
            label="Solapamiento · tokens"
            hint="0 a 120 tokens, siempre menor que el fragmento."
            min={0}
            max={120}
          />
        </SettingsSection>
        <SettingsSection
          number="04"
          title="Ejecución de ingesta"
          description="Preferencias locales. La concurrencia y los tamaños de lote del backend se configuran en el servidor."
        >
          <SettingsField
            form={form}
            name="embeddingBatchSize"
            label="Lote de embeddings"
            hint="1 a 64 fragmentos por lote. Valor documentado: 32."
            min={1}
            max={64}
          />
          <SettingsField
            form={form}
            name="extractionConcurrency"
            label="Extracciones simultáneas"
            hint="1 a 8 procesos. Valor documentado: 2."
            min={1}
            max={8}
          />
          <SettingsField
            form={form}
            name="pageBatchSize"
            label="Páginas por lote"
            hint="1 a 100 páginas. Valor documentado: 10."
            min={1}
            max={100}
          />
        </SettingsSection>
        <div className="mt-7 flex flex-wrap items-center justify-between gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={settings.restoreDefaults}
          >
            <RotateCcw size={15} />
            Restaurar valores
          </Button>
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-xs text-muted-foreground">
              {form.formState.isDirty
                ? 'Hay cambios pendientes'
                : 'Sin cambios pendientes'}
            </span>
            <Button
              type="submit"
              className="min-h-11"
              disabled={!settings.loaded || !form.formState.isDirty}
            >
              <Save size={16} />
              Guardar configuración
            </Button>
          </div>
        </div>
        {settings.notice && (
          <p role="status" className="mt-4 text-sm text-success">
            {settings.notice}
          </p>
        )}
      </form>
      <EmbeddingSettings />
      <AiProviderSettings />
    </DashboardPage>
  )
}
