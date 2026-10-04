import type { UseFormReturn } from 'react-hook-form'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from '#/components/ui/field'
import { Input } from '#/components/ui/input'
import { NativeSelect, NativeSelectOption } from '#/components/ui/native-select'
import { useWorkspace } from '#/components/admin/workspace-provider'
import type {
  SourceMetadata,
  SourceMetadataInput,
} from '#/lib/pdf-ingestion/schema'

type SourceMetadataFieldsProps = {
  form: UseFormReturn<SourceMetadataInput, unknown, SourceMetadata>
}

export function SourceMetadataFields({ form }: SourceMetadataFieldsProps) {
  const { errors } = form.formState
  const development = useWorkspace((store) => store.envMode === 'DEVELOPMENT')

  return (
    <div className="grid items-start gap-5 sm:grid-cols-2 xl:grid-cols-4">
      <Field data-invalid={Boolean(errors.originUrl)} className="gap-1.5">
        <FieldLabel
          htmlFor="originUrl"
          className="text-sm font-semibold text-foreground"
        >
          Origen oficial
        </FieldLabel>
        <Input
          id="originUrl"
          type="url"
          inputMode="url"
          autoComplete="url"
          placeholder="https://sum.unmsm.edu.pe"
          aria-invalid={Boolean(errors.originUrl)}
          {...form.register('originUrl')}
          className="h-11 rounded-md border-input bg-background px-3 text-sm shadow-none placeholder:text-muted-foreground/70 focus-visible:border-primary focus-visible:ring-primary/15"
        />
        <FieldDescription className="text-xs text-muted-foreground">
          Enlace a la página o resolución oficial.
        </FieldDescription>
        {errors.originUrl && <FieldError errors={[errors.originUrl]} />}
      </Field>

      <Field data-invalid={Boolean(errors.resolution)} className="gap-1.5">
        <FieldLabel
          htmlFor="resolution"
          className="text-sm font-semibold text-foreground"
        >
          Código o resolución · opcional
        </FieldLabel>
        <Input
          id="resolution"
          autoComplete="off"
          placeholder="Ej. RR / 2026"
          aria-invalid={Boolean(errors.resolution)}
          {...form.register('resolution')}
          className="h-11 rounded-md border-input bg-background px-3 text-sm shadow-none placeholder:text-muted-foreground/70 focus-visible:border-primary focus-visible:ring-primary/15"
        />
        {errors.resolution && <FieldError errors={[errors.resolution]} />}
      </Field>

      <Field
        data-invalid={Boolean(errors.documentType)}
        className="gap-1.5 [&_[data-slot=native-select-wrapper]]:w-full"
      >
        <FieldLabel
          htmlFor="documentType"
          className="text-sm font-semibold text-foreground"
        >
          Tipo de documento
        </FieldLabel>
        <NativeSelect
          id="documentType"
          aria-invalid={Boolean(errors.documentType)}
          {...form.register('documentType')}
          className="h-11 rounded-md border-input bg-background px-3 pr-10 text-sm shadow-none focus-visible:border-primary focus-visible:ring-primary/15"
        >
          <NativeSelectOption value="plan_estudios">
            Plan de estudios
          </NativeSelectOption>
          <NativeSelectOption value="reglamento">Reglamento</NativeSelectOption>
          <NativeSelectOption value="resolucion">Resolución</NativeSelectOption>
          <NativeSelectOption value="directiva">Directiva</NativeSelectOption>
          <NativeSelectOption value="otro">Otro</NativeSelectOption>
        </NativeSelect>
        <FieldDescription className="text-xs text-muted-foreground">
          Este tipo se conserva en cada documento del lote.
        </FieldDescription>
        {errors.documentType && <FieldError errors={[errors.documentType]} />}
      </Field>
      <Field className="gap-1.5 [&_[data-slot=native-select-wrapper]]:w-full">
        <FieldLabel htmlFor="priority" className="text-sm font-semibold">
          Prioridad de ingesta
        </FieldLabel>
        <NativeSelect
          id="priority"
          {...form.register('priority')}
          className="h-11 rounded-md border-input bg-background px-3 pr-10 text-sm shadow-none"
        >
          <NativeSelectOption value="alta">Alta</NativeSelectOption>
          <NativeSelectOption value="normal">Normal</NativeSelectOption>
          <NativeSelectOption value="baja">Baja</NativeSelectOption>
        </NativeSelect>
      </Field>
      {development && (
        <label className="flex min-h-12 items-start gap-3 rounded-md border border-warning/30 bg-warning/5 p-3 text-sm sm:col-span-2 xl:col-span-4">
          <input
            type="checkbox"
            aria-label="Documento de prueba"
            className="mt-0.5 size-4 accent-primary"
            {...form.register('testDocument')}
          />
          <span>
            <span className="font-semibold">
              Marcar como documento de prueba
            </span>
            <span className="mt-1 block text-xs text-muted-foreground">
              Quedará identificado en la biblioteca y se podrá eliminar solo en
              modo DEVELOPMENT.
            </span>
          </span>
        </label>
      )}
    </div>
  )
}
