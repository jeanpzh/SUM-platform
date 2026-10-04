import { useState } from 'react'
import { Upload } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '#/components/ui/sheet'
import { Button } from '#/components/ui/button'
import { useVectorTransfer } from '#/hooks/use-vector-transfer'

export function VectorImportSheet() {
  const [open, setOpen] = useState(false)
  const transfer = useVectorTransfer()
  function changeOpen(value: boolean) {
    setOpen(value)
    if (!value) transfer.reset()
  }
  return (
    <Sheet open={open} onOpenChange={changeOpen}>
      <SheetTrigger asChild>
        <Button className="min-h-11">
          <Upload size={16} />
          Importar corpus
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader className="px-6 pt-7 pr-12">
          <SheetTitle className="font-display text-2xl">
            Trae tu conocimiento
          </SheetTitle>
          <SheetDescription>
            Revisa los registros antes de añadirlos a la biblioteca local.
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-6 px-6 pb-6">
          <div className="rounded-md border border-border bg-card p-4 text-sm leading-6 text-muted-foreground">
            JSON de SUM, registros JSON / JSONL, CSV, Pinecone o ChromaDB. Cada
            registro necesita título y texto; página, origen y colección son
            opcionales. Los vectores, si existen, deben tener 768 dimensiones.
          </div>
          <div>
            <label
              htmlFor="corpus-file"
              className="mb-2 block text-sm font-semibold"
            >
              Archivo de datos · máximo 4 MB
            </label>
            <input
              id="corpus-file"
              type="file"
              accept=".json,.jsonl,.csv"
              className="w-full rounded-md border border-input p-3 text-sm file:mr-3 file:rounded file:border-0 file:bg-muted file:px-3 file:py-2 file:text-foreground"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void transfer.readFile(file)
              }}
            />
            <p className="mt-2 text-xs text-muted-foreground">
              CSV: title,text,page,source,category. Los PDF se cargan desde
              Ingesta de PDF.
            </p>
          </div>
          {transfer.busy && (
            <p role="status" className="text-sm">
              Validando archivo…
            </p>
          )}
          {transfer.error && (
            <p role="alert" className="text-sm text-destructive">
              {transfer.error}
            </p>
          )}
          {transfer.preview && (
            <section className="space-y-4">
              <div>
                <h2 className="text-sm font-semibold">
                  Vista previa · {transfer.fileName}
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {transfer.preview.format} ·{' '}
                  {transfer.preview.documents.length} documentos ·{' '}
                  {transfer.preview.documents.reduce(
                    (sum, doc) => sum + doc.chunks.length,
                    0,
                  )}{' '}
                  fragmentos
                </p>
              </div>
              {transfer.preview.documents.slice(0, 3).map((doc) => (
                <article
                  key={doc.id}
                  className="rounded-md border border-border p-4"
                >
                  <h3 className="font-semibold">{doc.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {doc.category} · {doc.chunks.length} fragmentos
                  </p>
                  <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">
                    {doc.chunks[0].text}
                  </p>
                </article>
              ))}
              <Button
                className="w-full min-h-11"
                onClick={() => {
                  if (transfer.commit()) changeOpen(false)
                }}
              >
                Añadir a la biblioteca
              </Button>
            </section>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
