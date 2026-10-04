export const MAX_PDF_BYTES = 32 * 1024 * 1024
export const MAX_BATCH_FILES = 50

export function fileIdentity(
  file: Pick<File, 'name' | 'size' | 'lastModified'>,
) {
  return JSON.stringify([file.name, file.size, file.lastModified])
}

export async function validatePdf(file: File): Promise<string | null> {
  if (!file.size) return 'El archivo está vacío.'
  if (file.size > MAX_PDF_BYTES) return 'Supera el límite de 32 MB por PDF.'
  if (
    !file.name.toLowerCase().endsWith('.pdf') &&
    file.type !== 'application/pdf'
  )
    return 'Selecciona un archivo PDF.'
  try {
    const sample = new TextDecoder().decode(
      await file.slice(0, 1024).arrayBuffer(),
    )
    if (!sample.includes('%PDF-'))
      return 'El contenido no tiene una cabecera PDF válida.'
  } catch {
    return 'No se pudo leer este archivo.'
  }
  return null
}

export async function runConcurrent<T>(
  items: T[],
  limit: number,
  run: (item: T) => Promise<void>,
) {
  let cursor = 0
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (cursor < items.length) {
        const item = items[cursor++]
        await run(item)
      }
    }),
  )
}
