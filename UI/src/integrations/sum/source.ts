import type { z } from 'zod'
import type { policyScopeSchema } from '../../academic/context/schemas'
import type {
  SumAcademicHistoryResponse,
  SumStudyPlanResponse,
  SumProgrammingResponse,
} from './types/index'

/** Trusted server selectors. Identity and SUM credentials are held by the adapter, never by a model. */
export interface StudentSession {
  connectionId: string
  planCode: string
  historyComplete?: boolean
  policyScope?: z.infer<typeof policyScopeSchema>
}
export interface SumSources {
  history(session: StudentSession): Promise<SumAcademicHistoryResponse>
  /** Scope faculty/school/specialty too; planCode alone is not globally unique. Cache this shared curriculum. */
  plan(session: StudentSession): Promise<SumStudyPlanResponse>
  programming(
    session: StudentSession,
    term?: string,
  ): Promise<SumProgrammingResponse>
}
