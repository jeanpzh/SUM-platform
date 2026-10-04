import { RefreshCw, Save } from 'lucide-react'
import { useEmbeddingAdministration } from '#/hooks/use-embedding-administration'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { SettingsSection } from './settings-field'
import { selectClass } from './corpus-scope'

export function EmbeddingSettings() {
  const settings = useEmbeddingAdministration()
  const { form } = settings
  const provider = form.watch('provider')
  const errors = form.formState.errors
  return (
    <form onSubmit={settings.save} noValidate className="mt-8">
      <SettingsSection
        number="05"
        title="Modelo de embeddings"
        description="Configuración guardada en el backend. Cada trabajo conserva el perfil con el que fue creado."
      >
        <div>
          <label
            htmlFor="embedding-provider"
            className="mb-2 block text-sm font-semibold"
          >
            Proveedor
          </label>
          <select
            id="embedding-provider"
            className={selectClass}
            {...form.register('provider')}
          >
            <option value="tei">TEI · servidor local</option>
            <option value="ollama">Ollama · servidor local</option>
            <option value="openai">OpenAI · cloud</option>
          </select>
        </div>
        <div>
          <label
            htmlFor="embedding-model"
            className="mb-2 block text-sm font-semibold"
          >
            Modelo
          </label>
          <Input
            id="embedding-model"
            {...form.register('model')}
            aria-invalid={!!errors.model}
          />
          {errors.model && (
            <p className="mt-2 text-xs text-destructive">
              {errors.model.message}
            </p>
          )}
        </div>
        <div>
          <label
            htmlFor="embedding-revision"
            className="mb-2 block text-sm font-semibold"
          >
            Revisión
          </label>
          <Input
            id="embedding-revision"
            {...form.register('revision')}
            aria-invalid={!!errors.revision}
          />
          <p className="mt-2 text-xs text-muted-foreground">
            {errors.revision?.message ??
              (provider === 'ollama'
                ? 'Usa auto para detectar y fijar el digest del modelo instalado.'
                : provider === 'tei'
                  ? 'SHA de la revisión cargada en el servidor TEI.'
                  : 'Identificador de tu versión de despliegue, por ejemplo v1.')}
          </p>
        </div>
        <div>
          <label
            htmlFor="embedding-tokens"
            className="mb-2 block text-sm font-semibold"
          >
            Límite de tokens del modelo
          </label>
          <Input
            id="embedding-tokens"
            type="number"
            min={64}
            max={8192}
            {...form.register('max_tokens', { valueAsNumber: true })}
            aria-invalid={!!errors.max_tokens}
          />
          {errors.max_tokens && (
            <p className="mt-2 text-xs text-destructive">
              {errors.max_tokens.message}
            </p>
          )}
        </div>
        <div className="sm:col-span-2 space-y-2 rounded-md border border-border bg-card p-4 text-xs leading-6 text-muted-foreground">
          <p>
            El índice actual usa 768 dimensiones. El modelo elegido debe
            devolver esta dimensión; OpenAI text-embedding-3 permite
            solicitarla.
          </p>
          <p>
            {provider === 'ollama'
              ? 'Instala el modelo en el servidor Ollama configurado para el indexador.'
              : provider === 'openai'
                ? 'La credencial del proveedor se configura en el servidor y no se envía al navegador.'
                : 'El modelo y la revisión deben coincidir con el servidor TEI activo.'}
          </p>
          <p>
            Las versiones publicadas siguen disponibles mientras se reindexa.
            Guardar el perfil no inicia una reindexación.
          </p>
        </div>
        <div className="sm:col-span-2 flex flex-wrap items-center justify-between gap-4">
          <Button
            type="submit"
            disabled={
              !settings.ready || settings.busy || !form.formState.isDirty
            }
          >
            <Save size={15} />{' '}
            {settings.busy ? 'Procesando…' : 'Guardar modelo en backend'}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={
              !settings.ready ||
              settings.busy ||
              form.formState.isDirty ||
              !settings.stale
            }
            onClick={() => void settings.reindexStale()}
          >
            <RefreshCw size={15} /> Reindexar pendientes ({settings.stale})
          </Button>
        </div>
        <p className="sm:col-span-2 text-xs text-muted-foreground">
          La reindexación por lote envía hasta 100 documentos con un perfil
          diferente al actual. Consulta su avance en Trabajos.
        </p>
        {settings.error && (
          <p role="alert" className="sm:col-span-2 text-sm text-destructive">
            {settings.error}
          </p>
        )}
        {settings.notice && (
          <p role="status" className="sm:col-span-2 text-sm text-success">
            {settings.notice}
          </p>
        )}
      </SettingsSection>
    </form>
  )
}
