import { createFileRoute } from '@tanstack/react-router'
import { z } from 'zod'

export const Route = createFileRoute('/assistant/$runId')({
  params: { parse: (params) => ({ runId: z.uuid().parse(params.runId) }) },
  component: () => null,
})
