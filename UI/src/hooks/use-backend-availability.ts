import { useEffect } from 'react'
import { useStore } from 'zustand'
import { checkConnection } from '#/lib/pdf-ingestion/backend'
import type { WorkspaceStoreApi } from '#/stores/admin-workspace-store'

export function useBackendAvailability(store: WorkspaceStoreApi) {
  const loaded = useStore(store, (current) => current.loaded)
  useEffect(() => {
    if (!loaded) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    async function check() {
      let delay = 15000
      try {
        const capabilities = await checkConnection(controller.signal)
        if (controller.signal.aborted) return
        store.setState({
          backendStatus: 'ready',
          backendError: '',
          envMode: capabilities.env_mode,
          embeddingProfile: capabilities.embedding_profile,
          staleEmbeddingDocuments: capabilities.stale_documents,
        })
      } catch (cause) {
        if (controller.signal.aborted) return
        delay = 5000
        store.setState({
          backendStatus: 'unavailable',
          backendError:
            cause instanceof Error
              ? cause.message
              : 'El servicio no está disponible.',
        })
      }
      timer = setTimeout(() => {
        void check()
      }, delay)
    }
    void check()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [store, loaded])
}
