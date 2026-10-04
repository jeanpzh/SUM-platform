import { useEffect, useRef, useState } from 'react'
import { Dialog } from 'radix-ui'
import {
  CheckCircle2,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  TestTube2,
  X,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import {
  fetchModelPricing,
  fetchProviders,
  probeMessage,
  providerDefinitions,
  providerKinds,
  saveProvider,
  testProvider,
} from '#/lib/ai/providers'
import type {
  ConnectionProbeResult,
  ProviderConnection,
  ProviderInput,
  ProviderKind,
} from '#/lib/ai/providers'
import { SettingsSection } from './settings-field'
import { selectClass } from './corpus-scope'

type DraftModel = { model: string; input: string; output: string; date: string }
const validModel = /^[A-Za-z0-9._:/-]{1,150}$/

function Field({
  label,
  id,
  hint,
  children,
}: {
  label: string
  id: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">
        {label}
      </label>
      {children}
      {hint && (
        <p className="mt-2 text-xs leading-5 text-muted-foreground">{hint}</p>
      )}
    </div>
  )
}

export function AiProviderSettings() {
  const returnFocus = useRef<HTMLElement | null>(null)
  const [connections, setConnections] = useState<ProviderConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<ProviderConnection | null>(null)
  const [kind, setKind] = useState<ProviderKind>('ollama')
  const [name, setName] = useState('')
  const [url, setUrl] = useState(providerDefinitions.ollama.url)
  const [apiKey, setApiKey] = useState('')
  const [priority, setPriority] = useState<ProviderInput['priority']>('normal')
  const [enabled, setEnabled] = useState(true)
  const [models, setModels] = useState<DraftModel[]>([])
  const [modelInput, setModelInput] = useState('')
  const [probeModel, setProbeModel] = useState('')
  const [probe, setProbe] = useState<ConnectionProbeResult | null>(null)
  const [probedModel, setProbedModel] = useState('')
  const [advanced, setAdvanced] = useState(false)
  const [busy, setBusy] = useState<'saving' | 'testing' | 'pricing' | null>(
    null,
  )
  const [formError, setFormError] = useState('')

  async function reload(signal?: AbortSignal) {
    setLoading(true)
    setError('')
    try {
      const result = await fetchProviders(signal)
      if (!signal?.aborted) setConnections(result)
    } catch (cause) {
      if (!signal?.aborted)
        setError(
          cause instanceof Error
            ? cause.message
            : 'No se pudo cargar Settings.',
        )
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }
  useEffect(() => {
    const controller = new AbortController()
    void reload(controller.signal)
    return () => controller.abort()
  }, [])
  useEffect(() => {
    setProbe(null)
  }, [kind, url, apiKey, modelInput, probeModel, models])

  function begin(connection?: ProviderConnection) {
    returnFocus.current = document.activeElement as HTMLElement
    setEditing(connection || null)
    setKind(connection?.provider || 'ollama')
    setName(connection?.name || '')
    setUrl(connection?.base_url || providerDefinitions.ollama.url)
    setApiKey('')
    setPriority(connection?.priority || 'normal')
    setEnabled(connection?.enabled ?? true)
    setModels(
      connection?.models.map((model) => ({
        model: model.model,
        input: String(model.input_usd_per_million),
        output: String(model.output_usd_per_million),
        date: model.pricing_date,
      })) || [],
    )
    setModelInput('')
    setProbeModel(connection?.models[0]?.model || '')
    setProbe(null)
    setProbedModel('')
    setAdvanced(false)
    setFormError('')
    setNotice('')
    setOpen(true)
  }
  function choose(provider: ProviderKind) {
    setKind(provider)
    setUrl(providerDefinitions[provider].url)
    setApiKey('')
    setModels([])
    setModelInput('')
    setProbeModel('')
    setFormError('')
  }
  async function pricedModel(model: string): Promise<DraftModel> {
    if (!validModel.test(model))
      throw new Error('Introduce un identificador de modelo válido.')
    const draft = {
      model,
      input: '',
      output: '',
      date: new Date().toISOString().slice(0, 10),
    }
    try {
      const pricing = await fetchModelPricing(kind, model)
      draft.input =
        pricing.input_usd_per_million === null
          ? ''
          : String(pricing.input_usd_per_million)
      draft.output =
        pricing.output_usd_per_million === null
          ? ''
          : String(pricing.output_usd_per_million)
      draft.date = pricing.pricing_date
    } catch {
      /* The connection can still be tested; a saved run requires explicit pricing. */
    }
    if (draft.input === '' || draft.output === '') setAdvanced(true)
    return draft
  }
  async function addModel() {
    if (busy) return
    setFormError('')
    const model = modelInput.trim()
    if (models.some((item) => item.model === model)) {
      setFormError('Este modelo ya está añadido.')
      return
    }
    if (models.length >= 20) {
      setFormError('Máximo 20 modelos por conexión.')
      return
    }
    setBusy('pricing')
    try {
      const draft = await pricedModel(model)
      setModels((current) => [...current, draft])
      setModelInput('')
      setProbeModel(model)
    } catch (cause) {
      setFormError(
        cause instanceof Error ? cause.message : 'No se pudo añadir el modelo.',
      )
    } finally {
      setBusy(null)
    }
  }
  function updatePrice(
    model: string,
    key: 'input' | 'output' | 'date',
    value: string,
  ) {
    setModels((current) =>
      current.map((item) =>
        item.model === model ? { ...item, [key]: value } : item,
      ),
    )
  }
  async function testConnection() {
    if (busy) return
    const model = modelInput.trim() || probeModel || models[0]?.model || ''
    if (!validModel.test(model)) {
      setFormError('Introduce o selecciona un modelo para probar.')
      return
    }
    setFormError('')
    setProbe(null)
    setBusy('testing')
    setProbedModel(model)
    try {
      setProbe(
        await testProvider({
          provider: kind,
          base_url: url,
          api_key: apiKey,
          model,
          ...(editing
            ? { config_id: editing.id, expected_revision: editing.revision }
            : {}),
        }),
      )
    } catch (cause) {
      setFormError(
        cause instanceof Error
          ? cause.message
          : 'No se pudo probar la conexión.',
      )
    } finally {
      setBusy(null)
    }
  }
  async function save(event: React.FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormError('')
    setBusy('saving')
    try {
      let selected = models
      const pending = modelInput.trim()
      if (pending && !selected.some((item) => item.model === pending)) {
        if (selected.length >= 20)
          throw new Error('Máximo 20 modelos por conexión.')
        selected = [...selected, await pricedModel(pending)]
        setModels(selected)
        setModelInput('')
        setProbeModel(pending)
      }
      if (!selected.length) throw new Error('Introduce al menos un modelo.')
      if (selected.some((item) => item.input === '' || item.output === '')) {
        setAdvanced(true)
        throw new Error(
          'No hay tarifa automática para algún modelo. Completa sus tarifas en Opciones avanzadas; puedes probar la conexión antes.',
        )
      }
      const connection = await saveProvider(
        {
          provider: kind,
          name:
            name.trim() ||
            `${providerDefinitions[kind].label} · ${selected[0].model}`.slice(
              0,
              100,
            ),
          base_url: url,
          api_key: apiKey,
          priority,
          enabled,
          models: selected.map((item) => ({
            model: item.model,
            input_usd_per_million: Number(item.input),
            output_usd_per_million: Number(item.output),
            pricing_date: item.date,
          })),
          ...(editing ? { expected_revision: editing.revision } : {}),
        },
        editing?.id,
      )
      setConnections((current) =>
        editing
          ? current.map((item) =>
              item.id === connection.id ? connection : item,
            )
          : [...current, connection],
      )
      setApiKey('')
      setOpen(false)
      setNotice(
        `Conexión ${connection.name} guardada · revisión ${connection.revision}.`,
      )
    } catch (cause) {
      setFormError(
        cause instanceof Error ? cause.message : 'No se pudo guardar.',
      )
    } finally {
      setBusy(null)
    }
  }

  const retainsKey =
    editing?.has_api_key &&
    editing.provider === kind &&
    editing.base_url === url
  return (
    <div className="mt-8">
      <SettingsSection
        number="06"
        title="IA con LiteLLM"
        description="Configura modelos para consultar y evaluar el corpus publicado. Prueba la conexión antes de usarlos."
      >
        <div className="space-y-4 sm:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">
              {loading
                ? 'Cargando conexiones…'
                : `${connections.length} conexiones guardadas`}
            </span>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                disabled={loading}
                onClick={() => void reload()}
                aria-label="Recargar proveedores"
              >
                <RefreshCw size={16} />
              </Button>
              <Button
                disabled={loading || connections.length >= 50}
                onClick={() => begin()}
              >
                <Plus size={16} /> Añadir conexión
              </Button>
            </div>
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {!loading && !error && !connections.length && (
            <p className="rounded-md border border-dashed border-border p-5 text-sm leading-6 text-muted-foreground">
              Elige un proveedor, introduce un modelo y su clave. Las conexiones
              guardadas aparecerán en Prueba RAG.
            </p>
          )}
          {connections.map((connection) => (
            <div
              key={connection.id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-border bg-card p-4"
            >
              <div className="min-w-0">
                <h3 className="break-words text-sm font-semibold">
                  {connection.name}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {providerDefinitions[connection.provider].label} ·{' '}
                  {connection.enabled ? 'Habilitado' : 'Deshabilitado'} · v
                  {connection.revision}
                </p>
                <p className="mt-2 break-all text-xs text-muted-foreground">
                  {connection.models.map((model) => model.model).join(' · ')}
                </p>
              </div>
              <Button
                variant="outline"
                className="min-h-11"
                aria-label={`Editar y probar ${connection.name}`}
                onClick={() => begin(connection)}
              >
                <Pencil size={16} /> Editar / probar
              </Button>
            </div>
          ))}
          {notice && (
            <p role="status" className="text-sm text-success">
              {notice}
            </p>
          )}
        </div>
      </SettingsSection>
      <Dialog.Root
        open={open}
        onOpenChange={(value) => {
          if (!busy) {
            setOpen(value)
            if (!value) {
              setApiKey('')
              setProbe(null)
            }
          }
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
          <Dialog.Content
            className="fixed left-1/2 top-1/2 z-50 max-h-[92dvh] w-[calc(100%_-_2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-border bg-background p-5 shadow-lg sm:p-7"
            onCloseAutoFocus={(event) => {
              event.preventDefault()
              returnFocus.current?.focus()
            }}
            onEscapeKeyDown={(event) => {
              if (busy) event.preventDefault()
            }}
            onInteractOutside={(event) => {
              if (busy) event.preventDefault()
            }}
          >
            <div className="flex items-start justify-between gap-5">
              <div>
                <Dialog.Title className="font-display text-2xl">
                  {editing ? 'Editar conexión de IA' : 'Añadir conexión de IA'}
                </Dialog.Title>
                <Dialog.Description className="mt-2 text-sm text-muted-foreground">
                  Selecciona proveedor y modelo. Las claves se guardan cifradas.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-11 shrink-0"
                  disabled={!!busy}
                  aria-label="Cerrar"
                >
                  <X size={20} />
                </Button>
              </Dialog.Close>
            </div>
            <form onSubmit={save} className="mt-6 space-y-5">
              <fieldset disabled={!!busy} className="space-y-5">
                <legend className="sr-only">Configuración de conexión</legend>
                <Field label="Proveedor" id="provider-kind">
                  <select
                    id="provider-kind"
                    className={selectClass}
                    value={kind}
                    onChange={(event) =>
                      choose(event.target.value as ProviderKind)
                    }
                  >
                    {providerKinds.map((provider) => (
                      <option key={provider} value={provider}>
                        {providerDefinitions[provider].label}
                      </option>
                    ))}
                  </select>
                </Field>
                {providerDefinitions[kind].local && (
                  <Field
                    label="API Base URL"
                    id="provider-url"
                    hint="URL accesible desde AI Service. Para tu computadora usa host.docker.internal."
                  >
                    <Input
                      id="provider-url"
                      type="url"
                      required
                      maxLength={500}
                      value={url}
                      onChange={(event) => setUrl(event.target.value)}
                    />
                  </Field>
                )}
                <Field
                  label="API key"
                  id="provider-key"
                  hint={
                    retainsKey
                      ? 'Deja vacío para conservar la clave guardada.'
                      : providerDefinitions[kind].local
                        ? 'Opcional si el servidor local no exige autenticación.'
                        : 'Clave de tu cuenta del proveedor.'
                  }
                >
                  <Input
                    id="provider-key"
                    type="password"
                    autoComplete="new-password"
                    maxLength={4096}
                    value={apiKey}
                    onChange={(event) => setApiKey(event.target.value)}
                    required={!providerDefinitions[kind].local && !retainsKey}
                    placeholder={retainsKey ? 'Clave guardada' : 'API key'}
                  />
                </Field>
                <Field
                  label="Modelo"
                  id="provider-model"
                  hint="Introduce el ID del proveedor. Para varios modelos, añade cada uno con + o Enter."
                >
                  <div className="flex gap-2">
                    <Input
                      id="provider-model"
                      maxLength={150}
                      value={modelInput}
                      onChange={(event) => setModelInput(event.target.value)}
                      placeholder="Identificador del modelo"
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.preventDefault()
                          void addModel()
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      className="size-11 shrink-0"
                      aria-label="Añadir modelo"
                      onClick={() => void addModel()}
                    >
                      <Plus size={16} />
                    </Button>
                  </div>
                  {!!models.length && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {models.map((item) => (
                        <span
                          key={item.model}
                          className="inline-flex max-w-full items-center gap-2 rounded-md bg-primary/10 pl-3 text-sm text-primary"
                        >
                          <span className="break-all">{item.model}</span>
                          <button
                            type="button"
                            className="flex size-11 shrink-0 items-center justify-center rounded-md hover:bg-primary/10 focus-visible:outline-2 focus-visible:outline-ring"
                            aria-label={`Quitar ${item.model}`}
                            onClick={() => {
                              setModels((current) =>
                                current.filter(
                                  (model) => model.model !== item.model,
                                ),
                              )
                              if (probeModel === item.model) setProbeModel('')
                            }}
                          >
                            <X size={14} />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </Field>
                {models.length > 1 && !modelInput.trim() && (
                  <Field label="Modelo para probar" id="provider-probe-model">
                    <select
                      id="provider-probe-model"
                      className={selectClass}
                      value={probeModel || models[0].model}
                      onChange={(event) => setProbeModel(event.target.value)}
                    >
                      {models.map((item) => (
                        <option key={item.model}>{item.model}</option>
                      ))}
                    </select>
                  </Field>
                )}
                <details
                  open={advanced}
                  onToggle={(event) => setAdvanced(event.currentTarget.open)}
                  className="rounded-md border border-border p-4"
                >
                  <summary className="cursor-pointer text-sm font-semibold">
                    Opciones avanzadas
                  </summary>
                  <div className="mt-5 space-y-5">
                    <Field
                      label="Nombre de la conexión"
                      id="provider-name"
                      hint="Opcional: se genera usando proveedor y modelo."
                    >
                      <Input
                        id="provider-name"
                        maxLength={100}
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                      />
                    </Field>
                    <Field label="Prioridad" id="provider-priority">
                      <select
                        id="provider-priority"
                        className={selectClass}
                        value={priority}
                        onChange={(event) =>
                          setPriority(
                            event.target.value as ProviderInput['priority'],
                          )
                        }
                      >
                        <option value="high">Alta</option>
                        <option value="normal">Normal</option>
                        <option value="low">Baja</option>
                      </select>
                    </Field>
                    <label className="flex min-h-11 items-center gap-3 text-sm">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(event) => setEnabled(event.target.checked)}
                        className="size-4 accent-primary"
                      />{' '}
                      Habilitado
                    </label>
                    <p className="text-xs leading-5 text-muted-foreground">
                      Las tarifas conocidas se cargan del catálogo incluido en
                      LiteLLM. Son estimaciones; revisa las de tu contrato. Sin
                      una tarifa conocida, define ambos importes. Un servidor
                      Custom requiere tarifa explícita.
                    </p>
                    {models.map((item, index) => (
                      <div
                        key={item.model}
                        className="space-y-3 border-t border-border pt-4"
                      >
                        <p className="break-all text-sm font-medium">
                          {item.model}
                        </p>
                        <div className="grid gap-3 sm:grid-cols-3">
                          <Field
                            label="Entrada USD / millón"
                            id={`price-in-${index}`}
                          >
                            <Input
                              id={`price-in-${index}`}
                              type="number"
                              min={0}
                              max={10000}
                              step="any"
                              value={item.input}
                              onChange={(event) =>
                                updatePrice(
                                  item.model,
                                  'input',
                                  event.target.value,
                                )
                              }
                            />
                          </Field>
                          <Field
                            label="Salida USD / millón"
                            id={`price-out-${index}`}
                          >
                            <Input
                              id={`price-out-${index}`}
                              type="number"
                              min={0}
                              max={10000}
                              step="any"
                              value={item.output}
                              onChange={(event) =>
                                updatePrice(
                                  item.model,
                                  'output',
                                  event.target.value,
                                )
                              }
                            />
                          </Field>
                          <Field
                            label="Fecha de tarifa"
                            id={`price-date-${index}`}
                          >
                            <Input
                              id={`price-date-${index}`}
                              type="date"
                              value={item.date}
                              onChange={(event) =>
                                updatePrice(
                                  item.model,
                                  'date',
                                  event.target.value,
                                )
                              }
                            />
                          </Field>
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              </fieldset>
              <div className="rounded-md border border-border bg-card p-4">
                <Button
                  type="button"
                  variant="outline"
                  disabled={!!busy || (!modelInput.trim() && !models.length)}
                  onClick={() => void testConnection()}
                >
                  {busy === 'testing' ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <TestTube2 size={16} />
                  )}
                  {busy === 'testing' ? 'Probando…' : 'Probar conexión'}
                </Button>
                <p className="mt-3 text-xs leading-5 text-muted-foreground">
                  Envía una llamada breve para verificar acceso al modelo y
                  herramientas. Puede consumir tokens. No guarda cambios ni
                  prueba el corpus.
                </p>
                {probe && (
                  <div
                    role={probe.success ? 'status' : 'alert'}
                    className={`mt-3 text-sm ${probe.success ? 'text-success' : 'text-destructive'}`}
                  >
                    <p className="flex items-start gap-2">
                      {probe.success && (
                        <CheckCircle2 size={18} className="shrink-0" />
                      )}
                      {probeMessage(probe)}
                    </p>
                    <p className="mt-2 break-all text-xs">
                      {probedModel} · {(probe.latency_ms / 1000).toFixed(2)} s ·{' '}
                      {probe.input_tokens + probe.output_tokens} tokens
                      reportados
                    </p>
                  </div>
                )}
              </div>
              {formError && (
                <p
                  role="alert"
                  className="break-words text-sm text-destructive"
                >
                  {formError}
                </p>
              )}
              <div className="flex flex-wrap justify-end gap-3 border-t border-border pt-5">
                <Dialog.Close asChild>
                  <Button type="button" variant="outline" disabled={!!busy}>
                    Cancelar
                  </Button>
                </Dialog.Close>
                <Button type="submit" disabled={!!busy}>
                  {busy === 'saving'
                    ? 'Guardando…'
                    : busy === 'pricing'
                      ? 'Cargando tarifas…'
                      : 'Guardar conexión'}
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}
