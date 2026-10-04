import { useRef } from 'react'
import { FileUp } from 'lucide-react'
import { Button } from '#/components/ui/button'
import type { PdfSelection } from '#/hooks/use-pdf-file-selection'
import { PdfFileRow } from './pdf-file-row'

type PdfDropzoneProps = {
  entries: PdfSelection[]
  notice: string
  busy: boolean
  isDragging: boolean
  onDragStateChange: (isDragging: boolean) => void
  onFilesSelect: (files: File[]) => Promise<void>
  onFileDrop: (event: React.DragEvent<HTMLElement>) => void
  onRemove: (id: string) => void
  onTitleChange: (id: string, title: string) => void
  onClear: () => void
}

export function PdfDropzone({
  entries,
  notice,
  busy,
  isDragging,
  onDragStateChange,
  onFilesSelect,
  onFileDrop,
  onClear,
  onRemove,
  onTitleChange,
}: PdfDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <section aria-labelledby="pdf-upload-label" className="min-w-0">
      <div
        onDragEnter={(event) => {
          event.preventDefault()
          onDragStateChange(true)
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (
            !event.currentTarget.contains(event.relatedTarget as Node | null)
          ) {
            onDragStateChange(false)
          }
        }}
        onDrop={(event) => {
          if (busy) {
            event.preventDefault()
            onDragStateChange(false)
          } else onFileDrop(event)
        }}
        data-testid="pdf-dropzone"
        className={`grid items-center justify-items-center gap-4 rounded-lg border border-dashed px-5 py-6 text-center transition-[background-color,border-color,transform] duration-300 [transition-timing-function:cubic-bezier(0.32,0.72,0,1)] sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:justify-items-start sm:gap-5 sm:text-left ${isDragging ? 'translate-y-[-1px] border-primary bg-primary-soft' : 'border-input bg-background hover:border-primary/60'}`}
      >
        <div className="grid size-12 place-items-center rounded-md bg-muted text-muted-foreground">
          <FileUp size={22} strokeWidth={1.5} aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <h2
            id="pdf-upload-label"
            className="font-display text-[1.25rem] font-medium text-foreground"
          >
            Arrastra tus PDF aquí
          </h2>
          <p className="mb-0 mt-1 text-sm text-muted-foreground">
            Adjunta varios documentos en una sola carga.
          </p>
          <p className="mb-0 mt-2 text-xs text-muted-foreground">
            Hasta 50 PDF por lote · 32 MB por archivo
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          disabled={busy}
          tabIndex={-1}
          aria-label="Seleccionar archivos PDF"
          className="sr-only"
          onChange={(event) => {
            void onFilesSelect(Array.from(event.currentTarget.files ?? []))
            event.currentTarget.value = ''
          }}
        />
        <Button
          type="button"
          variant="outline"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="h-11 border-border bg-background px-5 text-primary hover:border-primary hover:bg-primary-soft"
        >
          Seleccionar archivos
        </Button>
      </div>

      {notice && (
        <p role="status" className="mt-3 text-sm text-warning">
          {notice}
        </p>
      )}
      {!!entries.length && (
        <>
          <div className="mb-3 mt-5 flex items-center justify-between gap-2">
            <p className="text-sm font-semibold">
              {entries.length} archivos adjuntos
            </p>
            <Button
              variant="ghost"
              type="button"
              disabled={busy}
              onClick={onClear}
              className="text-xs"
            >
              Limpiar lista
            </Button>
          </div>
          <ul
            className="grid max-h-[480px] gap-3 overflow-y-auto pr-1 md:grid-cols-2"
            aria-label="PDF adjuntos"
          >
            {entries.map((entry) => (
              <PdfFileRow
                key={entry.id}
                entry={entry}
                busy={busy}
                onRemove={() => onRemove(entry.id)}
                onTitleChange={(title) => onTitleChange(entry.id, title)}
              />
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
