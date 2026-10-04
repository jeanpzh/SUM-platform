import { ArrowUpRight, Link2 } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Card, CardContent } from '#/components/ui/card'
import { usePdfBatchUpload } from '#/hooks/use-pdf-batch-upload'
import { useWorkspace } from '#/components/admin/workspace-provider'
import { PdfDropzone } from './pdf-dropzone'
import { SourceMetadataFields } from './source-metadata-fields'

export function DocumentUploadCard() {
  const batch = usePdfBatchUpload()
  const { selection: pdf, form } = batch
  const loaded = useWorkspace((store) => store.loaded)
  const backendStatus = useWorkspace((store) => store.backendStatus)
  const backendError = useWorkspace((store) => store.backendError)
  const busy = form.formState.isSubmitting || !loaded

  return (
    <Card
      id="documentos"
      className="rounded-xl border border-border bg-card p-2 shadow-none"
    >
      <CardContent className="space-y-6 rounded-lg bg-background p-4 sm:p-6">
        <PdfDropzone
          entries={pdf.entries}
          notice={pdf.notice}
          busy={busy}
          isDragging={pdf.isDragging}
          onDragStateChange={pdf.setIsDragging}
          onFilesSelect={pdf.selectFiles}
          onFileDrop={pdf.handleDrop}
          onClear={pdf.clear}
          onRemove={pdf.remove}
          onTitleChange={(id, title) => pdf.patch(id, { title, error: '' })}
        />

        <form
          onSubmit={batch.submit}
          noValidate
          className="min-w-0 border-t border-border pt-6"
        >
          <div className="mb-5 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
            <h2 className="font-display text-xl">Metadatos del lote</h2>
            <p className="max-w-xl text-xs leading-5 text-muted-foreground">
              Misma procedencia y tipo para el lote. Cada PDF conserva su título
              y trabajo.
            </p>
          </div>
          <fieldset disabled={busy} className="min-w-0">
            <SourceMetadataFields form={form} />
          </fieldset>
          <div className="mt-6 flex flex-col gap-4 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="m-0 flex flex-1 items-start gap-2 text-xs leading-5 text-muted-foreground">
              <Link2
                size={14}
                strokeWidth={1.6}
                className="mt-0.5 shrink-0"
                aria-hidden="true"
              />
              3 cargas simultáneas · seguimiento independiente por PDF.
            </p>
            <Button
              type="submit"
              disabled={
                !batch.pending.length ||
                batch.checking ||
                busy ||
                !batch.connected
              }
              className="group h-12 w-full shrink-0 justify-between sm:w-64 rounded-md bg-primary pl-5 pr-2.5 text-sm font-semibold text-primary-foreground shadow-none transition-[background-color,transform] duration-300 [transition-timing-function:cubic-bezier(0.32,0.72,0,1)] hover:bg-primary-hover active:scale-[0.99] disabled:bg-muted disabled:text-muted-foreground disabled:opacity-100"
            >
              <span>
                {form.formState.isSubmitting
                  ? 'Enviando lote…'
                  : `Iniciar ingesta (${batch.pending.length})`}
              </span>
              <span className="grid size-8 place-items-center rounded-full bg-white/15 transition-transform duration-300 [transition-timing-function:cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-0.5 group-hover:-translate-y-px">
                <ArrowUpRight size={16} strokeWidth={1.6} aria-hidden="true" />
              </span>
            </Button>
          </div>
          <p
            aria-live="polite"
            className="mb-0 mt-2 min-h-5 text-xs text-success"
          >
            {batch.confirmation}
          </p>
          {backendStatus === 'unavailable' && (
            <p role="alert" className="mt-3 text-sm text-warning">
              {backendError} Comprobaremos el servicio de nuevo automáticamente.
              Puedes seguir preparando tus archivos.
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  )
}
