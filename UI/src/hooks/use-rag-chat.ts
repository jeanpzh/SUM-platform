import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import * as z from 'zod'
import { useWorkspace } from '#/components/admin/workspace-provider'
import { retrieveChunks } from '#/lib/admin-workspace/retrieval'
import type { RetrievalHit } from '#/lib/admin-workspace/retrieval'

const questionSchema = z.object({
  question: z
    .string()
    .trim()
    .min(3, 'Escribe al menos 3 caracteres.')
    .max(2000, 'La consulta es demasiado larga.'),
})

export type ChatTurn = { id: string; question: string; sources: RetrievalHit[] }

export function useRagChat() {
  const documents = useWorkspace((store) => store.state.documents)
  const settings = useWorkspace((store) => store.state.settings)
  const [scope, setScope] = useState('all')
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const form = useForm<z.infer<typeof questionSchema>>({
    resolver: zodResolver(questionSchema),
    defaultValues: { question: '' },
  })

  const submit = form.handleSubmit(({ question }) => {
    setTurns((current) => [
      ...current.slice(-49),
      {
        id: crypto.randomUUID(),
        question,
        sources: retrieveChunks(question, documents, settings, scope),
      },
    ])
    form.reset()
  })

  function setSuggestedQuestion(question: string) {
    form.setValue('question', question, { shouldValidate: true })
    form.setFocus('question')
  }

  return {
    form,
    submit,
    scope,
    setScope,
    turns,
    documents,
    settings,
    setSuggestedQuestion,
    clear: () => {
      setTurns([])
      form.reset()
    },
  }
}
