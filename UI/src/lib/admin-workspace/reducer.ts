import type { IndexingJob } from '#/data/pdf-ingestion-jobs'
import type {
  CorpusDocument,
  WorkspaceSettings,
  WorkspaceState,
} from './schema'

export type WorkspaceAction =
  | { type: 'hydrate'; state: WorkspaceState }
  | { type: 'enqueue'; job: IndexingJob }
  | { type: 'upsert-job'; job: IndexingJob }
  | { type: 'remove-backend-document'; documentId: string }
  | { type: 'retry'; id: string }
  | { type: 'cancel'; id: string }
  | { type: 'import'; documents: CorpusDocument[] }
  | { type: 'remove'; ids: string[] }
  | { type: 'archive'; id: string }
  | { type: 'reindex'; jobs: IndexingJob[] }
  | { type: 'settings'; settings: WorkspaceSettings }

export function workspaceReducer(
  state: WorkspaceState,
  action: WorkspaceAction,
): WorkspaceState {
  switch (action.type) {
    case 'hydrate':
      return action.state
    case 'enqueue':
      return { ...state, jobs: [action.job, ...state.jobs].slice(0, 500) }
    case 'remove-backend-document':
      return {
        ...state,
        jobs: state.jobs.filter((job) => job.documentId !== action.documentId),
      }
    case 'upsert-job': {
      const old = state.jobs.find((job) => job.id === action.job.id)
      if (old && (old.sequence ?? 0) > (action.job.sequence ?? 0)) return state
      return {
        ...state,
        jobs: old
          ? state.jobs.map((job) =>
              job.id === action.job.id ? action.job : job,
            )
          : [action.job, ...state.jobs].slice(0, 500),
      }
    }
    case 'retry':
      return {
        ...state,
        jobs: state.jobs.map((job) =>
          job.id === action.id &&
          (job.status === 'failed' || job.status === 'cancelled')
            ? {
                ...job,
                status: 'queued',
                stage: 0,
                progress: undefined,
                updatedAt: 'Ahora',
                note: 'Reintento local agregado a la cola.',
              }
            : job,
        ),
      }
    case 'cancel':
      return {
        ...state,
        jobs: state.jobs.map((job) =>
          job.id === action.id &&
          (job.status === 'queued' || job.status === 'processing')
            ? {
                ...job,
                status: 'cancelled',
                updatedAt: 'Ahora',
                note: 'Solicitud cancelada. La versión publicada se conserva.',
              }
            : job,
        ),
      }
    case 'import':
      return { ...state, documents: [...action.documents, ...state.documents] }
    case 'remove':
      return {
        ...state,
        documents: state.documents.filter(
          (doc) => !action.ids.includes(doc.id),
        ),
      }
    case 'archive':
      return {
        ...state,
        documents: state.documents.map((doc) =>
          doc.id === action.id
            ? {
                ...doc,
                status: doc.status === 'published' ? 'archived' : 'published',
              }
            : doc,
        ),
      }
    case 'reindex':
      return { ...state, jobs: [...action.jobs, ...state.jobs].slice(0, 500) }
    case 'settings':
      return { ...state, settings: action.settings }
  }
}
