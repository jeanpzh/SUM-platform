import { useEffect } from 'react'
import { workspaceSchema } from '#/lib/admin-workspace/schema'
import type { WorkspaceStoreApi } from '#/stores/admin-workspace-store'

const STORAGE_KEY = 'sum-admin-workspace-v1'

export function useWorkspacePersistence(store: WorkspaceStoreApi) {
  useEffect(() => {
    let hydrationError = ''
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const result = workspaceSchema.safeParse(JSON.parse(stored))
        if (result.success)
          store.getState().dispatch({ type: 'hydrate', state: result.data })
        else
          hydrationError =
            'El espacio guardado no es compatible. Se cargó la muestra inicial.'
      }
    } catch {
      hydrationError = 'No se pudo leer el espacio guardado en este navegador.'
    }
    store.setState({ loaded: true, persistenceError: hydrationError })
    return store.subscribe((current, previous) => {
      if (current.state === previous.state) return
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(current.state))
        store.setState({ persistenceError: '' })
      } catch {
        store.setState({
          persistenceError:
            'El navegador no pudo guardar los cambios. Exporta el corpus para conservarlo.',
        })
      }
    })
  }, [store])
}
