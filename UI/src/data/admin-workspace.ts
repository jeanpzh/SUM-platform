import { defaultSettings } from '#/lib/admin-workspace/schema'
import type {
  CorpusDocument,
  WorkspaceState,
} from '#/lib/admin-workspace/schema'

const sampleDocuments: CorpusDocument[] = [
  {
    id: 'sample-ingestion',
    title: 'Documento sintético de prueba',
    fileName: 'documento-sintetico.txt',
    source: 'examples/indexing/documento.txt',
    category: 'Ingesta',
    status: 'published',
    sample: true,
    indexedChunkSize: 384,
    indexedOverlap: 48,
    chunks: [
      {
        id: 'sample-ingestion-1',
        page: 1,
        text: 'DOCUMENTO SINTÉTICO DE PRUEBA. NO ES UNA NORMA INSTITUCIONAL. Este texto permite comprobar la carga, extracción, fragmentación e indexación de un documento en español. Sus datos son ficticios y no deben utilizarse como orientación académica.',
      },
      {
        id: 'sample-ingestion-2',
        page: 1,
        text: 'El proceso debe conservar el título y los metadatos, generar vectores y comunicar el estado final del trabajo. Esta prueba no define requisitos de matrícula, reglas de evaluación ni procedimientos de una universidad.',
      },
    ],
  },
  {
    id: 'sample-publication',
    title: 'Publicación de versiones',
    fileName: 'publicacion-de-versiones.txt',
    source: 'docs/indexer-service.md',
    category: 'Operaciones',
    status: 'published',
    sample: true,
    indexedChunkSize: 384,
    indexedOverlap: 48,
    chunks: [
      {
        id: 'sample-publication-1',
        page: 1,
        text: 'La versión anterior sigue disponible durante una actualización y ante fallos; cancelar impide publicar el nuevo resultado. El backend publica el puntero del catálogo y el estado final del trabajo en una transacción.',
      },
      {
        id: 'sample-publication-2',
        page: 2,
        text: 'Las etapas del trabajo son validación, extracción, fragmentación, generación de vectores, almacenamiento y publicación. Los contadores de páginas, fragmentos y vectores acompañan el progreso.',
      },
    ],
  },
  {
    id: 'sample-citations',
    title: 'Fragmentos y trazabilidad',
    fileName: 'fragmentos-y-trazabilidad.txt',
    source: 'docs/indexer-service.md',
    category: 'Recuperación',
    status: 'published',
    sample: true,
    indexedChunkSize: 384,
    indexedOverlap: 48,
    chunks: [
      {
        id: 'sample-citations-1',
        page: 1,
        text: 'Los fragmentos conservan el texto, la página, el localizador y los metadatos del documento. La URL se conserva como procedencia; el indexador no la visita. Las relaciones son referencias declaradas, no reglas académicas verificadas.',
      },
    ],
  },
]

export const initialWorkspace: WorkspaceState = {
  version: 1,
  settings: defaultSettings,
  documents: sampleDocuments,
  jobs: [],
}
