import { useId } from 'react'
import type { CorpusDocument } from '#/lib/admin-workspace/schema'

export const selectClass =
  'min-h-11 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'

export function CorpusScope({
  documents,
  value,
  onChange,
}: {
  documents: CorpusDocument[]
  value: string
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <div className="min-w-0">
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">
        Consultar en
      </label>
      <select
        id={id}
        className={selectClass}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="all">Toda la biblioteca publicada</option>
        {documents
          .filter((doc) => doc.status === 'published')
          .map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.title}
            </option>
          ))}
      </select>
    </div>
  )
}
