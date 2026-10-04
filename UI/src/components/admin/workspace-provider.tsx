import { createContext, useContext, useState } from 'react'
import { useStore } from 'zustand'
import { useWorkspacePersistence } from '#/hooks/use-workspace-state'
import { useIndexingMonitor } from '#/hooks/use-indexing-monitor'
import { useBackendAvailability } from '#/hooks/use-backend-availability'
import { createWorkspaceStore } from '#/stores/admin-workspace-store'
import type {
  WorkspaceStore,
  WorkspaceStoreApi,
} from '#/stores/admin-workspace-store'

const WorkspaceContext = createContext<WorkspaceStoreApi | null>(null)

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [store] = useState(createWorkspaceStore)
  useWorkspacePersistence(store)
  useBackendAvailability(store)
  useIndexingMonitor(store)
  return (
    <WorkspaceContext.Provider value={store}>
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace<T>(selector: (store: WorkspaceStore) => T): T {
  return useStore(useWorkspaceApi(), selector)
}

export function useWorkspaceApi(): WorkspaceStoreApi {
  const store = useContext(WorkspaceContext)
  if (!store)
    throw new Error('useWorkspace must be used inside WorkspaceProvider')
  return store
}
