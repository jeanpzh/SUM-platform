import { createStore } from 'zustand/vanilla'
import { initialWorkspace } from '#/data/admin-workspace'
import { workspaceReducer } from '#/lib/admin-workspace/reducer'
import type { WorkspaceAction } from '#/lib/admin-workspace/reducer'
import type { WorkspaceState } from '#/lib/admin-workspace/schema'

export type WorkspaceStore = {
  state: WorkspaceState
  loaded: boolean
  persistenceError: string
  envMode: 'checking' | 'DEVELOPMENT' | 'PRODUCTION'
  embeddingProfile: {
    provider: 'tei' | 'ollama' | 'openai'
    model: string
    revision: string
    dimension: number
    max_tokens: number
  } | null
  staleEmbeddingDocuments: number
  backendRevision: number
  backendStatus: 'checking' | 'ready' | 'unavailable'
  backendError: string
  originals: Map<string, File>
  retryRequests: Map<string, { file: File; key: string }>
  monitoringErrors: Record<string, string>
  dispatch: (action: WorkspaceAction) => void
}

// Each app render owns a store; server requests never share user data.
export function createWorkspaceStore() {
  return createStore<WorkspaceStore>()((set) => ({
    state: initialWorkspace,
    loaded: false,
    persistenceError: '',
    envMode: 'checking',
    embeddingProfile: null,
    staleEmbeddingDocuments: 0,
    backendRevision: 0,
    backendStatus: 'checking',
    backendError: '',
    originals: new Map(),
    retryRequests: new Map(),
    monitoringErrors: {},
    dispatch: (action) =>
      set((store) => ({
        state: workspaceReducer(store.state, action),
      })),
  }))
}

export type WorkspaceStoreApi = ReturnType<typeof createWorkspaceStore>
